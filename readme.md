# MAME Smart ROM Sorter (GUI + CLI) 🚀

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Cyborgbob/MAME-Smart-ROM-Sorter?color=blue&label=Latest%20Release)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![GitHub License](https://img.shields.io/github/license/Cyborgbob/MAME-Smart-ROM-Sorter?color=green)

<img width="1918" height="1078" alt="Screenshot 2026-02-22 180435" src="https://github.com/user-attachments/assets/eb837374-7b80-468d-8140-09252e1beef8" />


**Status:** ✅ House Tested & Looking for external Testers!

## 🚨 IMPORTANT: Windows Virus Warning (False Positive)

**Please Read Before Downloading:**
Because this program is a standalone `.exe` created by a solo developer (Technically Not a Technician & Bob Cogito "AI Thinking System") and not a large corporation, it does not have a digital signature. **Windows Defender and other antiviruses will likely flag this as a virus.**

* **This is a False Positive.**
* The code is **Open Source** (included in this repository) so you can verify it yourself.
* It does nothing but read your XML, filter your list, and copy your files.
* **To Run:** Click "More Info" -> "Run Anyway" or add the folder to your exclusion list.

---

## What is This Tool? 🤔

The **MAME Smart ROM Sorter** is your "digital broom" for MAME collections. If you’ve ever downloaded a full MAME set, you know it’s packed with thousands of files you don't need: console games (SNES, Genesis), calculators, mahjong/casino games, non-working prototypes, and endless duplicates.

This tool turns that overwhelming mess into a **clean, curated, arcade-only collection** perfectly tailored to your arcade cabinet or gamepad setup.

### ✨ Features & Upgrades

* **Smart Setup Wizard:** Drop the `.exe` in your MAME folder, and the tool will automatically command MAME to generate your `full.xml` and auto-download the latest `catver.ini` directly from GitHub!
* **Smart Update Checker:** The tool silently checks GitHub on startup so you never miss a new version.
* **Set Type Detection:** The engine actively scans your ROMs to ensure you are using a **Non-Merged set**, warning you if it detects incompatible Split or Merged files.
* **Strict 1G1R (One Game, One ROM):** The tool intelligently groups games by family and picks the *absolute best* version based on your preferred Region and Language priority list.
* **Hardware-Aware Dependency Engine:** It doesn't just copy the game ROM. It automatically identifies and copies required **BIOS sets**, **CHDs (Hard Drives)**, **Devices**, and **Audio Samples** needed to make the game actually run!
* **Missing Assets Audit:** Generates a detailed Audit Report in the log telling you *exactly* which files are missing from your source folder so you can go find them.
* **Granular Filtering:** Filter by Max Buttons, Control Type (Lightgun, Trackball, Analog), Screen Orientation, Release Decade, and Emulation Status (Working vs. Imperfect).

---

## 📜 Version History (v4.20 to v4.45 Highlights)

Since the last public release (v4.20), the engine has undergone massive upgrades. Here are the major milestones:

* **v4.45 (The Experience Update):** Added native Windows background audio for that classic '80s hacker/arcade vibe, and completely eradicated "Ghost Files" and dummy devices from the Missing Assets log.
* **v4.42 (The Community Update):** Introduced the GitHub Smart Update Checker and expanded the Operations Dashboard to include direct links to essential MAME community resources and local arcades.
* **v4.36 (The Polish Update):** Added a real-time, determinate Progress Bar and live file counter for the copying phase.
* **v4.35 (The Automation Update):** Introduced the Front-Loaded Smart Setup Wizard to automatically fetch missing `full.xml` and `catver.ini` files on startup.
* **v4.31 (The Time Machine Update):** Added robust Decade Filtering to bucket games by release era (Pre-1970s through 2020s).
* **v4.29 (The Safety Update):** Built the Set Type Detector to warn users if they accidentally try to use incompatible Split or Merged ROM sets. Added Hard Drive space validation to prevent crashes.
* **v4.21 (The 1G1R Update):** Replaced brute-force XML parsing with high-speed memory streaming. Introduced the **One Game, One ROM** engine and the true hardware Dependency Graph (BIOS/Devices).

---

## 🧐 Before You Begin: What is MAME? (For the Complete Novice)

* **MAME:** The emulator program that plays the arcade games (does many other things too). Our tool *organizes* the arcade files for MAME, but it is not MAME itself.
* **ROM:** The digital copy of the arcade game (e.g., `pacman.zip`).
* **Non-Merged ROM Set:** This is the type of collection our tool explicitly needs. Every game zip file must be "complete" and self-contained.

---

## 🛠️ Prerequisites & Placement

**WHERE TO PUT THE TOOL:** This program is designed to be placed and run **directly inside the root of your MAME folder** (where your `mame.exe` lives). While you *can* run it from anywhere and manually point it to your directories, running it from the MAME root allows the Smart Setup Wizard to automate the heavy lifting for you.

To use the sorter, you need **three** files & a working MAME install with a Full Non-Merged ROMSET:
1. **The Tool:** `MAME_Sorter.exe` (📥 [Download the Latest Release Here](https://github.com/Cyborgbob/MAME-Smart-ROM-Sorter/releases/latest)).
2. **The Brain:** `full.xml` (Your machine's map. *The app can auto-generate this if placed in the MAME root!*)
3. **The Filter:** `catver.ini` (*The app can auto-download this if placed in the MAME root!*)

---

## 🚀 How to Use (Step-by-Step)

1. **Prepare Your Folder:** Drop `MAME_Sorter.exe` into your main MAME directory.
2. **Launch & Setup:** Double-click the `.exe`. Click Agree on the Welcome Screen, then let the Smart Setup Wizard fetch/generate your XML and INI files.
3. **Navigate the Tabs:**
   * **Paths & Config:** Verify your Source ROMs folder and set an Output Base folder.
   * **Controls:** Tell the app what hardware you have (e.g., "Max 2 Players, 6 Buttons, Joysticks only").
   * **Filters:** Select your Emulation Status (e.g., Working Only) and enable **1G1R**.
   * **Genres & Decades:** Uncheck the eras or game types you hate (e.g., Sports, Casino).
   * **Locales:** Move your preferred languages/regions to the right box.
4. **Operations:** Save your preset for later, and click **"🚀 RUN MAME SMART SORTER"**.
5. **Review the Audit:** When finished, check the `filter_log.txt` file. It acts as a comprehensive pipeline summary and will list any files you are missing!

---

## 👨‍💻 For Developers (Running from Source)

Want to run the raw Python code instead of the `.exe`?

1. Ensure **Python 3.8+** is installed on your system.
2. The GUI requires `tkinter`. This is usually bundled with Windows Python installers, but Linux users may need to run `sudo apt-get install python3-tk`.
3. Run the script: `python mame_sorter_tkinterv4.45.py`

---

## 📺 Helpful Resources, Links & Guides

Built right into the Operations Tab, we've provided a massive ecosystem dashboard to help you:

**TNT Official Guides:**
* 🌐 [TNT Official Website](https://www.technicallynotatechnician.com/)
* ▶️ [MAME ROMs Made Easy](https://youtu.be/KvEklx52CsI)
* ▶️ [ROM Filtering Guide](https://youtu.be/IXWbLji_5Jo)
* 🛠️ [ClrMamePro Guide (Convert your ROM sets!)](https://youtu.be/miXMtHDUeb0)

**MAME Community Ecosystem:**
* 👾 [MAMEdev Official](https://www.mamedev.org/)
* 📖 [MAME Wiki](https://wiki.mamedev.org/index.php?title=Main_Page)
* 🗄️ [ArcadeItalia (ADB)](http://adb.arcadeitalia.net/)
* 🖼️ [ProgettoSnaps (For Catver/Art assets)](https://www.progettosnaps.net/index.php)

**Arcade Community Shoutouts:**
* 🔥 [Team Encoder](https://www.team-encoder.com/)
* 🚀 [Rogue Synapse (The Last Starfighter)](http://www.roguesynapse.com/games/last_starfighter.php)
* 👁️ [Sinnesloschen (Polybius)](http://www.sinnesloschen.com/)
* 🕹️ [Houston Arcade & Pinball Expo](https://www.houstonarcadeexpo.com/)

---

## 🐛 Found a Bug? (How to Report)

If you run into an issue or a game isn't filtering correctly, we want to fix it! To help us hunt down the bug quickly, please report it via the [**GitHub Issues Tab**](https://github.com/Cyborgbob/MAME-Smart-ROM-Sorter/issues) or shoot us an email at `technicallynotatechnician@gmail.com` with the following information:

1. **The Details:** What exactly went wrong? (e.g., *"Space Invaders is missing!"* or *"The app froze when I clicked X"*).
2. **Your Preset:** Please attach the `.json` preset file you used.
3. **Your Log:** Please attach the full `filter_log.txt` generated after your run.

*Note: Without your preset and full log file, it is extremely difficult to diagnose the issue!*

---

## ☕ Support & Contact

This tool is 100% free and open source. If it saved you hours of organizing, a sub or a coffee helps keep the lights on!

* 📺 **Subscribe:** [Technically Not a Technician on YouTube](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1)
* ☕ **Buy Me a Coffee:** [buymeacoffee.com/technicallynota](https://buymeacoffee.com/technicallynota)

**Want to chat, or just bullshit with me?** Shoot me an email: `technicallynotatechnician@gmail.com`

---

## ❤️ Community Credits

This tool was forged in the fires of community testing. A massive thank you to the following early adopters who provided the logs, feedback, and feature requests that shaped this version:

* **Marcus:** For detailed bug hunting that directly led to the 2-Way Joystick patch, the Tiered Emulation Status dropdown, and the concept for the Decades filter.
* **@johnmclain250:** Your sandbox testing and filter logs helped us identify the "Clone Leak" and the X-Men player count bugs, directly leading to the creation of the 1G1R engine and the Deep Scan logic.
* **@Englad666:** For sending in detailed logs to help us iron out complex control and orientation filtering.
* **@TravisK-i1e:** For representing the RetroArch community and inspiring the "Smart Setup Wizard" that fetches missing files from GitHub.
* **@FermentedGrumpyGrapeSqueezit:** For the emulation trivia and regional ROM hierarchy insights.
* **The r/MAME Community:** For documenting the metadata standards that make tools like this possible.

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

* **Free to Share:** Copy and redistribute.
* **Free to Adapt:** Remix and build upon.

* **NonCommercial:** You cannot sell this tool.
<img width="1918" height="1078" alt="Screenshot 2026-02-22 175255" src="https://github.com/user-attachments/assets/0cf8ca91-40ce-4779-a0ca-4f0b871dc667" />


