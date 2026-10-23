# 插件皮肤交接 / Delegated skin handoff

## 当前状态 / Status

1.3.0 包含插件侧接入代码。**官方皮肤中心尚未注册 DIY 插件皮肤，也尚未提供下述选中标记。** 当前版本继续通过已有的 `diy-journal` 资源皮肤加载；安装本插件不会自动增加官方“插件皮肤”卡片。

Version 1.3.0 contains plugin-side support. The official Skin Center has not registered this delegated skin or adopted the explicit selection signal below. Existing installations continue using the `diy-journal` asset skin.

## 接口 / Contract proposal

- 插件根目录 `skin.json`：委托选择 ID 为 `diy-journal-plugin`，包名为 `@alphazerolan/dsh-plugin-diy-journal`，wiring ID 为 `ui-diy-journal`。`skin/skin.json` 仍是资源皮肤 `diy-journal`。
- **提议由皮肤中心维护** `html[data-dsh-delegated-skin]`，值为当前实际展示的委托皮肤 ID，包含临时试穿。默认外观、普通皮肤、壁纸接管或退出时清除；取消试穿时恢复原选择。插件只读取，绝不设置此标记。
- 插件运行时提供 `body[data-dsh-diy-journal]` 和 `body[data-dsh-diy-journal-handoff]`，表示客户端就绪和可交还外观。它们不表示正在绘制；实际绘制单独使用 `body[data-dsh-diy-journal-rendering]`。此语义已在本地皮肤中心接入分支实现，仍需上游审核。
- 仅当明确选中 `diy-journal-plugin`、普通皮肤标记为空或等于自己的委托 ID，且无 `body[data-we-wallpaper]` 时加载样式。样式由现有皮肤中心接口处理，沿用安装目录里的当前照片和布局。
- 切走后移除绘制标记与样式，停止视频和开场动画，并取消未完成加载；保留设置入口、用户文件和布局。旧版中心没有选中标记时不启动委托渲染。

The proposed center-owned `data-dsh-delegated-skin` attribute identifies the currently displayed delegated selection, including previews. Clear it for stock, asset skins, wallpaper takeover and shutdown; restore it when cancelling a preview. The plugin only reads this signal. The opt-in `selectionMode: explicit` also lets the center stamp `data-dsh-skin` with our delegated ID so legacy peers yield. Our renderer allows that own-ID claim. Plugin readiness/capability markers are distinct from the actual rendering marker. Switching away removes styles and media without deleting user data. Older centers remain on the asset-skin path.

## 上游接入仍需完成 / Remaining upstream work

1. 确认选中标记与就绪标记的契约，在页面启动注入和运行时切换中同时维护；只靠“没有普通皮肤标记”不能区分默认外观与不同插件皮肤。
2. 注册委托皮肤条目，补齐皮肤中心要求的多语言介绍，并验证安装、试穿、取消、应用、重启和卸载。
3. 确定官方安装来源。目前安装使用 GitHub/Release，**未发布同名 npm 包**；不能直接把包名作为可用的 npm 安装入口。需先发布包，或与维护者确认支持独立的安装来源字段。
4. 皮肤中心接入仍需上游审核、合并和发布。旧 1.2.0 Release 不包含本接口。

Upstream must agree on the contract, register/localize the entry and verify its lifecycle. The package is not published to npm: agree on an install-source mechanism or publish it before enabling one-click installation. The center integration still requires upstream review, merge and release.

## 已验证 / Verification

自动检查覆盖默认外观、其他资源皮肤、其他委托皮肤、壁纸接管、取消后迟到的响应、加载失败、资源释放及开场动画退出。浏览器隔离验证使用真实皮肤中心输出的样式，检查浅色/深色作用域与切走后清除；并已在独立 DSH 环境验证接入分支的实际卡片、试穿、取消、默认还原、应用和刷新恢复；不代表官方版本已经发布。

Automated checks cover switching, cancellation races, load failure, resource cleanup and intro teardown. An isolated browser harness uses real Skin Center stylesheet output to verify light/dark scopes and removal. An isolated live DSH also verifies the integration branch through real card selection, try-on, cancel, stock restore, apply and reload. This is not a claim of official availability.
