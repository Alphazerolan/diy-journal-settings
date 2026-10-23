# Changelog / 更新记录

## 1.3.0 — 2026-10-24

- 增加插件皮肤交接支持：独立描述文件、明确选中后绘制、切换后释放样式与媒体。官方选中信号及卡片注册仍待接入；旧版皮肤中心继续使用原资源皮肤路径。修正插件接管后的图片与字体路径，并让旧式插件皮肤正确让路。详见 [接入状态](docs/DELEGATED-SKIN.md)。
- Prepare delegated-skin handoff with an independent descriptor, explicit-selection rendering and style/media cleanup. Upstream selection signaling and registration are pending; older centers retain the asset-skin path. See [integration status](docs/DELEGATED-SKIN.md).

- 移除插件设置页重复的“使用官方默认”按钮，切换或恢复默认皮肤统一使用 DSH 皮肤中心；保留重新应用手账本与两种图片恢复功能。
- Remove the duplicate default-skin button from plugin settings; use DSH Skin Center to switch or restore skins. Keep journal reapplication and both artwork restore actions.

## 1.2.0 — 2026-10-23

- 样式菜单增加启动翻书动画开关，保存后生效；关闭自动开场仍可手动重播。
- 照片区域支持导入 MP4、自动生成封面，可与静态图片混排，沿用白边、胶带、题字、位置、角度和缩放。
- 菜单与实际皮肤共用视频拼贴渲染；默认静音循环，离开可视区域或减少动画时暂停，播放失败显示封面。
- 更新和恢复现用素材时保留动画偏好、视频与封面信息；内置纯皮肤版本维持 1.14.3。

English:

- Add a persistent global startup-animation switch to the style menu; turning it off skips early injection while keeping manual replay available.
- Preserve the animation preference through editor preparation and plugin updates.
- Support MP4 imports with browser validation and poster capture, alongside animated GIF photos.
- Share the video collage renderer between menu previews, scene previews and the integrated plugin; preserve photo borders, tape, captions, transforms and stacking.
- Pause offscreen/reduced-motion playback, release video resources on skin switch, and retain posters on playback failure.
- Restore installed videos with their poster metadata when preparing a new editor or recovering current artwork.

## 1.1.3 — 2026-10-23

- 开场提前到宿主页面注入阶段，与客户端加载并行；等待主界面就绪后淡出，取消客户端重复自动播放，超时及错误回退至原加载界面。浏览器检查通过，作者已确认本机启动效果。
- Start the intro through host page injections alongside client boot, wait for the UI before fading, remove duplicate late autoplay, and release the native loader on errors/timeouts. Browser verified; desktop startup appearance confirmed by the author.
- 接入 5 秒手账翻页开场，末尾淡出进入真实界面；设置页可重播，支持跳过及减少动画偏好。
- Add a five-second journal opening, fading into the live UI, with replay, skip and reduced-motion support.

## 1.1.2 — 2026-10-22

- 图片操作增加“打开文件夹”，直接打开当前区域目录，不改变当前选图。
- 分别恢复当前皮肤使用的图片、随插件附带的鲸鱼娘预设配图；更新当前区域预览，保存并应用后更新皮肤。
- 保留原有图片及布局，补充设置入口和新版样式菜单截图。

- Open the current area's photo folder without changing its selection.
- Restore photos from the installed skin or bundled Whale-chan presets independently; preview immediately and apply only on Save and apply.
- Preserve existing photo files and layouts; add settings-entry and updated editor screenshots.

## 1.1.1 — 2026-10-22

- 内置皮肤更新至 1.14.3，合并重复素材并对装饰图进行无损压缩。
- 同步编辑器模板与图片引用，避免保存后恢复旧文件引用；预览标题复用同一份素材。
- 字体、预设照片和用户自选图片保持原样；已有照片与布局继续保留。

- Bundle skin 1.14.3 with deduplicated assets and losslessly compressed decorations.
- Update editor templates and image references; reuse the title asset in previews.
- Keep fonts, preset illustrations and personal photos unchanged; preserve existing layouts.

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
