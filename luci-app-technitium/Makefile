# SPDX-License-Identifier: GPL-3.0-or-later

include $(TOPDIR)/rules.mk

LUCI_TITLE:=LuCI integration for Technitium DNS Server
LUCI_DEPENDS:=+rpcd-mod-ucode +ucode-mod-fs +technitium
LUCI_EXTRA_DEPENDS:=technitium (>=15.6.2-r2)
LUCI_PKGARCH:=all
PKG_VERSION:=1.1.0
PKG_RELEASE:=1
PKG_LICENSE:=GPL-3.0-or-later

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
