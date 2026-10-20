# DIY Journal settings plugin

[中文说明](README.zh.md)

Independent local companion plugin for the [DIY Journal skin](https://github.com/Alphazerolan/diy-journal-skin).
It adds **Settings > DIY Journal > Open style menu** to DeepSeek Harness.
Windows desktop support; Python 3.9+ required. No npm installation or API key is needed.

## Install

1. Install and select the DIY Journal skin first.
2. Download this repository and extract it to a permanent directory.
3. Run `python install.py` from that directory, then restart Harness.
4. Open Settings > DIY Journal. Choose photos and layouts, then Save and apply.
   Refresh Harness or reselect the skin to see the result.

For a custom data directory, use `python install.py --dsh-home "PATH"`.
The installer backs up and updates only its marked entry in the desktop profile's
`cordis.patch.yml`. It does not patch application binaries. Keep the plugin directory
in place; after moving it run the installer again. Python is detected during install,
so no developer-machine path is shipped.

## Data and updates

The first install creates `$DSH_HOME/diy-journal-editor`, initializes layouts and
extracts the skin's bundled generated images into that workspace. User photos,
layouts and explicit empty selections survive subsequent installer runs. Upgrade
the skin separately; plugin upgrades do not reset personal photos. Runtime paths
are local and ignored by Git. No user photos or credentials are bundled here.

The menu is a loopback HTTP service with a random per-launch token, origin/host
checks and a 20-minute idle timeout. It never uploads photos. Saving updates only
the DIY Journal skin. Host updates can require plugin API adaptation.

## Uninstall

Run `python install.py --uninstall`, then restart Harness. This removes only the
marked plugin entry and keeps the skin, backups and personal workspace.

## Development

`node --test tests/*.test.mjs` and `python tests/test_install.py`.
Code is MIT; copied paper/tape decorations and fonts retain the skin's NOTICE.
UI strings currently use Chinese; this repository includes bilingual instructions.
