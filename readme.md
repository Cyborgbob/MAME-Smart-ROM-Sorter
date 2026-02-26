# MAME Smart ROM Sorter (GUI + CLI) 🚀

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Cyborgbob/MAME-Smart-ROM-Sorter?color=blue&label=Latest%20Release)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![GitHub License](https://img.shields.io/github/license/Cyborgbob/MAME-Smart-ROM-Sorter?color=green)

**The Digital Broom for your MAME Arcade Collection.** *Created by Shawn Flanagan & Mr. Bob "Blocks" Cogito (AI Thinking System)*

---

## 🚨 IMPORTANT: Windows Virus Warning (False Positive)
Because this program is a standalone `.exe` built by independent creators and not signed by a massive corporation, **Windows Defender will likely flag this as a virus.**

* **This is a False Positive.** The Python source code is included in this repository for you to audit.
* **To Run:** Click **"More Info"** -> **"Run Anyway"** or add the `.exe` to your antivirus exclusion list.

---

## What is This Tool? 🤔
The **MAME Smart ROM Sorter** turns an overwhelming, multi-thousand-file MAME set into a **clean, curated, arcade-only collection** perfectly tailored to your hardware limits.

### ✨ v4.74 Featured Upgrades
* **Custom "TNT" Icon:** Includes the new custom arcade cabinet branding for a professional desktop experience.
* **"Couch Co-op" Ready:** Defaults to a modern controller preset (4 Players / 8 Buttons).
* **God Mode Metadata:** Integrates ProgettoSnaps and Controls.ini to definitively separate "Real Arcade" games from junk devices, slot machines, and mahjong boards.
* **Hardware-Aware Engine:** Automatically identifies and copies required BIOS sets, CHDs, and Audio Samples needed for your specific collection.

---

## 🛠️ Visual User Guide (Step-by-Step)

### 1. The Welcome Screen
Upon launch, you'll be greeted by the Joshua-inspired splash screen. Click **Agree & Continue** to proceed.

> 🔊 **Experience the Nostalgia:** Upon launch, the app greets you with the classic `play_game.wav` cue: *"Do you want to play a game?"*

<img width="1919" height="1079" alt="4 74 Welcome" src="https://github.com/user-attachments/assets/9e1b413c-6298-40da-a578-97cbc09c16ac" />

### 2. The Setup Wizard (First Run)
If run from your MAME root, the app detects missing files. It offers to command MAME to build your `full.xml` and download 13 curated "God Mode" metadata files directly from the GitHub community.

<img width="1919" height="1079" alt="4 74 XML   ini Pimp" src="https://github.com/user-attachments/assets/3f9a5804-2e67-485e-8ba9-168a8cfa87c4" />

### 3. Paths & Configuration
Verify your source and output directories. This links your ROMs to the metadata databases for advanced filtering.

<img width="1919" height="1079" alt="4 74 Path" src="https://github.com/user-attachments/assets/d784b252-729a-4117-95c2-8f5d9bed4622" />

### 4. Controls & Inputs
New in v4.74, settings default to a **Couch Co-op** state. Enable **Strict Control Filtering** to ensure you only get games your cabinet hardware can actually play.

<img width="1919" height="1079" alt="4 74 controls" src="https://github.com/user-attachments/assets/35a75146-1d53-4d27-9cbb-4ddeab0abed8" />

### 5. Advanced Game Filters
The brain of the **1G1R (One Game, One ROM)** engine. Pick the absolute best version of every game, eliminating hundreds of redundant clones.

<img width="1919" height="1079" alt="4 74 Filters" src="https://github.com/user-attachments/assets/4f92c431-819b-4daa-8297-8a35709f0c99" />

### 6. Hierarchical Genre Curation
Browse categories with full **mouse-wheel support**. Essential genres like **Fighters** and **Shooters** are pinned to the top with game examples (Pac-Man, Galaga) to make selection intuitive.

<img width="1919" height="1079" alt="4 74 genres" src="https://github.com/user-attachments/assets/af54a4ff-1b38-4018-b398-b65243f09df4" />

### 7. Release Decades
A dedicated tab to filter by era. Want only the 1980s golden age? Uncheck the rest and keep your set era-accurate.

<img width="1915" height="1079" alt="4 74 Decades" src="https://github.com/user-attachments/assets/c1d7659c-c18f-43ef-9b52-283cba7d827e" />

### 8. Regions & Languages
Set your regional priority (e.g., USA > World > Japan). The 1G1R engine uses this list to decide which version of a game is the "best" for your collection.

<img width="1919" height="1079" alt="4 74 Regions" src="https://github.com/user-attachments/assets/3d483e27-bd07-4519-9514-f233f658c9f6" />

### 9. Operations & Dashboard
Save your configuration as a `.json` preset, then hit the orange button to begin. 

> 🏆 **The Finish Line:** When the sorting operation is successfully completed, you are rewarded with the final `game_over.wav` cue!

<img width="1919" height="1079" alt="4 74 Operations" src="https://github.com/user-attachments/assets/d1a26c58-940f-4e13-a5eb-b705ee6f4b4e" />

---

## 🚀 How to Run (Quick Start)
1. Drop `MAME_Smart_ROM_Sorter_v4.74.exe` into your main MAME directory.
2. Launch and let the **Setup Wizard** gather your files.
3. Select your hardware limits and preferred genres.
4. Click **"🚀 RUN MAME SMART SORTER"**.
5. Check `filter_log.txt` when done to see a full audit of your new set!

---

## 🏛️ The Arcade Hall of Fame & Resources
This tool stands on the shoulders of giants. We want to extend a massive **Thank You** to the following projects, developers, and communities that keep the arcade dream alive. 

### The Data Gods (Metadata Providers)
* 🗄️ **[ProgettoSnaps](https://www.progettosnaps.net/index.php)**: The legendary Italian database providing the core CatVer, Mature, and Series categorizations.
* 📦 **[AntoPISA GitHub](https://github.com/AntoPISA/MAME_SupportFiles)**: For hosting the automated INI repositories.
* 🕹️ **[Controls.dat Project (ArcadeControls)](https://controls.arcadecontrols.com/)**: The absolute gold standard for mapping arcade hardware inputs to MAME XML.
* 🗄️ **[Arcade Database (ADB)](http://adb.arcadeitalia.net/)**: The ultimate web-based MAME encyclopedia by ArcadeItalia.
* 👥 **[NPlayers (Belgium)](https://nplayers.arcadebelgium.be/)**: For determining true simultaneous multiplayer vs. alternating play.

### The Titans (Core Emulation)
* 👾 **[MAMEdev Official](https://www.mamedev.org/)**: For preserving video game history.
* 📖 **[MAME Wiki](https://wiki.mamedev.org/index.php?title=Main_Page)**: The ultimate technical resource.

### The Legends & Friends of the Channel
* 🚀 **Doc from [Rogue Synapse](http://www.roguesynapse.com/games/last_starfighter.php)**: Keeping the *Last Starfighter* dream alive.
* 🔥 **[Team Encoder](https://www.team-encoder.com/)**: Legends in arcade modding and hardware hacking.
* 👁️ **[Sinnesloschen (Polybius)](http://www.sinnesloschen.com/)** & **[Polybius Archive](https://www.coinop.org/game/103223/polybius)**: Because the truth is out there.
* 🕹️ **[Houston Arcade Expo](https://www.houstonarcadeexpo.com/)**: One of the best arcade shows on earth.

### The Architects & Testers
* **Mr. Bob "Blocks" Cogito**: Co-creator and AI Logic Engine.
* **TravisK-i1e**: Setup Wizard inspiration.
* **Marcus**: 2-Way Joystick and Decades filter logic.
* **@johnmclain250**: 1G1R engine testing and bug hunting.

### TNT Official Links & Video Guides
* 🌐 **[TNT Official Website](https://www.technicallynotatechnician.com/)**
* 🎥 **[Subscribe on YouTube](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1)**
* ☕ **[Buy Me a Coffee](https://buymeacoffee.com/technicallynota)**
* ▶️ **[Smart ROM Sorter Setup Guide](https://youtu.be/GAOdZ947ofs)**
* ▶️ **[ROMLister Filtering Guide](https://youtu.be/IXWbLji_5Jo)**
* ▶️ **[Arcade Database Hack Guide](https://youtu.be/KvEklx52CsI)**
* ▶️ **[ClrMamePro Conversion Guide](https://youtu.be/miXMtHDUeb0)**

---

## 📜 License
Licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International**.
Copyright (c) 2025-2026 Shawn Flanagan.
