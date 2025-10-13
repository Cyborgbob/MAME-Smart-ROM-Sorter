# MAME Smart ROM Sorter (GUI + CLI) v4.1 ✨

**Status:** ✅ Tested & Production-Ready!

## What is This Tool? 🤔

The **MAME Smart ROM Sorter** is a powerful tool designed to help arcade enthusiasts clean up messy MAME ROM collections and manage their arcade game collection. If you’ve ever downloaded a full MAME set, you know it’s packed with thousands of files you don’t need: console games, home computers, non-working games, and duplicates. This tool is your digital broom! 🧹

It turns a giant, overwhelming folder of files into a **lean, playable arcade collection** tailored specifically to your needs, making MAME ROM management simple.

---

## 🧐 Before You Begin: What is MAME? (For the Complete Novice)

If you're new to this, it can be confusing! Here are the basics in plain English:

* **MAME:** This is the **emulator program** that lets you play old arcade games on a modern computer. Our tool helps you organize the game files *for* MAME, but it is **not** MAME itself. You'll need to get MAME separately.
* **ROM:** Think of a ROM as a **digital copy of an arcade game**. It's usually a single `.zip` file (e.g., `pacman.zip`).
* **Non-Merged ROM Set:** This is a type of collection where every single game's `.zip` file is complete and self-contained. Our tool requires this format because other set types have missing files, and our tool needs every game to be whole.

---

## 🚀 Key Features (Why This Tool is a Game-Changer)

-   **True Arcade-Only Filtering:** Accurately identifies and keeps *only* arcade games, filtering out the consoles, computers, and handhelds that clutter other sorting tools.
-   **Intelligent Sorting Hierarchy:** Automatically prioritizes the best version of each game, ensuring you get the official Parent ROM over clones, bootlegs, or hacks.
-   **Full Dependency Handling:** The script is smart enough to find and copy all the essential files a game needs to run. This means games that require a separate "digital console" (like Neo Geo games) or have large data files will just work, without you having to hunt down extra files.
-   **User-Friendly GUI:** A simple graphical interface for Windows users means you don't have to touch the command line. An `.exe` version is available for maximum portability.
-   **Save & Load Presets:** Save your filtering settings to a file to easily re-run the same sort later or share your cabinet's configuration.

---

## ⚙️ Getting Started: Your Guide to a Clean ROM Set

Follow these steps carefully. Remember our motto: **Excellent in, perfect out.**

### **Step 0: The Golden Rule (Please Read!)**

<div align="center">
  <table border="1" style="border-color: red; background-color: #fff0f0; padding: 10px;">
    <tr>
      <td>
        <h3 align="center">⚠️ IMPORTANT ⚠️</h3>
        <p align="center">For this program to work, you MUST place the <code>MAME_Sorter.exe</code> file in the <strong>SAME FOLDER</strong> as your MAME assets (your <code>roms</code> folder and the <code>full.xml</code> file).</p>
      </td>
    </tr>
  </table>
</div>

### **Step 1: Prepare Your MAME Assets (The "Excellent In")**

1.  **A Full Non-Merged MAME ROM Set:**
    * **Why?** Our tool needs each game's `.zip` file to be complete. If you need to convert your set, check out this guide: [**How to Convert Merged to Non-Merged Sets**](https://youtu.be/miXMtHDUeb0)

2.  **The `full.xml` File (The "Brain"):**
    * **Why?** This file is the database our program uses to make all its smart decisions.
    * **How to get it:** This is the only technical step! Open a command prompt or PowerShell in your MAME directory and run this command:
        ```shell
        mame.exe -listxml > full.xml
        ```
        *(Note: If you're in PowerShell, you might need to type `.\mame.exe -listxml > full.xml`)*
    * This can take a few minutes. When it's done, copy the new `full.xml` file into the sorter's folder.

3.  **(Optional but Recommended) Your `samples` Folder:**
    * If you have a `samples` folder for extra game sounds, copy it into the sorter's folder.

### **Step 2: Run the Program & Choose Filters**

Double-click the `MAME_Sorter.exe` file. Fill out the form to match your arcade cabinet's setup (players, buttons, control types, etc.).

### **Step 3: Run the Sort & Enjoy!**

Click the **"Run"** button. The program will start processing your files. When it's done, you'll find a new folder called **`filtered_mame_set`** containing your perfectly curated collection, ready to use!

---

## 🎉 You Did It! Feeling Grateful?

If this tool just saved you hours of tedious work, please consider supporting our future projects! A subscription or a small tip helps us keep making free, powerful tools for the community.

-   **📺 Subscribe on YouTube:** [Technically Not a Technician](https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1)
-   **☕ Buy Me a Coffee:** [buymeacoffee.com/technicallynota](https://buymeacoffee.com/technicallynota)

---

## 📺 Helpful Resources & Video Guides

-   **New to MAME? Start Here!** A beginner-friendly guide to getting MAME set up.
    * [**Mastering Mame and Relive Arcade Nostalgia BUT For Dummies!!**](https://www.youtube.com/watch?v=P4As2E070Vw)

---

## 🐛 Reporting Bugs & Feedback

Found an issue or have an idea for an improvement? Please report it on [the "Issues" tab of our GitHub repository](https://github.com/your-username/your-repo-name/issues). This helps us track and fix problems in a structured way.

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. This means you are free to share and adapt this work for non-commercial purposes, as long as you give appropriate credit and distribute any remixes under the same license. You can view the full license text in the `LICENSE` file.

---

## ❤️ Credits & Support

This tool was a collaborative effort between:
-   **Shawn Flanagan (Technically Not a Technician):** Concept, expert testing, and project direction.
-   **Bob Cogito (AI Assistant):** Code development, debugging, and documentation.