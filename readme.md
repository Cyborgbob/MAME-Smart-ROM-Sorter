# MAME Smart ROM Sorter v5.0 ![GitHub release](https://img.shields.io/github/v/release/Cyborgbob/MAME-Smart-ROM-Sorter?color=blue&label=Latest%20Release) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![Python](https://img.shields.io/badge/Python-3.x-blue) ![Project](https://img.shields.io/badge/Project-Home%20Arcade-orange)

**The Digital Broom for your MAME Arcade Collection.**

Created by **Shawn Flanagan / CyborgBob** for **Technically Not a Technician**, with Mr. Bob "Blocks" Cogito assisting as the AI planning and logic partner.

---

## Important: Windows virus warning / false positive

Because this program is a standalone Windows `.exe` created by an independent developer and packaged with PyInstaller, Windows Defender or another antivirus tool may warn you before launch.

That does **not automatically mean the app is malicious**.

- The Python source package is included so users can inspect the code.
- The app does not include ROMs, BIOS files, CHDs, samples, or game downloads.
- The app works on files and folders you already provide.
- If Windows blocks the app, click **More Info** and then **Run Anyway**, or build from source.

---

## What is this tool?

**MAME Smart ROM Sorter** helps home arcade builders turn a massive MAME set into a smaller, cleaner, purpose-built folder.

Instead of manually digging through thousands of ZIP files, you choose the kind of arcade setup you are building, and the sorter helps copy or hard-link the matching files into a new curated output folder.

This is meant for people building things like:

- A general-purpose arcade cabinet.
- A joystick/button cabinet.
- A couch/controller setup.
- A light gun-focused setup.
- A trackball-focused setup.
- A driving/racing-focused setup.
- A fighter-focused setup.
- A lean "best playable arcade games" style folder.

---

## What it does not do

MAME Smart ROM Sorter does **not** include, provide, link to, download, or distribute ROMs, BIOS files, CHDs, samples, or copyrighted game content.

You must provide your own legally obtained MAME files.

This project is a sorting/curation tool. It is not a ROM site, downloader, emulator, or legal shortcut.

---

## v5.0 highlights

- **Cleaner v5.0 code structure** with separated engine, GUI, and shared logic files.
- **Preset-driven workflow** for common cabinet/controller goals.
- **1G1R-style curation logic** to reduce redundant clones/regional duplicates.
- **God Mode metadata filtering** using MAME XML and optional support INI data.
- **Working arcade focus** to avoid stuffing your build with junk, gambling, fruit machines, and non-playable clutter.
- **Region and language preference logic** for better parent/clone selection.
- **CHD-aware export behavior** for games that need disk folders.
- **Portable deployment support** so the sorter can live beside or near a MAME install.
- **TNT personality layer** including app sounds, branding, and arcade-style presentation.

---

## Recommended ROM set type

For best results, use a **non-merged MAME ROM set**.

Why? A non-merged set is easier to curate because each game ZIP is more self-contained. Merged and split sets can work in some cases, but they are more likely to create missing parent, BIOS, device, sample, or CHD dependency problems after copying.

If a game still fails after sorting, check MAME's own error message first. The sorter may have copied the correct target ROM while MAME still needs a parent, BIOS, device ZIP, or CHD dependency.

---

## Quick start

1. Download `MAME_Smart_ROM_Sorter_v5.0.exe` from the GitHub release.
2. Place it in or near your MAME folder.
3. Launch the app and accept the startup agreement.
4. Point the app at your MAME metadata/support files when needed.
5. Choose a preset or build your own filter setup.
6. Choose your source ROM folder.
7. Choose your output folder.
8. Run the sorter.
9. Review the output folder and log files.
10. Test the curated folder in MAME or your front-end.

---

## Release download files

The GitHub release should include these files:

| File | Purpose |
|---|---|
| `MAME_Smart_ROM_Sorter_v5.0.exe` | Windows executable for normal users. |
| `MAME_Smart_ROM_Sorter_v5.0_Source.zip` | Source code, presets, required non-ROM assets, and build inputs. |
| `SHA256SUMS.txt` | Optional checksum file for verifying release downloads. |

---

## Visual user guide

The public repository already had a stronger visual guide than the stripped-down rebuilt README. This v5.0 README restores that style.

> Note: Some screenshots below come from the existing public GitHub README and may show the older v4.x interface. They still explain the workflow. Replace them with fresh v5.0 screenshots when final v5 screenshots are ready.

### 1. Welcome screen

The app opens with a themed welcome/agreement screen before doing any heavy work.

![Welcome Screen](https://github.com/user-attachments/assets/9e1b413c-6298-40da-a578-97cbc09c16ac)

### 2. Setup wizard / XML and INI helper

The sorter can help users understand required metadata like `full.xml` and the optional support INI files that improve filtering quality.

![Setup Wizard / XML and INI Helper](https://github.com/user-attachments/assets/3f9a5804-2e67-485e-8ba9-168a8cfa87c4)

### 3. Paths and configuration

Users connect the sorter to the MAME folder, source ROM folder, output folder, XML data, and support files.

![Paths and Configuration](https://github.com/user-attachments/assets/d784b252-729a-4117-95c2-8f5d9bed4622)

### 4. Controls and inputs

Filter around the controls you actually have: joystick, buttons, trackball, spinner, light gun, driving, and similar cabinet constraints.

![Controls and Inputs](https://github.com/user-attachments/assets/35a75146-1d53-4d27-9cbb-4ddeab0abed8)

### 5. Advanced filters

Use the deeper filters to remove clutter, prioritize playable arcade titles, and tune the set around your goals.

![Advanced Filters](https://github.com/user-attachments/assets/4f92c431-819b-4daa-8297-8a35709f0c99)

### 6. Genres and curation

Pick broad arcade categories, reduce unwanted genres, and shape the output toward the games you actually want to play.

![Genres and Curation](https://github.com/user-attachments/assets/af54a4ff-1b38-4018-b398-b65243f09df4)

### 7. Decades / era filtering

Build around an arcade era: 1970s black-and-white classics, 1980s golden age, 1990s fighters, or a wider all-era build.

![Decades / Era Filtering](https://github.com/user-attachments/assets/c1d7659c-c18f-43ef-9b52-283cba7d827e)

### 8. Regions and languages

Set region/language preferences so the sorter can make better parent/clone choices.

![Regions and Languages](https://github.com/user-attachments/assets/3d483e27-bd07-4519-9514-f233f658c9f6)

### 9. Operations and dashboard

Run the job, review logs, and check the final curated output folder before loading it into your emulator or front-end.

![Operations and Dashboard](https://github.com/user-attachments/assets/d1a26c58-940f-4e13-a5eb-b705ee6f4b4e)

---

## Included v5.0 presets and assets

The source package includes the v5.0 build assets needed to rebuild the current app package.

| Asset type | Examples |
|---|---|
| Preset JSON | `preset_v5.0.json`, `All.json`, `Controller.json`, `Lightgun.json`, `Trackball.json`, `driving.json`, `fighter.json` |
| Preset art | `All.png`, `Controller.png`, `Lightgun.png`, `Trackball.png`, `Driving.png`, `fighter.png` |
| App branding | `TNTLogo400by400.png`, `TNTicon256by256.ico`, `Polybius01.png`, `Polybius02.png`, `Download.png` |
| App sounds | `play_game.wav`, `game_over.wav`, `goodbye.wav` |
| Build files | `main.py`, `sorter_engine.py`, `sorter_gui.py`, `sorter_shared.py`, `MAME Smart ROM Sorter.spec` |

No ROMs or copyrighted game files are included.

---

## Frequently asked questions

### How do I sort and organize my MAME ROMs?

Point the tool at your MAME metadata and ROM folder, choose your filters or preset, and run the sorter. It creates a curated output folder based on your selected arcade goal.

### How do I remove MAME clones and create a 1G1R-style set?

Enable the 1G1R-style options and set region/language preferences. The sorter uses MAME parent/clone relationships and your preferences to reduce duplicate regional versions.

### Can I filter games by cabinet controls?

Yes. That is one of the main points of the tool. The sorter is built around practical arcade limits: controls, buttons, players, screen orientation, genre, working status, and cabinet-style goals.

### Why are some games still missing after sorting?

MAME can require parent ROMs, BIOS ZIPs, device ZIPs, CHDs, or samples. The sorter helps curate files, but it cannot magically fix an incomplete ROM set.

### Does the tool download ROMs?

No. It does not include or download ROMs, BIOS files, CHDs, samples, or copyrighted game content.

### Does it require the internet?

The sorter is designed around local processing. Some optional support metadata may come from public community data sources, but the tool itself is meant to sort files locally once the needed metadata is present.

### Why does Windows warn me?

Unsigned PyInstaller-built apps often trigger warnings. The source is included so users can inspect or rebuild it.

---

## Arcade Hall of Fame and resources

This project stands on the shoulders of giants. Thank you to the projects, developers, and communities that keep arcade history alive.

### Metadata and arcade data

- [ProgettoSnaps](https://www.progettosnaps.net/index.php) — CatVer, Mature, Series, and other support data.
- [AntoPISA MAME Support Files](https://github.com/AntoPISA/MAME_SupportFiles) — hosted MAME support INI repositories.
- [Controls.dat Project / ArcadeControls](https://controls.arcadecontrols.com/) — arcade control metadata.
- [Arcade Database / ADB](http://adb.arcadeitalia.net/) — MAME reference data and arcade encyclopedia.
- [NPlayers](https://nplayers.arcadebelgium.be/) — player-count and multiplayer behavior data.

### Core emulation

- [MAMEdev](https://www.mamedev.org/) — preserving arcade and computing history.
- [MAME Wiki](https://wiki.mamedev.org/index.php?title=Main_Page) — MAME technical documentation.

### Friends, inspirations, and community

- [Rogue Synapse](http://www.roguesynapse.com/games/last_starfighter.php) — keeping the Last Starfighter dream alive.
- [Team Encoder](https://www.team-encoder.com/) — arcade modding and hardware hacking.
- [Sinnesloschen / Polybius](http://www.sinnesloschen.com/) and [Polybius Archive](https://www.coinop.org/game/103223/polybius) — because the truth is out there.
- [Houston Arcade Expo](https://www.houstonarcadeexpo.com/) — one of the best arcade shows on earth.

### Project credits

- **Shawn Flanagan / CyborgBob** — project owner, creator, testing, direction, and release lead.
- **Technically Not a Technician** — channel and public project home.
- **Mr. Bob "Blocks" Cogito** — AI planning, documentation, and code-assist partner.
- **Community testers and commenters** — feature feedback, bug reports, and arcade cabinet reality checks.

---

## TNT links and video guides

- [Technically Not a Technician website](https://www.technicallynotatechnician.com/)
- [Subscribe on YouTube](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1)
- [Buy Me a Coffee](https://buymeacoffee.com/technicallynota)
- [Smart ROM Sorter Setup Guide](https://youtu.be/GAOdZ947ofs)
- [ROMLister Filtering Guide](https://youtu.be/IXWbLji_5Jo)
- [Arcade Database Hack Guide](https://youtu.be/KvEklx52CsI)
- [ClrMamePro Conversion Guide](https://youtu.be/miXMtHDUeb0)

---

## License summary

MSRS v5.0 uses a simple split-license model:

- **Source code:** MIT License. See `LICENSE`.
- **Documentation:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 unless a file says otherwise.
- **TNT / Technically Not a Technician branding, logos, icons, preset images, screenshots, Polybius images, WAV sounds, video assets, and other non-code creative assets:** reserved by Shawn Flanagan / Technically Not a Technician unless otherwise stated.
- **MAME / game content:** no ROMs, BIOS files, CHDs, samples, or copyrighted game files are included, linked, downloaded, or distributed.

You may use the bundled assets as part of running, testing, documenting, or rebuilding MAME Smart ROM Sorter. You may not reuse them to impersonate Shawn/TNT, imply endorsement, rebrand another project, or sell/distribute them as a standalone asset pack.

See `LICENSE`, `LICENSE_OVERVIEW.md`, `ASSET_LICENSE_NOTES.md`, and `THIRD_PARTY_NOTICES.md` for the release package notes.

