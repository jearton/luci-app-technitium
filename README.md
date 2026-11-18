# LuCI app for Technitium DNS

Open **Services → Technitium DNS** to check the native service, manage startup and open the Technitium web console. Account, zone and DNS settings are managed in the Technitium console.

This app expects the `technitium` OpenWrt package from [openwrt-pro](https://github.com/jearton/openwrt-pro), including its `/etc/init.d/technitium` service. Build it using the standard LuCI feed alongside that package.

LuCI's RPC ACL separates status and service control. The Technitium console has its own login. LuCI does not store its credentials.
