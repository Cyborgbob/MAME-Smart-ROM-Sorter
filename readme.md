# MAME Smart ROM Sorter (GUI + CLI) v4.20 🚀

**Status:** ✅ Tested & Production-Ready\!

## 🚨 IMPORTANT: Windows Virus Warning (False Positive)

**Please Read Before Downloading:**
Because this program is a standalone `.exe` created by a solo developer (Technically Not a Technician) and not a large corporation, it does not have a digital signature. **Windows Defender and other antiviruses will likely flag this as a virus.**

  * **This is a False Positive.**
  * The code is **Open Source** (included in this repository) so you can verify it yourself.
  * It does nothing but read your XML, filter your list, and copy your files.
  * **To Run:** Click "More Info" -\> "Run Anyway" or add the folder to your exclusion list.

-----

## What is This Tool? 🤔

The **MAME Smart ROM Sorter** is your "digital broom" for MAME collections. If you’ve ever downloaded a full MAME set, you know it’s packed with thousands of files you don't need: console games (SNES, Genesis), calculators, non-working prototypes, and duplicates.

**v4.20** turns that overwhelming mess into a **clean, curated, arcade-only collection** tailored to *your* preferences.

### ✨ New in v4.20 (The "Game Changer" Update)

Based on community feedback (shoutout to **@johnmclain250**\!), we have completely rebuilt the engine:

1.  **The Missing Assets Audit (Killer Feature):**

      * **The Problem:** In the past, if a game didn't copy, you never knew why.
      * **The Fix:** The tool now generates a detailed **Audit Report** in the log window. It tells you *exactly* what is missing—down to the specific `chd`, `sample`, or `bios` file—so you can go find it.

2.  **Smart Filtering with `CatVer.ini`:**

      * We replaced the old manual "blocklist" with the official `CatVer.ini` (Category/Version) system.
      * **Result:** You can now filter by **Genre** (Platformer, Shooter, Fighter) and perfectly strip out non-arcade categories like "Tabletop," "Handheld," and "Computers" with zero false positives.

3.  **Strict 1G1R (One Game, One ROM):**

      * The tool prioritizes the **Parent** version of a game. If the Parent works, it ignores the 50+ clones/bootlegs, keeping your menu clean.

-----

## 🧐 Before You Begin: What is MAME? (For the Complete Novice)

If you're new to this, it can be confusing\! Here are the basics:

  * **MAME:** The emulator program that plays the games. Our tool *organizes* the files for MAME, but it is not MAME itself.
  * **ROM:** The digital copy of the game (e.g., `pacman.zip`).
  * **Non-Merged ROM Set:** This is the type of collection our tool needs. Every game zip file must be "complete" and self-contained.

-----

## 🛠️ Prerequisites (What You Need)

To use v4.20, you need **three** files in your folder.

1.  **The Tool:** `MAME_Sorter.exe` (Download from Releases).
2.  **The Brain:** `full.xml` (Your machine's map).
      * *How to get it:* Open a command prompt in your MAME folder and type: `mame.exe -listxml > full.xml`
3.  **The Filter:** `CatVer.ini` (**NEW for v4.20**)
      * *How to get it:* Download it from [AntoPISA's Progetto Snaps](https://www.progettosnaps.net/catver/).
      * *Why:* This file tells the sorter which games are "Fighters" and which are "Calculators."

-----

## 🚀 How to Use (Step-by-Step)

1.  **Prepare Your Folder:** Create a new folder on your desktop. Put `MAME_Sorter.exe`, `full.xml`, and `CatVer.ini` inside it.
2.  **Launch:** Double-click the `.exe`. You will see the new **Dashboard Interface**.
3.  **Select Paths:**
      * **Source Folder:** Point this to your messy "Full MAME Set."
      * **Output Folder:** Point this to an empty folder where you want your clean games to go.
4.  **Set Filters:**
      * **Categories:** Uncheck things you don't want (e.g., *Print Club, Electromechanical*).
      * **Genres:** (Optional) Only want *Shooters*? Uncheck everything else.
5.  **Run:** Click **"Start Sorting"**.
6.  **Review the Audit:** When finished, check the log window. It will list any files you are missing so you can fix your set\!

-----

## 📺 Helpful Resources & Video Guides

  * **New to MAME? Start Here\!**
      * [**Mastering Mame and Relive Arcade Nostalgia BUT For Dummies\!\!**](https://www.youtube.com/watch?v=P4As2E070Vw)
  * **Understanding Merged vs. Non-Merged Sets:**
      * [**MAME ROMs Explained**](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ)
  * **The v4.20 Update Walkthrough:**
      * *(Video Coming Soon\!)*

-----

## ❤️ Community Credits

This update was driven by **you**.

  * **@johnmclain250:** A massive thank you for your detailed testing. Your logs helped us identify the "Tiger Handheld" leak and the X-Men clone issues, directly leading to the `CatVer.ini` integration.
  * **The r/MAME Community:** For documenting the metadata standards that make tools like this possible.

-----

## ☕ Support the Project

This tool is 100% free and open source. If it saved you hours of organizing, a sub or a coffee helps keep the lights on\!

  * **📺 Subscribe:** [Technically Not a Technician](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1)
  * **☕ Buy Me a Coffee:** [buymeacoffee.com/technicallynota](https://buymeacoffee.com/technicallynota)

-----

## 🐛 Reporting Bugs

Found an issue? Please report it on the [**Issues Tab**](https://www.google.com/search?q=https://github.com/Cyborgbob/MAME-Smart-ROM-Sorter/issues). Include your `filter_log.txt` if possible—it helps us debug instantly\!

-----

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

  * **Free to Share:** Copy and redistribute.
  * **Free to Adapt:** Remix and build upon.
  * **NonCommercial:** You cannot sell this tool.