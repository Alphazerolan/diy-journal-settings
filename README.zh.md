# DIY 手账本设置插件

[English](README.md)

独立于皮肤的本地插件，在 Harness 中增加“设置 → DIY 手账本 → 打开样式菜单”。
适用于 Windows 桌面版，需要 Python 3.9 或更新版本，无需 API 密钥或 npm 安装。

## 安装

1. 先安装并选择 [DIY 手账本皮肤](https://github.com/Alphazerolan/diy-journal-skin)。
2. 下载本仓库并解压到长期保留的目录。
3. 在该目录运行 `python install.py`，然后重启 Harness。
4. 从设置页打开样式菜单，选择图片与布局，点击“保存并应用”，再刷新 Harness。

自定义数据目录可使用 `python install.py --dsh-home "目录"`。
安装器会备份桌面配置，只更新自己标记的插件入口，不修改程序文件。
插件目录移动后重新运行安装器即可；Python 路径在本机安装时检测，不预置开发者路径。

## 图片与更新

首次安装会在 `$DSH_HOME/diy-journal-editor` 创建独立工作目录，读取皮肤中已嵌入的
默认配图并初始化布局。后续安装保留已选择的照片、布局和明确选择的空白状态。
皮肤需单独更新；更新插件不会重置个人照片。仓库不包含个人照片或登录资料。

菜单仅监听本机地址，使用随机令牌和来源校验，闲置 20 分钟退出，不上传照片。
支持图片选择、布局、双照片、胶带、位置／角度／缩放、宽窄白边和题字、场景预览。
保存只更新 DIY 手账本。Harness 升级后如接口变化，插件可能需要适配。

## 卸载

运行 `python install.py --uninstall` 后重启 Harness。只移除本插件入口，保留皮肤、
配置备份和个人工作目录。

## 开发验证

运行 `node --test tests/*.test.mjs` 和 `python tests/test_install.py`。
代码使用 MIT；装饰与字体保留各自声明。菜单目前为中文，安装说明提供中英双语。
