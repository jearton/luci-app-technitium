# LuCI app for Technitium DNS

Open **Services → Technitium DNS** to check the native service, manage startup and open the Technitium web console. Account, zone and DNS settings are managed in the Technitium console.

This app expects the `technitium` OpenWrt package from [openwrt-pro](https://github.com/jearton/openwrt-pro), including its `/etc/init.d/technitium` service. Build it using the standard LuCI feed alongside that package.

LuCI's RPC ACL separates status and service control. The Technitium console has its own login. LuCI does not store its credentials.

## Update an existing installation

On a router that already has the native `technitium` package, update the LuCI plugin with the `luci-app-technitium-*.apk` file from [Releases](https://github.com/jearton/luci-app-technitium/releases). Verify the download against the accompanying `SHA256SUMS`. The existing Chinese translation package can be kept for the v1.0.2 layout fix.

Copy the verified APK from your computer. This example uses the default LAN address and the v1.0.2 filename.

```sh
scp -O luci-app-technitium-1.0.2-r1.apk root@192.168.1.1:/tmp/
ssh root@192.168.1.1
```

On the router, check that the uploaded file exists at the exact path. If it is missing, repeat the copy from your computer and check the destination address. The router clears `/tmp` on reboot.

```sh
ls -l /tmp/luci-app-technitium-1.0.2-r1.apk
```

If the router already has the native `technitium` and `rpcd-mod-ucode` packages, this update works offline. The install command skips repository configuration for this invocation and permits the verified standalone APK. [APK options](https://github.com/alpinelinux/apk-tools/blob/v3.0.5/doc/apk.8.scd)

```sh
apk --no-network --repositories-file /dev/null --allow-untrusted add /tmp/luci-app-technitium-1.0.2-r1.apk
apk --no-network --repositories-file /dev/null list -I luci-app-technitium
```

Refresh **Services → Technitium DNS** in LuCI. The router can stay running during the update.

## Screenshots

**Services → Technitium DNS**

LuCI v1.0.2 rendered in Chrome with the Argon theme and example service status.

![Technitium DNS LuCI page with a compact console button on the left](docs/luci-technitium.png)

**Technitium Console → Zones**

Captured from Technitium Console 1.4.2 in the x86/64 OpenWrt lab.

![Technitium Console with the lab DNS zones](docs/technitium-console.png)

## Builds

[Actions](https://github.com/jearton/luci-app-technitium/actions) builds the OpenWrt 25.12 APK and Simplified Chinese translation. A version tag publishes both APKs and their SHA-256 checksums to [Releases](https://github.com/jearton/luci-app-technitium/releases) and [GHCR](https://github.com/jearton/luci-app-technitium/pkgs/container/luci-app-technitium). Install the matching native `technitium` package as well.
