#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise actual APK transactions in a disposable IPv4-only OpenWrt VM."""

import gzip
import hashlib
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

BASE_URL = (
    "https://github.com/jearton/openwrt-pro/releases/download/"
    "v25.12.6-20261118/openwrt-x86-64-generic-squashfs-combined-efi.img.gz"
)
BASE_SHA256 = "676599499413774b57b0f728a16d00a2929e2234ac6be9693705b083471638cf"
OFFLINE = "apk --no-network --repositories-file /dev/null --allow-untrusted"
AUTH = """
token=$(curl -fsS --max-time 10 -G http://127.0.0.1:5380/api/user/login \
    --data-urlencode user=admin --data-urlencode pass@/etc/technitium/setup-password |
    jsonfilter -e '@.token')
test -n "$token"
"""


class Guest:
    def __init__(self, directory, key):
        self.directory = directory
        self.key = key

    def ssh_args(self):
        return [
            "-i", str(self.key), "-p", "10022",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "UserKnownHostsFile=" + str(self.directory / "known_hosts"),
            "-o", "LogLevel=ERROR",
        ]

    def run(self, script, timeout=120):
        result = subprocess.run(
            ["ssh", *self.ssh_args(), "root@127.0.0.1", "sh -se"],
            input="set -eu\n" + script, text=True, capture_output=True, timeout=timeout,
        )
        if result.returncode:
            # Script bodies can contain tokens in shell variables, so report
            # only tool output and never echo the submitted script.
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    def upload(self, paths):
        # scp uses -P for the port, while ssh uses -p.
        options = self.ssh_args()
        options[options.index("-p")] = "-P"
        subprocess.run(
            ["scp", "-O", *options, *map(str, paths), "root@127.0.0.1:/tmp/technitium-test/"],
            check=True, timeout=120,
        )


def await_ssh(guest):
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        try:
            guest.run("true", timeout=5)
            return
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(2)
    raise RuntimeError("The isolated VM did not provide its test SSH endpoint")


def bootstrap(serial_path, public_key):
    deadline = time.monotonic() + 180
    serial = socket.socket(socket.AF_UNIX)
    while time.monotonic() < deadline:
        try:
            serial.connect(str(serial_path))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(1)
    else:
        raise RuntimeError("QEMU serial socket did not open")
    with serial:
        serial.settimeout(2)
        output = b""
        command_sent = False
        while time.monotonic() < deadline:
            try:
                chunk = serial.recv(65536)
                if not chunk:
                    raise RuntimeError("QEMU closed its serial console")
                output = (output + chunk)[-32768:]
            except socket.timeout:
                serial.sendall(b"\n")
                continue
            if b"Please press Enter" in output or b"Press Enter" in output:
                serial.sendall(b"\n")
            if b"root@OpenWrt" in output and not command_sent:
                command = (
                    "mkdir -p /etc/dropbear; printf '%s\\n' '" + public_key + "' "
                    ">> /etc/dropbear/authorized_keys; chmod 600 /etc/dropbear/authorized_keys; "
                    "/etc/init.d/dropbear start; printf '\\nBOOTSTRAP-%s\\n' READY\n"
                )
                serial.sendall(command.encode())
                command_sent = True
            if b"BOOTSTRAP-READY" in output:
                return
    raise RuntimeError("Unable to bootstrap the disposable VM console")


def tests(guest, apks):
    guest.run("""
until /etc/init.d/technitium running && test -e /etc/technitium/provisioned; do sleep 2; done
test "$(cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null || echo 1)" = 1
mkdir -p /tmp/technitium-test
""")
    guest.upload(sorted(apks.glob("*.apk")) + [apks / "packages.adb"])
    guest.run(AUTH + """
curl -fsS -G -H "Authorization: Bearer $token" http://127.0.0.1:5380/api/zones/create \
    --data-urlencode zone=package-ci.test --data-urlencode type=Primary |
    jsonfilter -e '@.status' | grep -qx ok
curl -fsS -G -H "Authorization: Bearer $token" http://127.0.0.1:5380/api/zones/records/add \
    --data-urlencode domain=node.package-ci.test --data-urlencode type=A \
    --data-urlencode ipAddress=192.0.2.42 --data-urlencode ttl=60 |
    jsonfilter -e '@.status' | grep -qx ok
cp /etc/technitium/setup-password /tmp/password.before
cp /etc/config/dhcp /tmp/dhcp.before
cp /etc/config/firewall /tmp/firewall.before
""")
    guest.run(OFFLINE + " add /tmp/technitium-test/*.apk\n")
    guest.run("""
until curl -fsS http://127.0.0.1:5380/ >/dev/null; do sleep 2; done
/etc/init.d/technitium running
/etc/init.d/technitium enabled
cmp /etc/technitium/setup-password /tmp/password.before
cmp /etc/config/dhcp /tmp/dhcp.before
cmp /etc/config/firewall /tmp/firewall.before
nslookup node.package-ci.test 127.0.0.1 | grep -F 192.0.2.42
test -f /usr/lib/technitium/console/index.html
test -f /usr/lib/technitium/server/DnsServerApp.dll
curl -fsS http://127.0.0.1:5380/ | grep -F 'id="root"'
ubus call luci.technitium status | jsonfilter -e '@.running' | grep -qx true
""")
    guest.run(AUTH)
    print("Running legacy installation upgraded with DNS data, password and networking preserved.", flush=True)

    guest.run(AUTH + """
curl -fsS -G -H "Authorization: Bearer $token" http://127.0.0.1:5380/api/settings/set \
    --data-urlencode dnsServerLocalEndPoints=0.0.0.0:1053 |
    jsonfilter -e '@.status' | grep -qx ok
until ubus call luci.technitium status | jsonfilter -e '@.listener_ports[*]' | grep -qx 1053; do sleep 1; done
curl -fsS -G -H "Authorization: Bearer $token" http://127.0.0.1:5380/api/settings/set \
    --data-urlencode dnsServerLocalEndPoints=0.0.0.0:53 |
    jsonfilter -e '@.status' | grep -qx ok
until ubus call luci.technitium status | jsonfilter -e '@.listener_ports[*]' | grep -qx 53; do sleep 1; done
cp /etc/technitium/setup-password /tmp/password.before
""")
    print("LuCI reports the actual DNS listener after changing 53 to 1053 and back.", flush=True)

    for running, enabled in [(False, False), (False, True), (True, False), (True, True)]:
        guest.run(
            "/etc/init.d/technitium " + ("start" if running else "stop") + "\n"
            "/etc/init.d/technitium " + ("enable" if enabled else "disable") + "\n"
        )
        guest.run(
            OFFLINE + " --repository /tmp/technitium-test/packages.adb fix --reinstall technitium\n",
            timeout=120,
        )
        guest.run(
            ("" if running else "! ") + "/etc/init.d/technitium running\n" +
            ("" if enabled else "! ") + "/etc/init.d/technitium enabled\n" +
            "cmp /etc/technitium/setup-password /tmp/password.before\n"
        )
        if running:
            guest.run("until curl -fsS http://127.0.0.1:5380/ >/dev/null; do sleep 1; done\n" + AUTH)
        print(f"Reinstallation preserved running={running}, enabled={enabled}.", flush=True)

    guest.run("""
/etc/init.d/technitium stop
/etc/init.d/technitium disable
""")
    try:
        guest.run("reboot", timeout=5)
    except (RuntimeError, subprocess.TimeoutExpired):
        pass
    time.sleep(5)
    await_ssh(guest)
    guest.run("""
! /etc/init.d/technitium running
! /etc/init.d/technitium enabled
test -f /etc/technitium/data/auth.config
""")
    print("Disabled service remains disabled after reboot.", flush=True)
    guest.run("mkdir -p /tmp/technitium-test\n")
    guest.upload(sorted(apks.glob("*.apk")) + [apks / "packages.adb"])

    # Mark dependencies explicitly installed before removing the old application.
    # This keeps the VM's libraries available for the subsequent offline install.
    guest.run(OFFLINE + " add libstdcpp6 libgcc1 libopenssl3 libatomic1 zlib ca-bundle rpcd-mod-ucode ucode-mod-fs\n")
    guest.run(OFFLINE + " del luci-app-technitium luci-i18n-technitium-zh-cn technitium\n")
    guest.run("""
# Retain the old dataset as a rollback point while testing a first installation.
mv /etc/technitium /root/technitium.before-fresh-install
uci set 'dhcp.@dnsmasq[0].port=53'
uci commit dhcp
/etc/init.d/dnsmasq restart
cp /etc/config/dhcp /tmp/dhcp.before
cp /etc/config/firewall /tmp/firewall.before
""")
    guest.run(OFFLINE + " add /tmp/technitium-test/*.apk\n")
    guest.run("""
! /etc/init.d/technitium running
! /etc/init.d/technitium enabled
test ! -e /etc/technitium/setup-password
cmp /etc/config/dhcp /tmp/dhcp.before
cmp /etc/config/firewall /tmp/firewall.before
ubus call luci.technitium status | jsonfilter -e '@.running' | grep -qx false
/etc/init.d/technitium start || true
! /etc/init.d/technitium running
/etc/init.d/dnsmasq running
""")
    print("Fresh offline installation stays disabled and detects the existing DNS listener.", flush=True)
    guest.run("""
uci set 'dhcp.@dnsmasq[0].port=5353'
uci commit dhcp
/etc/init.d/dnsmasq restart
/etc/init.d/technitium start
until curl -fsS http://127.0.0.1:5380/ >/dev/null; do sleep 2; done
/etc/init.d/technitium running
! /etc/init.d/technitium enabled
test "$(wc -c < /etc/technitium/setup-password)" -eq 48
curl -fsS http://127.0.0.1:5380/ | grep -F 'id="root"'
""")
    guest.run(AUTH + """
curl -fsS -G -H "Authorization: Bearer $token" http://127.0.0.1:5380/api/zones/list |
    jsonfilter -e '@.status' | grep -qx ok
""")
    print("Manual start serves the bundled console with its generated admin password.", flush=True)


def main():
    apks = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="technitium-apk-vm-") as temporary:
        directory = Path(temporary)
        archive = directory / "base.img.gz"
        print("Downloading the checksum-pinned regression image.", flush=True)
        urllib.request.urlretrieve(BASE_URL, archive)
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == BASE_SHA256
        with gzip.open(archive, "rb") as source, (directory / "disk.img").open("wb") as target:
            shutil.copyfileobj(source, target)
        shutil.copyfile("/usr/share/OVMF/OVMF_VARS_4M.fd", directory / "vars.fd")
        key = directory / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        public_key = key.with_suffix(".pub").read_text().strip()
        net = "user,id=lan,restrict=on,ipv6=off,net=192.168.1.0/24,host=192.168.1.2"
        net += ",hostfwd=tcp:127.0.0.1:10022-192.168.1.1:22"
        command = [
            "qemu-system-x86_64", "-machine", "q35", "-accel", "kvm", "-accel", "tcg",
            "-smp", "2", "-m", "1536", "-display", "none", "-monitor", "none",
            "-serial", f"unix:{directory / 'serial.sock'},server=on,wait=off",
            "-drive", "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd",
            "-drive", f"if=pflash,format=raw,file={directory / 'vars.fd'}",
            "-drive", f"if=ide,format=raw,file={directory / 'disk.img'}",
            "-netdev", net, "-device", "e1000,netdev=lan",
        ]
        process = subprocess.Popen(command)
        try:
            print("Booting the isolated IPv4-only VM.", flush=True)
            bootstrap(directory / "serial.sock", public_key)
            guest = Guest(directory, key)
            await_ssh(guest)
            print("The test SSH endpoint is ready.", flush=True)
            tests(guest, apks)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
