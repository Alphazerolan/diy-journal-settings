# Changelog / 更新记录

## 1.1.0 — 2026-10-22

- 将独立样式菜单升级为标准 DSH 一体化插件，内置 DIY 手账本皮肤 1.14.2。
- 在设置页应用皮肤、切换官方默认外观、打开本地照片与布局编辑器。
- 首次加载准备皮肤；更新时保留自选照片、布局和本地修改，替换前备份旧文件。
- 切换皮肤时清理并重新挂载动态效果；停止插件时关闭菜单服务。
- 菜单需要 Python 3.9+；皮肤渲染需要启用皮肤中心。仅支持编辑 DIY 手账本。
- 旧脚本安装用户请先按 README 移除旧入口，再安装新版，避免重复加载。

English:

- Upgrades the standalone editor to a standard DSH bundle with DIY Journal skin 1.14.2.
- Apply the skin, switch to the official default, and open the local editor from Settings.
- Provision the skin on first load; preserve personal photos, layouts and local edits during upgrades, with backups before replacement.
- Clean up and restore dynamic effects on skin switches; stop the menu service when the plugin stops.
- Requires skin-center for rendering and Python 3.9+ for editing. Edits DIY Journal only.
- Legacy script installations must remove the old entry as documented in the README before upgrading.
