# DIY Journal: skin and style menu

English | [中文](README.zh.md)

A notebook-inspired skin for DeepSeek Harness (DSH), restyling as many interface
components as the developer could think of—from the home screen, sidebars and
conversation bubbles to menus, cards and tool panels. [See the preview](#preview).

To bring the freedom of a scrapbook to the skin, this plugin bundles **DIY Journal
skin 1.14.3 and its style menu** in one installation. Use **Settings > DIY Journal**
to apply it, adjust layouts and styles in each area, replace images, and combine
tape, photo borders and captions to make the journal your own.

[Download plugin 1.1.3](https://github.com/Alphazerolan/diy-journal-settings/releases/tag/v1.1.3) ·
[Standalone skin and component gallery](https://github.com/Alphazerolan/diy-journal-skin) ·
[Changelog](CHANGELOG.md)

This repository upgrades the former standalone editor into a skin-and-editor
bundle. It edits DIY Journal only, not arbitrary skins. The standalone skin
remains available for users who only need its appearance.

## Skin and DIY features

- **Paper and hand-drawn styling:** handwritten headings, notebook pages and binder rings, tape collages, light/dark palettes, and 14 separately themed ChatGPT-generated Whale-chan illustrations.
- **Specially designed components:** user notes and reply stationery, session paper planes, notification envelopes and their expanded state, collapsed sessions, workspace hover information, task board, account card, and an address-book remote-access dialog. [Explore the static component gallery by function](https://github.com/Alphazerolan/diy-journal-skin/blob/main/docs/COMPONENTS.md).
- **Per-area collages:** choose photos and layouts for the home screen, sidebars and settings pages; adjust position, rotation, scale, tape colors/patterns, narrow/wide borders and captions.
- **Two-photo and no-photo layouts:** swap photo order and overlap; choosing no photo collapses the photo area without leaving an empty placeholder.
- **Scene previews:** preview the corresponding home or settings area in the menu, then save and refresh DSH to apply. Personal photos stay local.

## Style menu

Open the editor from **Settings > DIY Journal**.

![DIY Journal entry in DSH Settings](docs/images/diy-settings-entry.png)

- **Open folder:** opens the current area's photo directory without changing the selection. Use Choose image to select files added there.
- **Restore current skin photos:** reads the photos currently used in the installed DIY Journal skin for this area and restores them into the editor preview.
- **Restore Whale-chan presets:** restores the bundled illustrations shown in the gallery for this area.

Both restore actions affect the current area only, retaining existing photo files and layout settings. If No photo is selected, restoring an image enables the single-tape layout so it is visible. **The skin changes only after Save and apply**; refresh DSH afterwards.

The screenshot below shows the running updated editor. The skin scene at its bottom uses static sample content.

![Style menu with image selection, folder access, both restore actions and scene preview](docs/images/diy-style-menu.png)

## Preview

These are existing actual DSH window captures from the skin repository, retaining its redacted presentation. They show the bundled skin's appearance; layout can vary with DSH version, window size and content. See the [static component gallery](https://github.com/Alphazerolan/diy-journal-skin/blob/main/docs/COMPONENTS.md) for more specially designed components.

### Home · Light

![Light home](docs/images/diy-journal-light.jpg)

### Home · Dark

![Dark home](docs/images/diy-journal-dark.jpg)

### Conversation bubbles · User and DeepSeek replies

User messages use blue grid-paper notes. DeepSeek replies use lined paper with a handwritten signature and a paper clip. These actual window captures retain the full sidebar with personal information hidden. Each theme was selected in the app before capture.

**Light**

![Actual light window with user and DeepSeek reply bubbles](docs/images/diy-journal-messages-light.jpg)

**Dark**

![Actual dark window with user and DeepSeek reply bubbles](docs/images/diy-journal-messages-dark.jpg)

### Settings · Light

![Light settings](docs/images/diy-journal-settings-light.jpg)

### Settings · Dark

![Dark settings](docs/images/diy-journal-settings-dark.jpg)

## Requirements

- DSH 0.2.1-rc.2 or newer, with skin-center installed and enabled.
- Verified on Windows. The editor needs Python 3.9+ (standard library only).
  The skin still works without Python.
- Distributed through GitHub Releases; not yet published to npm or listed in Workshop.

## Install

Download the `.tgz` from the link above and install it with the standard plugin manager:

```powershell
dsh plugin --profile desktop add "C:/Downloads/alphazerolan-dsh-plugin-diy-journal-1.1.3.tgz"
```

Use `web` instead of `desktop` for Web profiles. Fully restart that DSH instance.
Use **Settings > DIY Journal > Apply Journal**, or choose it in skin-center.
Apply persists the selection and reloads the page. No CMD or Python installer
needs to be run. Python is detected automatically; `DIY_JOURNAL_PYTHON` can
specify an absolute executable path.

The plugin carries the skin assets; skin-center continues to render them.
A delegated-skin registration is not required.

## Migrate from the old local editor

If the old entry was installed with `python install.py`, run
`python install.py --uninstall` from that directory before installing this bundle
and restarting. Do not load both entries. Personal data and the skin are retained.

## Data, updates and disabling

- Skin: `$DSH_HOME/skins/diy-journal`; respects `DSH_SKINS_HOME` / `DSH_SKINS_DIR`.
- Photos/layouts: `$DSH_HOME/diy-journal-editor`, outside the plugin package.
- First editor launch extracts defaults; subsequent launches preserve photos,
  layouts and explicit empty selections.
- Updates replace only files matching previous shipped defaults. Local edits
  are preserved and reported. Previous files are backed up under
  `$DSH_HOME/diy-journal-editor-backups`.
- Existing manual installs are adopted conservatively: unknown differences
  stay unchanged. Preserved files do not receive upstream changes to those files.
- When custom or extra files exist, retain older assets that they may reference. A customized installation may therefore use more space than a fresh install.
- Saving only updates DIY Journal; it never selects it over another active skin.
- Switching away cleans the plugin's state markers; switching back mounts them.
- Disabling/uninstalling closes the menu and enhancements, retaining the asset
  skin and personal data. Select another skin or **Use official default** first
  to also remove its appearance.

The menu is loopback-only, with random tokens, origin checks and a 20-minute
idle timeout. Photos are never uploaded.

## Artwork and character credits

The 14 default illustrations were generated with ChatGPT; themes and records are in [ARTWORK.json](skin/ARTWORK.json). They depict **DeepSeek 鲸鱼娘（大肥鱼）/ Whale-chan**. Original character design is credited to [上善](https://www.pixiv.net/users/62155430), the DeepSeek maid redesign to [ZipZipPipe](https://www.pixiv.net/users/18604994), and this skin's illustration generation, journal layout and integration to Alphazerolan. See [NOTICE](skin/NOTICE) for sources and scope.

This is an unofficial fan work; character redistribution permission has not been independently verified. AI generation does not establish character authorization. Bundled illustrations and character artwork are for personal, non-commercial use only, and third-party rights remain with their holders. Fonts retain their OFL licenses; code is [MIT](LICENSE).

## Development

```sh
npm run build
npm test
npm run test:python
npm pack
```

`client.js` is generated from `src/` and the bundled state projector. Asset-skin
provenance checks stay intact. Only code shipped in this plugin is executed,
never arbitrary scripts from the user's skin directory.
Code is MIT; asset terms are in [NOTICE](NOTICE) and [skin/NOTICE](skin/NOTICE).

### Journal opening animation

With DIY Journal active, DSH's early page injections start the five-second opening alongside client plugin loading. It fades out once the live UI is ready; if the video ends first, its last frame remains briefly while loading continues. Timeouts and failures release the normal loading screen. The ordinary client no longer starts a second automatic playback. Skip with the on-screen button or Escape; replay from Settings → DIY Journal. Reduced-motion preferences are respected. Playback is provided by this plugin, not the standalone skin package.

This starts after the host supplies its boot injections, so it cannot cover earlier Electron or host startup. The early-injection version has passed browser checks, and the author has confirmed the startup appearance on their desktop.
