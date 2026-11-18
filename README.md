# OpenWrt Technitium DNS

**简体中文** | [English](README.en.md)

为 OpenWrt 提供原生 Technitium DNS Server、Technitium Console 和 LuCI 服务管理。本项目独立构建和发布完整安装所需的软件包。

| 软件包 | 内容 |
| --- | --- |
| `technitium` | [Technitium DNS Server](https://github.com/TechnitiumSoftware/DnsServer) 15.6.2、[Technitium Console](https://github.com/byGarcia/technitium-console) 1.4.2、ASP.NET Core 10.0.15 musl 运行时、procd 服务和配置备份路径 |
| `luci-app-technitium` | LuCI 状态、启动、停止、重启、开机启动设置和控制台入口 |
| `luci-i18n-technitium-zh-cn` | LuCI 界面的简体中文翻译 |

当前原生服务包支持 **OpenWrt 25.12 x86/64**。LuCI 包与 CPU 架构无关，其他架构需要匹配的原生运行时包。

## 安装与默认状态

从 [Releases](https://github.com/jearton/luci-app-technitium/releases) 同时下载后台包和 LuCI 主包，需要中文时再下载翻译包。按随附的 `SHA256SUMS` 校验下载文件。将 APK 上传到路由器，命令中的地址使用实际 LAN 地址。

```sh
scp -O technitium-15.6.2-r2.apk luci-app-technitium-1.1.0-r1.apk root@192.168.1.1:/tmp/
ssh root@192.168.1.1
```

在路由器终端安装两个 APK。APK 会通过路由器已配置的软件源解析并获取运行时依赖。

```sh
apk add --allow-untrusted /tmp/technitium-15.6.2-r2.apk /tmp/luci-app-technitium-1.1.0-r1.apk
```

系统依赖已经安装时，可以离线执行以下命令。

```sh
apk --no-network --repositories-file /dev/null --allow-untrusted add /tmp/technitium-15.6.2-r2.apk /tmp/luci-app-technitium-1.1.0-r1.apk
apk --no-network --repositories-file /dev/null list -I technitium luci-app-technitium
```

依赖包包括 `libstdcpp6`、`libgcc1`、`libopenssl3`、`libatomic1`、`zlib`、`ca-bundle` 、`rpcd-mod-ucode` 和 `ucode-mod-fs`，同时需要已安装 LuCI。`--allow-untrusted` 用于本次安装已校验的独立 APK。[OpenWrt APK 文档](https://openwrt.org/docs/guide-user/additional-software/apk)

**首次独立安装后，Technitium 默认停止，开机启动默认关闭。** 进入「服务 → Technitium DNS」启动服务，并按需开启开机启动。首次启动前，请配置现有 DNS 服务，释放 53 端口。首次启动会检查 DNS 端口占用。

软件包升级保留服务原有的运行状态、开机启动设置和 `/etc/technitium/` 数据。固件构建者可以在安装软件包并完成 DNS 集成后，显式开启服务。

通用包由管理员配置 DHCP、防火墙、OpenClash、其他 DNS 服务和内网域名转发。软件包附带 Advanced Forwarding 5.2 安装归档，可在 Technitium 控制台安装。

## 首次登录控制台

进入「服务 → Technitium DNS」，确认服务已运行，点击「打开 Technitium 控制台」。当前入口使用与 LuCI 相同的主机地址和 HTTP 端口 `5380`，初始 DNS 端口为 `53`。DNS 端口可在 Technitium Console 修改，LuCI 从服务进程的实际 TCP/UDP 监听端口读取并展示，停止时显示「未监听」。控制台自身的 HTTP 端口修改后，需要同步调整当前 LuCI 集成的入口。

用户名是 `admin`。通过路由器的 LuCI 终端或 SSH 管理连接查看首次启动时随机生成的密码。

```sh
cat /etc/technitium/setup-password
```

登录后在控制台修改密码。该文件保留初始密码，修改密码后仍会显示原值。确认新密码可以登录后，删除路由器上的初始密码文件。

控制台使用自己的登录认证。LuCI 的 RPC 权限控制服务管理操作。

## 更新已有安装

上传匹配版本的后台包和 LuCI 主包，再执行上面的安装命令。v1.1.0 的 LuCI 主包依赖 `technitium >= 15.6.2-r2`。

安装前确认文件存在于准确的目标路径。路由器重启会清空 `/tmp`。

```sh
ls -l /tmp/technitium-15.6.2-r2.apk /tmp/luci-app-technitium-1.1.0-r1.apk
```

更新后刷新 LuCI 页面。升级后台包会重启原先运行的服务，DNS 客户端会短时中断。升级前备份 `/etc/technitium/`。

## 构建和发布

本仓库是 OpenWrt 软件源，包含 `technitium/` 和 `luci-app-technitium/` 两个软件包目录。将本项目添加到 `feeds.conf.default`，安装软件源并选中 LuCI 插件，依赖关系会同时选中后台服务。

```text
src-git technitium https://github.com/jearton/luci-app-technitium.git
```

```sh
./scripts/feeds update technitium
./scripts/feeds install -a -p technitium
make menuconfig
make package/technitium/compile package/luci-app-technitium/compile V=s
```

发布固件时固定已验收的 tag 或 commit。`technitium/Makefile` 固定 DNS Server、Console 和运行时的版本及 SHA-256。

[Actions](https://github.com/jearton/luci-app-technitium/actions) 在 Linux 上使用 OpenWrt 25.12.6 SDK 构建三个 APK。隔离的 IPv4 x86 虚拟机测试旧版服务升级、运行状态和开机启动的四种组合、首次离线安装、端口冲突、DNS 记录和控制台登录。回归测试从 SHA-256 固定的旧版固件启动，软件包构建使用本项目和上游 OpenWrt SDK。

版本 tag 将三个 APK、本地 `packages.adb` 索引和校验文件发布到 [Releases](https://github.com/jearton/luci-app-technitium/releases) 和 [GHCR](https://github.com/jearton/luci-app-technitium/pkgs/container/luci-app-technitium)，并重新下载验证。

## 界面截图

**服务 → Technitium DNS**

使用 LuCI v1.0.2、Argon 主题和示例服务状态在 Chrome 渲染。

![Technitium DNS 的 LuCI 管理页，左侧为按文字宽度显示的控制台按钮](docs/luci-technitium.png)

**Technitium Console → Zones**

截图来自 x86/64 OpenWrt 实验环境中的 Technitium Console 1.4.2。

![Technitium Console 的域名区域列表](docs/technitium-console.png)
