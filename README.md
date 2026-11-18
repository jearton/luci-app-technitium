# LuCI app for Technitium DNS

Open **Services → Technitium DNS** to check the native service, manage startup and open the Technitium web console. Account, zone and DNS settings are managed in the Technitium console.

This app expects the `technitium` OpenWrt package from [openwrt-pro](https://github.com/jearton/openwrt-pro), including its `/etc/init.d/technitium` service. Build it using the standard LuCI feed alongside that package.

LuCI's RPC ACL separates status and service control. The Technitium console has its own login. LuCI does not store its credentials.

## Screenshots

Captured from the x86/64 OpenWrt lab, using Argon and Technitium Console 1.4.2.

**Services → Technitium DNS**

![LuCI Technitium service status and controls](docs/luci-technitium.png)

**Technitium Console → Zones**

![Technitium Console with the lab DNS zones](docs/technitium-console.png)

## Builds

[Actions](https://github.com/jearton/luci-app-technitium/actions) builds the OpenWrt 25.12 APK and Simplified Chinese translation. A version tag publishes both APKs and their SHA-256 checksums to [Releases](https://github.com/jearton/luci-app-technitium/releases) and [GHCR](https://github.com/jearton/luci-app-technitium/pkgs/container/luci-app-technitium). Install the matching native `technitium` package as well.
