# DIY 手账本：皮肤与样式菜单

[English](README.md) | 中文

标准 DSH 插件包，内置 DIY 手账本皮肤 1.14.2 和本地样式菜单。
首次加载自动准备皮肤；在 **设置 → DIY 手账本** 应用外观、打开菜单，
选择照片，调整布局、角度、缩放、胶带、白边和题字。

[下载插件 1.1.0](https://github.com/Alphazerolan/diy-journal-settings/releases/tag/v1.1.0) ·
[纯皮肤版本与组件展示](https://github.com/Alphazerolan/diy-journal-skin) ·
[更新记录](CHANGELOG.md)

本仓库由原来的独立样式菜单升级为一体化插件。仅调整 DIY 手账本，
不是适用于所有皮肤的通用编辑器。只需要外观时，可以继续使用纯皮肤版本。

![DSH 实际窗口中的内置皮肤](docs/images/home.png)

## 环境要求

- DSH 0.2.1-rc.2 或更新版本，已安装并启用皮肤中心。
- Windows 已验证。菜单需要 Python 3.9+，只使用标准库；没有 Python 时皮肤仍可使用。
- 通过 GitHub Releases 提供安装包；尚未发布 npm 或登记工坊。

## 安装

从上方下载入口取得 `.tgz` 文件，再通过标准插件管理方式安装，例如桌面档案：

```powershell
dsh plugin --profile desktop add "C:/Downloads/alphazerolan-dsh-plugin-diy-journal-1.1.0.tgz"
```

Web 用户将 `desktop` 换成 `web`。完全退出并重启对应 DSH 实例，打开
**设置 → DIY 手账本 → 应用手账本**。应用按钮保存选择并刷新页面；
也可在皮肤中心切换。无需运行 CMD 或 Python 安装脚本。
Python 自动检测，特殊环境可设置 `DIY_JOURNAL_PYTHON` 为其绝对路径。

本插件自带皮肤资产，渲染沿用皮肤中心，不需要委托皮肤登记。

## 旧版迁移

如果以前运行过 `python install.py` 安装本地入口，先在旧插件目录运行
`python install.py --uninstall`，再安装本包并重启。不要同时加载两个入口。
这只移除旧入口，保留照片、布局及皮肤。

## 数据、更新与停用

- 皮肤默认在 `$DSH_HOME/skins/diy-journal`，尊重 `DSH_SKINS_HOME` / `DSH_SKINS_DIR`。
- 照片与布局在 `$DSH_HOME/diy-journal-editor`，不放在插件安装目录。
- 首次打开菜单提取预设插画；以后保留自选照片、布局和明确的空图选择。
- 更新只替换仍与旧版预设一致的皮肤文件；本地定制保留并提示。
  原文件备份至 `$DSH_HOME/diy-journal-editor-backups`。
- 对原有手工安装的皮肤保守接入，不能确认来源的差异不覆盖。
  被保留的定制文件也不会自动获得新版对同一文件的改进。
- 菜单保存只更新 DIY 手账本，不会切走正在使用的其他皮肤。
- 切走皮肤清理插件动态标记，切回重新挂载。
- 停用或卸载插件关闭菜单服务及附加效果，保留资产皮肤与个人数据。
  要同时停用外观，先选择其他皮肤或点击“使用官方默认”。

菜单仅监听本机，具有随机令牌、来源检查和 20 分钟空闲退出，不上传照片。

## 开发

```sh
npm run build
npm test
python tests/test_install.py
npm pack
```

`client.js` 从 `src/` 和随包状态投影逻辑生成。原皮肤来源审查机制保持不变；
插件只运行随插件发布的代码，不加载用户皮肤目录中的任意脚本。
代码 MIT；素材条款见 [NOTICE](NOTICE) 和 [皮肤声明](skin/NOTICE)。
