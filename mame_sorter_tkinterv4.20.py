#!/usr/bin/env python3

"""
MAME Smart ROM Sorter — GUI (Tkinter) + CLI v4.20 (Modified)

----------------------------------------------------------------

Authors: Shawn Flanagan & Bob Cogito

Base: v4.19
v4.20 Changes:
    - FEATURE: Added "Missing Assets Audit" to filter_log.txt.
    - LOGIC: Now tracks BIOS/Parent files separately from Game ROMs.
    - LOGIC: Metadata map created to link filenames to Game Descriptions in the error log.
    - OUTPUT: Logs distinct lists for Missing ROMs, Missing BIOS/Parents, Missing CHDs, and Missing Samples.
    - UI: Restored v4.19 Splash Screen (with CatVer links) by user request.
"""

from __future__ import annotations

import os
import sys
import re
import shutil
import queue
import threading
import json
import webbrowser
import xml.etree.ElementTree as ET

from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


# -------------------------------
# PyInstaller Path Helper
# -------------------------------

def get_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent


# -------------------------------
# CONSTANTS: The Verified Block List
# -------------------------------

EXCLUDED_GENRES = {
    "System", "Device", "Printer", "Calculator", "Medical", "Medical Equipment",
    "Test", "Utility", "Utilities", "Console", "Game Console", "Handheld",
    "Computer", "Watch", "Clock", "Telephone", "Slot Machine", "Casino",
    "Gambling", "Electromechanical", "Mahjong", "Board Game", "Othello",
    "Whac-A-Mole", "Medal Game", "Photo Booth", "Music Player", "Document",
    "Touchscreen", "Non Arcade", "Robot", "Road Indicator", "Player",
    "Tablet", "Computer Graphic Workstation", "Digital Camera", 
    "Digital Simulator", "Musical Instrument", "Musical Instrument Accessory",
    "Radio", "Redemption Game", "Simulation", "TV Bundle", "Tabletop",
    "Game Console/Computer",
}

GENRE_DISPLAY_MAP = {
    "Arcade": "Video Pinball & Hybrids",
    "Ball & Paddle": "Breakout & Pong",
    "Multiplay": "Party / Mini-Games",
    "MultiGame": "Multi-Game Systems",
    "Climbing": "Climbing (Crazy Climber)",
    "Rhythm": "Music & Rhythm",
    "Shooter": "Shooter (Shmups & Guns)",
    "Driving": "Driving / Racing",
    "Fighter": "Fighting",
    "Beat'em": "Beat 'em Up",
    "Platform": "Platformer",
    "Puzzle": "Puzzle",
    "Maze": "Maze",
    "Sports": "Sports",
    "Misc.": "Misc. / Uncategorized",
}


# -------------------------------
# CLI helper prompts
# -------------------------------

def ask_yes_no(prompt: str) -> bool:
    print(f"\n{prompt}")
    print(" A) Yes")
    print(" B) No")
    while True:
        ans = input("> ").strip().upper()
        if ans in ("A", "Y", "YES"):
            return True
        if ans in ("B", "N", "NO"):
            return False
        print("❌ Please type A or B (Yes/No).")


def ask_choice(prompt: str, choices: Dict[str, str]) -> str:
    print(f"\n{prompt}")
    for letter, desc in choices.items():
        print(f" {letter}) {desc}")
    while True:
        answer = input("> ").strip().upper()
        if answer in choices:
            return choices[answer]
        print("❌ Invalid choice. Please enter one of: " + ", ".join(choices.keys()))


def ask_multi(prompt: str, choices: Dict[str, str]) -> List[str]:
    print(f"\n{prompt}")
    for letter, desc in choices.items():
        print(f" {letter}) {desc}")
    while True:
        answer = input("> ").strip().upper().replace(" ", "")
        if not answer:
            print("❌ Please select at least one option.")
            continue
        parts = [a for a in answer.split(",") if a]
        if all(a in choices for a in parts):
            return [choices[a] for a in parts]
        print("❌ Invalid selection. Use the letters shown (comma-separated).")


# -------------------------------
# Setup verification
# -------------------------------

def verify_setup(script_dir: Path) -> None:
    print("\nMAME Smart ROM Sorter — Setup Check")
    print("----------------------------------")
    print("This tool requires:")
    print(" • A valid full.xml (from MAME)")
    print(" • A path to your MAME ROMs folder")
    print(" • (Optional) A path to your MAME Samples folder")
    print(" • (Recommended) A catver.ini matching your MAME version")


# -------------------------------
# CLI input collection (fallback)
# -------------------------------

def get_user_inputs_cli() -> Dict[str, Any]:
    script_dir = get_base_path()
    default_xml = str(script_dir / "full.xml")
    default_roms = str(script_dir)
    default_samples = str(script_dir / "samples")
    default_output = "filtered_mame_set"
    default_catver = str(script_dir / "catver.ini")

    print("\nPaths (leave blank to use defaults shown in brackets)")
    full_xml = input(f"📄 Path to full.xml [default: {default_xml}]: ").strip() or default_xml
    rom_dir = input(f"🎮 Path to MAME ROMs folder [default: {default_roms}]: ").strip() or default_roms
    sample_dir = input(f"🔊 Path to MAME Samples folder (optional) [default: {default_samples}]: ").strip() or default_samples
    output_folder = input(f"📁 Main Output folder name [default: {default_output}]: ").strip() or default_output
    catver_path = input(f"📚 Path to catver.ini (optional) [default: {default_catver}]: ").strip() or default_catver

    player_choices = dict(zip("ABCDEFGHIJKLMNOPQ", [str(i) for i in range(1, 17)] + ["All"]))
    players_ans = ask_choice("👥 Max simultaneous players on your cab?", player_choices)
    players = 99 if players_ans == "All" else int(players_ans)

    button_choices = dict(zip("ABCDEFGHIJKLMNOPQ", [str(i) for i in range(1, 17)] + ["All"]))
    buttons_ans = ask_choice("🔘 Max ACTION buttons per player? (exclude coin/start)", button_choices)
    max_buttons = 99 if buttons_ans == "All" else int(buttons_ans)

    control_letters = {
        "A": "joystick",
        "B": "trackball",
        "C": "spinner",
        "D": "dial",
        "E": "paddle",
        "F": "lightgun",
        "G": "positional",
        "H": "mouse",
        "I": "pedal",
        "J": "stick (analog)",
        "K": "keyboard",
        "L": "buttons only",
        "M": "other",
        "N": "all",
    }
    controls_ans = ask_multi("🎮 Select control types (comma letters, or include 'N' for all):", control_letters)
    controls = [] if any(c.lower() == "all" for c in controls_ans) else controls_ans

    direction_letters = {
        "A": "4-way",
        "B": "8-way",
        "C": "2-way horizontal",
        "D": "2-way vertical",
        "E": "49-way",
        "F": "rotary",
        "G": "analog",
        "H": "All",
    }
    directions_ans = ask_multi("🧭 Joystick directions? (comma letters; H for All)", direction_letters)
    directions = [] if any(d.lower() == "all" for d in directions_ans) else directions_ans

    strict_mode = ask_yes_no("Strict Mode? (Reject games with ANY unselected control type?)")

    orientation_ans = ask_choice("🖥️ Screen orientation?", {"A": "horizontal", "B": "vertical", "C": "both"})
    working_only = ask_yes_no("✅ Only include fully working games? (Yes=Recommended)")
    mature = ask_yes_no("🔞 Include mature/18+ titles? (No = family friendly)")

    include_clones = ask_yes_no("Include official clones (different regions, versions)?")
    include_bootlegs = ask_yes_no("Include bootlegs & hacks?")
    include_prototypes = ask_yes_no("Include prototypes & demos?")

    region_input = input("\n🌍 Preferred region order (comma list, or 'all' / blank for all): ").strip().lower()
    region_order = [] if not region_input or region_input == "all" else [r.strip() for r in region_input.split(",") if r.strip()]

    language_input = input("🗣️ Preferred languages (comma list, or 'all' / blank for all): ").strip().lower()
    language_order = [] if not language_input or language_input == "all" else [r.strip() for r in language_input.split(",") if r.strip()]

    return {
        "full_xml": full_xml,
        "rom_dir": rom_dir,
        "sample_dir": sample_dir,
        "output_path": output_folder,
        "players": players,
        "max_buttons": max_buttons,
        "controls": controls,
        "directions": directions,
        "strict_controls": strict_mode,
        "orientation": orientation_ans,
        "working_only": working_only,
        "mature": mature,
        "include_clones": include_clones,
        "include_bootlegs": include_bootlegs,
        "include_prototypes": include_prototypes,
        "region_order": region_order,
        "language_order": language_order,
        "catver_path": catver_path,
        "genres": [], 
    }


# -------------------------------
# Core filtering utilities
# -------------------------------

CONTROL_KEYWORDS = {
    "joystick": {"joy", "joystick"},
    "trackball": {"trackball"},
    "spinner": {"spinner"},
    "dial": {"dial"},
    "paddle": {"paddle"},
    "lightgun": {"lightgun"},
    "positional": {"positional"},
    "mouse": {"mouse"},
    "pedal": {"pedal"},
    "stick (analog)": {"analog"},
    "keyboard": {"keyboard"},
    "buttons only": {"buttons only"},
    "other": {"other"},
}

DIRECTION_MAP = {
    "4-way": {"4"},
    "8-way": {"8"},
    "2-way horizontal": {"2h", "2-h", "2 horizontal"},
    "2-way vertical": {"2v", "2-v", "2 vertical"},
    "49-way": {"49"},
    "rotary": {"rotary", "12-way"},
    "analog": {"analog"},
}

KNOWN_LANGUAGES = {
    "english", "japanese", "spanish", "french", "german", "italian",
    "korean", "chinese", "dutch", "en", "ja", "es", "fr", "de", "it",
    "ko", "zh", "nl",
}

BOOTLEG_PATTERNS = ["bootleg", "hack"]
PROTOTYPE_PATTERNS = ["prototype", "beta", "demo"]

NON_ARCADE_SOURCE_FILES = {
    "genesis.cpp", "nes.cpp", "snes.cpp", "gamegear.cpp", "gameboy.cpp", "lynx.cpp",
    "pce.cpp", "a2600.cpp", "coleco.cpp", "intv.cpp", "odyssey2.cpp", "vectrex.cpp",
    "hh_tms.cpp", "hh_sm510.cpp", "msx.cpp", "spectrum.cpp", "c64.cpp", "amiga.cpp",
    "ti99.cpp", "x1.cpp", "coco.cpp", "apple2.cpp", "mac.cpp", "pc.cpp", "fm7.cpp",
}


def _status(status_q, msg: str) -> None:
    if status_q is not None:
        status_q.put(("status", msg))


# --- CATVER SUPPORT -------------------------------------------------

ARCADE_OK_PREFIXES = (
    "Action", "Arcade", "Beat'em", "Fighter", "Fighting", "Platform",
    "Maze", "Shooter", "Shoot'em", "Sports", "Racing", "Driving",
    "Run and Gun", "Puzzle", "Misc.", "Uncategorized", "Pinball",
    "Rhythm", "Music Game", "MultiGame", "Multiplay", "Climbing",
    "Breakout", "Ball & Paddle",
)

NON_ARCADE_CAT_PREFIXES = tuple(EXCLUDED_GENRES)
MATURE_CAT_MARKERS = ("Mature", "Adult", "XXX", "Erotic")


def load_catver(catver_path: Path, status_q: Optional[queue.Queue] = None) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not catver_path or not catver_path.exists():
        _status(status_q, f"⚠️ catver.ini not found at: {catver_path}")
        return mapping

    current_section: Optional[str] = None
    try:
        with catver_path.open("r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(("#", ";")):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip().lower()
                    continue

                if "=" in line and current_section in (None, "", "category", "catver"):
                    name, cat = line.split("=", 1)
                    rom = name.strip()
                    cat_txt = cat.strip()
                    if rom:
                        mapping[rom] = cat_txt
    except Exception as e:
        _status(status_q, f"⚠️ Failed to parse catver.ini: {e}")
        return {}

    _status(status_q, f"📚 Loaded {len(mapping)} CatVer entries from {catver_path.name}")
    return mapping


def get_main_genre(cat_string: str) -> str:
    if not cat_string:
        return "Unknown"
    main = cat_string.split(" / ")[0].strip()
    if main.startswith("TTL * "):
        main = main.replace("TTL * ", "").strip()
    return main


def catver_allows_arcade(name: str, catver_map: Dict[str, str]) -> bool:
    if not catver_map:
        return True
    cat = catver_map.get(name)
    if not cat:
        return True
    main = get_main_genre(cat)
    if main in EXCLUDED_GENRES:
        return False
    cat_str = cat.strip()
    for prefix in NON_ARCADE_CAT_PREFIXES:
        if cat_str.startswith(prefix):
            return False
    return True


def catver_marks_mature(name: str, catver_map: Dict[str, str]) -> bool:
    if not catver_map:
        return False
    cat = catver_map.get(name)
    if not cat:
        return False
    cat_lower = cat.lower()
    return any(marker.lower() in cat_lower for marker in MATURE_CAT_MARKERS)


# --- XML-based helpers (unchanged) ---

def is_actually_an_arcade_machine(machine_element) -> bool:
    if machine_element.get("isdevice") == "yes": return False
    if machine_element.get("ismechanical") == "yes": return False
    if machine_element.get("isbios") == "yes": return False
    if machine_element.get("runnable") == "no": return False
    source_file = machine_element.get("sourcefile")
    if source_file in NON_ARCADE_SOURCE_FILES: return False
    category_tag = machine_element.find("category")
    if category_tag is not None and category_tag.text:
        category_text = category_tag.text.lower()
        if any(keyword in category_text for keyword in ["console", "handheld", "computer", "system"]):
            return False
    return True


def _good_driver_status(driver) -> bool:
    if driver is None: return True
    status = (driver.get("status") or "").lower().strip()
    return not status or status in {"good", "perfect"}


def _match_orientation(display, want: str) -> bool:
    if want == "both" or display is None: return True
    rotate = (display.get("rotate") or "0").strip()
    try:
        r = int(rotate)
    except Exception:
        r = 0
    is_vertical = r in (90, 270)
    if want == "vertical": return is_vertical
    if want == "horizontal": return not is_vertical
    return True


def _collect_control_tokens(machine) -> Tuple[Set[str], Set[str]]:
    types, dirs = set(), set()
    input_tag = machine.find("input")
    if input_tag is not None:
        for ctrl in input_tag.findall("control"):
            ctype = (ctrl.get("type") or "").lower()
            ways = (ctrl.get("ways") or ctrl.get("ways2") or ctrl.get("ways3") or "").lower()
            if ctype: types.add(ctype)
            if ways: dirs.add(ways)
    ctrl2 = machine.find("control")
    if ctrl2 is not None:
        ctype = (ctrl2.get("type") or "").lower()
        ways = (ctrl2.get("ways") or "").lower()
        if ctype: types.add(ctype)
        if ways: dirs.add(ways)
    return types, dirs


def _controls_ok(config_controls: List[str], machine, strict: bool = False) -> bool:
    if not config_controls: return True 
    types, _ = _collect_control_tokens(machine)
    if not types: return True
    
    has_allowed = False
    for want in config_controls:
        kws = CONTROL_KEYWORDS.get(want.lower(), {want.lower()})
        for t in types:
            if any(kw in t.lower() for kw in kws):
                has_allowed = True
                break
        if has_allowed: break
    if not has_allowed: return False

    if strict:
        for t in types:
            is_permitted = False
            for want in config_controls:
                kws = CONTROL_KEYWORDS.get(want.lower(), {want.lower()})
                if any(kw in t.lower() for kw in kws):
                    is_permitted = True
                    break
            if not is_permitted: return False
    return True


def _directions_ok(config_dirs: List[str], machine) -> bool:
    if not config_dirs: return True
    _, dirs = _collect_control_tokens(machine)
    if not dirs: return True
    for want in config_dirs:
        tokens = DIRECTION_MAP.get(want, {want.lower()})
        for d in dirs:
            if any(tok in d.lower() for tok in tokens):
                return True
    return False


def _players_ok(limit: int, machine) -> bool:
    if limit >= 99 or machine.find("input") is None: return True
    try:
        return int(machine.find("input").get("players")) <= int(limit)
    except Exception: return True


def _buttons_ok(limit: int, machine) -> bool:
    if limit >= 99: return True 
    input_node = machine.find("input")
    if input_node is None: return True 
    try:
        if input_node.get("buttons"):
            if int(input_node.get("buttons")) > limit: return False
    except Exception: pass
    for ctrl in input_node.findall("control"):
        try:
            if ctrl.get("buttons"):
                if int(ctrl.get("buttons")) > limit: return False
        except Exception: pass
    return True


def _clone_status(machine) -> Tuple[int, bool]:
    cloneof = machine.get("cloneof")
    if not cloneof: return 0, False
    desc = machine.findtext("description", "").lower()
    is_bootleg = any(p in desc for p in BOOTLEG_PATTERNS)
    if is_bootleg: return 2, True
    is_prototype = any(p in desc for p in PROTOTYPE_PATTERNS)
    if is_prototype: return 3, True
    return 1, False


def _mature_ok(include_mature: bool, machine) -> bool:
    cat = machine.find("category")
    desc = machine.findtext("description", "")
    blob = f"{cat.text if cat is not None else ''} {desc or ''}".lower()
    if any(x in blob for x in ["mature", "adult", "mahjong (strip)", "erotic", "nsfw", "xxx", "(nude)"]):
        return include_mature
    return True


def _region_score(name: str, desc: str, region_order: List[str]) -> int:
    if not region_order: return 0
    text = f"{name} {desc}".lower()
    for idx, token in enumerate(region_order):
        if token.strip().lower() in text:
            return idx
    return len(region_order) + 1

# v4.20 Update: Now returns lists AND metadata for auditing
def parse_full_xml(
    xml_path: Path,
    config: Dict[str, Any],
    debug_path: Path,
    status_q=None,
    catver_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[str], List[str], List[str], Dict[str, str]]:
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    entries = list(root.findall("machine")) or list(root.findall("game"))
    _status(status_q, f"XML loaded: {len(entries)} entries detected…")

    matched: List[Dict[str, Any]] = []
    skip_reasons: Counter = Counter()

    selected_genres = set(config.get("genres", []))
    filter_by_genre = bool(selected_genres)
    
    strict_controls = config.get("strict_controls", False)

    for m in entries:
        name = m.get("name") or ""
        description = m.findtext("description", "")

        clone_score, _is_unwanted_type = _clone_status(m)
        if clone_score == 1 and not config.get("include_clones"):
            skip_reasons["clone_type"] += 1
            continue
        if clone_score == 2 and not config.get("include_bootlegs"):
            skip_reasons["clone_type"] += 1
            continue
        if clone_score == 3 and not config.get("include_prototypes"):
            skip_reasons["clone_type"] += 1
            continue

        if filter_by_genre:
            rom_cat_full = catver_map.get(name, "Unknown") if catver_map else "Unknown"
            rom_genre = get_main_genre(rom_cat_full)
            if rom_genre not in selected_genres:
                skip_reasons["genre_filter"] += 1
                continue
        
        rom_cat_full = catver_map.get(name, "Unknown") if catver_map else "Unknown"
        rom_genre = get_main_genre(rom_cat_full)
        if rom_genre in EXCLUDED_GENRES:
             skip_reasons["genre_excluded"] += 1
             continue

        if not catver_allows_arcade(name, catver_map or {}):
            skip_reasons["catver_non_arcade"] += 1
            continue

        if not is_actually_an_arcade_machine(m):
            skip_reasons["not_arcade"] += 1
            continue

        if config.get("working_only", False) and not _good_driver_status(m.find("driver")):
            skip_reasons["not_working"] += 1
            continue

        if not config.get("mature", False) and catver_marks_mature(name, catver_map or {}):
            skip_reasons["mature_catver"] += 1
            continue

        if not _mature_ok(config.get("mature", False), m):
            skip_reasons["mature"] += 1
            continue

        if not _match_orientation(m.find("display"), config.get("orientation", "both")):
            skip_reasons["orientation"] += 1
            continue
        if not _players_ok(config.get("players", 99), m):
            skip_reasons["players"] += 1
            continue
        
        if not _buttons_ok(config.get("max_buttons", 99), m):
            skip_reasons["buttons"] += 1
            continue
        
        if not _controls_ok(config.get("controls", []), m, strict=strict_controls):
            skip_reasons["controls"] += 1
            continue
            
        if not _directions_ok(config.get("directions", []), m):
            skip_reasons["directions"] += 1
            continue

        region_score_val = _region_score(name, description, config.get("region_order", []))

        if config.get("language_order"):
            langs = config["language_order"]
            text = f"{name} {description}".lower()
            language_score = len(langs) + 1
            for idx, l in enumerate(langs):
                if l.lower() in text:
                    language_score = idx
                    break
        else:
            language_score = 0

        chds = [disk.get("name") for disk in m.findall("disk")]
        samples = [s.get("name") for s in m.findall("sample")]
        if m.get("sampleof"):
            samples.append(m.get("sampleof"))
        bios = m.get("romof") # Tracking parent/bios name

        matched.append(
            {
                "name": name,
                "description": description,
                "clone_score": clone_score,
                "region_score": region_score_val,
                "language_score": language_score,
                "chds": chds,
                "samples": list(set(samples)),
                "bios": bios,
            }
        )

    _status(status_q, f"Matched {len(matched)} / {len(entries)} after filtering.")

    matched.sort(key=lambda r: (r["clone_score"], r["region_score"], r["language_score"], r["name"]))

    # v4.20: Segregate tracking for better reporting
    final_roms_to_copy: Set[str] = set()
    final_bios_parents_to_copy: Set[str] = set()
    final_chds_to_copy: Set[str] = set()
    final_samples_to_copy: Set[str] = set()
    seen_games: Set[str] = set()
    
    # Metadata map: "filename.zip" -> "Game Name"
    # Used for the Missing Assets Report
    metadata_map: Dict[str, str] = {}

    for r in matched:
        if r["name"] in seen_games:
            continue
        seen_games.add(r["name"])
        
        game_desc = r["description"]
        
        # 1. Main ROM
        final_roms_to_copy.add(r["name"])
        metadata_map[f"{r['name']}.zip"] = game_desc
        
        # 2. BIOS / Parent
        if r.get("bios"):
            final_bios_parents_to_copy.add(r["bios"])
            # Metadata: If we haven't named this parent yet, call it "Parent/BIOS for [Game]"
            # If it's a common BIOS like 'neogeo', it might be overwritten by the actual neogeo game desc later, which is fine.
            if f"{r['bios']}.zip" not in metadata_map:
                metadata_map[f"{r['bios']}.zip"] = f"Required Parent/BIOS for {game_desc}"

        # 3. CHDs
        for chd in r.get("chds", []):
            chd_path = f"{r['name']}/{chd}.chd"
            final_chds_to_copy.add(chd_path)
            metadata_map[chd_path] = f"CHD for {game_desc}"

        # 4. Samples
        for sample in r.get("samples", []):
            final_samples_to_copy.add(sample)
            metadata_map[f"{sample}.zip"] = f"Audio Samples for {game_desc}"
    
    # Writing standard debug log (Passed filter list)
    with open(debug_path, "w", encoding="utf-8") as dbg:
        dbg.write(f"Total parsed: {len(entries)}\n")
        dbg.write(f"Matched unique: {len(seen_games)}\n")
        for k, v in sorted(skip_reasons.items()):
            dbg.write(f"Skipped {k}: {v}\n")
        dbg.write("\n=== GAMES MATCHING FILTER ===\n")
        for i, r in enumerate(matched, 1):
            if r["name"] in seen_games: # Only list uniques
                dbg.write(f"{r['name']} — {r['description']}\n")

    return (
        list(final_roms_to_copy), 
        list(final_bios_parents_to_copy), 
        list(final_chds_to_copy), 
        list(final_samples_to_copy), 
        metadata_map
    )
# v4.20 Update: Missing Assets Audit Logic added here
def copy_assets(
    rom_list: List[str],
    bios_list: List[str],
    chd_list: List[str],
    sample_list: List[str],
    metadata_map: Dict[str, str],
    rom_dir: Path,
    sample_dir: Optional[Path],
    out_rom_dir: Path,
    out_sample_dir: Path,
    debug_path: Path,
    status_q=None,
) -> None:
    
    total_ops = len(rom_list) + len(bios_list) + len(chd_list) + len(sample_list)
    copied_count = 0
    
    # Audit lists for the report
    missing_roms = []
    missing_bios = []
    missing_chds = []
    missing_samples = []

    _status(status_q, f"📦 Processing {total_ops} asset checks...")

    # 1. Game ROMs
    for name in rom_list:
        found = False
        # Check ZIP then 7Z
        for ext in [".zip", ".7z"]:
            source = rom_dir / f"{name}{ext}"
            if source.exists():
                try:
                    shutil.copy2(source, out_rom_dir / source.name)
                    copied_count += 1
                    found = True
                    break
                except Exception as e:
                    _status(status_q, f"⚠️ Error copying {name}: {e}")
        
        if not found:
            desc = metadata_map.get(f"{name}.zip", "Unknown Game")
            missing_roms.append(f"{name}.zip - {desc}")

    # 2. BIOS / Parents
    for name in bios_list:
        found = False
        for ext in [".zip", ".7z"]:
            source = rom_dir / f"{name}{ext}"
            if source.exists():
                # Avoid re-copying if already done in ROM loop
                if not (out_rom_dir / source.name).exists():
                    try:
                        shutil.copy2(source, out_rom_dir / source.name)
                        copied_count += 1
                    except Exception as e:
                        _status(status_q, f"⚠️ Error copying BIOS {name}: {e}")
                found = True
                break
        
        if not found:
            desc = metadata_map.get(f"{name}.zip", "Required Parent/BIOS")
            missing_bios.append(f"{name}.zip - {desc}")

    # 3. CHDs
    for chd_rel_path in chd_list:
        # chd_rel_path is "gamename/file.chd"
        source_chd = rom_dir / chd_rel_path
        if source_chd.exists():
            dest_folder = out_rom_dir / source_chd.parent.name
            dest_folder.mkdir(exist_ok=True)
            try:
                shutil.copy2(source_chd, dest_folder / source_chd.name)
                copied_count += 1
            except Exception as e:
                _status(status_q, f"⚠️ Error copying CHD {chd_rel_path}: {e}")
        else:
            desc = metadata_map.get(chd_rel_path, "Unknown CHD")
            missing_chds.append(f"{chd_rel_path} - {desc}")

    # 4. Samples
    if sample_dir and sample_dir.is_dir():
        for sample_name in sample_list:
            source_sample = sample_dir / f"{sample_name}.zip"
            if source_sample.exists():
                try:
                    shutil.copy2(source_sample, out_sample_dir / source_sample.name)
                    copied_count += 1
                except Exception as e:
                    _status(status_q, f"⚠️ Error copying Sample {sample_name}: {e}")
            else:
                desc = metadata_map.get(f"{sample_name}.zip", "Unknown Sample")
                missing_samples.append(f"{sample_name}.zip - {desc}")

    _status(status_q, f"✅ Operation complete. {copied_count} files copied.")
    _status(status_q, f"⚠️ Found {len(missing_roms)} missing ROMs. See filter_log.txt for details.")

    # v4.20: Append Audit Report to Log
    with open(debug_path, "a", encoding="utf-8") as dbg:
        dbg.write("\n\n" + "="*60 + "\n")
        dbg.write("MISSING ASSETS REPORT\n")
        dbg.write("The following files were required by your selected games but were NOT found in your source folders.\n")
        dbg.write("To fix these games, locate these files and add them to your source directories.\n")
        dbg.write("="*60 + "\n")

        if missing_bios:
            dbg.write(f"\n[MISSING BIOS / PARENT SETS] ({len(missing_bios)})\n")
            dbg.write("* These are critical. Many games will not run without them.\n")
            for item in sorted(missing_bios):
                dbg.write(f" - {item}\n")
        else:
            dbg.write("\n[MISSING BIOS] None! All required BIOS files were found.\n")

        if missing_roms:
            dbg.write(f"\n[MISSING GAME ROMS] ({len(missing_roms)})\n")
            for item in sorted(missing_roms):
                dbg.write(f" - {item}\n")
        
        if missing_chds:
            dbg.write(f"\n[MISSING CHDS (Hard Drives)] ({len(missing_chds)})\n")
            for item in sorted(missing_chds):
                dbg.write(f" - {item}\n")

        if missing_samples:
            dbg.write(f"\n[MISSING AUDIO SAMPLES] ({len(missing_samples)})\n")
            for item in sorted(missing_samples):
                dbg.write(f" - {item}\n")


def run_sort(config: Dict[str, Any], status_q: Optional[queue.Queue] = None) -> None:
    script_dir = get_base_path()

    xml_path = Path(config.get("full_xml") or (script_dir / "full.xml"))
    rom_dir = Path(config.get("rom_dir") or script_dir)
    sample_dir_str = config.get("sample_dir")
    sample_dir = Path(sample_dir_str) if sample_dir_str else None

    out_base_dir = Path(config.get("output_path") or "filtered_mame_set")
    if not out_base_dir.is_absolute():
        out_base_dir = script_dir / out_base_dir

    out_rom_dir = out_base_dir / "roms"
    out_sample_dir = out_base_dir / "samples"
    out_rom_dir.mkdir(parents=True, exist_ok=True)
    out_sample_dir.mkdir(parents=True, exist_ok=True)

    debug_path = script_dir / "filter_log.txt"

    if not xml_path.exists():
        raise FileNotFoundError(f"full.xml not found: {xml_path}")
    if not rom_dir.is_dir():
        raise FileNotFoundError(f"ROM directory invalid: {rom_dir}")

    catver_cfg = config.get("catver_path") or (script_dir / "catver.ini")
    catver_map = load_catver(Path(catver_cfg), status_q=status_q)

    _status(status_q, "🔍 Parsing full.xml and applying filters…")
    
    # v4.20: Unpacking new return values
    roms, bios, chds, samples, meta_map = parse_full_xml(
        xml_path,
        config,
        debug_path,
        status_q=status_q,
        catver_map=catver_map,
    )

    total_assets = len(roms) + len(bios) + len(chds) + len(samples)
    _status(status_q, f"📁 Filter matched {total_assets} potential assets.")

    copy_assets(
        roms, bios, chds, samples, meta_map,
        rom_dir, sample_dir, out_rom_dir, out_sample_dir,
        debug_path, status_q
    )
    _status(status_q, f"📄 Missing Assets Report written to: {debug_path}")

# -------------------------------
# Preset utilities
# -------------------------------

def save_preset(path: Path, config: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_preset(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------------
# GUI: XML Scanner
# -------------------------------

def scan_xml_for_locales(xml_path: Path) -> Tuple[List[str], List[str]]:
    KNOWN_REGIONS = {
        "argentina", "asia", "australia", "austria", "belgium", "brazil",
        "canada", "china", "denmark", "europe", "euro", "finland",
        "france", "germany", "greece", "hispanic", "hong kong", "ireland",
        "italy", "japan", "korea", "netherlands", "new zealand", "norway",
        "poland", "portugal", "russia", "scandinavia", "singapore", "spain",
        "sweden", "switzerland", "taiwan", "uk", "usa", "us", "world",
        "w", "j", "u", "e", "a",
    }

    regions, languages = set(), set()
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        entries = list(root.findall("machine")) or list(root.findall("game"))
        for m in entries:
            desc = m.findtext("description", "")
            if "(" not in desc and ")" not in desc:
                continue
            tags_in_desc = re.findall(r"\((.*?)\)", desc)
            for tag_group in tags_in_desc:
                parts = [p.strip().lower() for p in tag_group.split(",")]
                for part in parts:
                    if not part:
                        continue
                    if part in KNOWN_LANGUAGES:
                        languages.add(part)
                    elif part in KNOWN_REGIONS:
                        regions.add(part)
    except Exception:
        return [], []
    return sorted(list(regions)), sorted(list(languages))

# -------------------------------
# GUI: CatVer Scanner
# -------------------------------

def scan_catver_for_genres(catver_path: Path) -> List[str]:
    if not catver_path.exists():
        return []
    
    mapping = load_catver(catver_path)
    unique_genres = set()
    
    for cat_str in mapping.values():
        main_genre = get_main_genre(cat_str)
        if main_genre in EXCLUDED_GENRES:
            continue
        if main_genre and main_genre != "Unknown":
            unique_genres.add(main_genre)
    
    return sorted(list(unique_genres))
# -------------------------------
# GUI layer (Tkinter)
# -------------------------------

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        
        def _configure_window(event):
            canvas.itemconfig(window_id, width=event.width)

        window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", _configure_window)
        
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mouse(_event):
            canvas.bind_all("<MouseWheel>", _on_mouse_wheel)

        def _unbind_mouse(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mouse)
        canvas.bind("<Leave>", _unbind_mouse)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class SorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAME Smart ROM Sorter (Tkinter) — v4.20")
        self.root.withdraw()
        self.show_splash_screen()
        self.root.deiconify()
        self.root.state("zoomed")
        self.root.minsize(1024, 768)

        self.status_q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None

        self.genre_vars: Dict[str, tk.BooleanVar] = {}

        self.player_values = [str(i) for i in range(1, 17)] + ["All"]
        self.control_values = [
            "joystick", "trackball", "spinner", "dial", "paddle",
            "lightgun", "positional", "mouse", "pedal",
            "stick (analog)", "keyboard", "buttons only", "other", "all",
        ]
        self.direction_values = [
            "4-way", "8-way", "2-way horizontal", "2-way vertical",
            "49-way", "rotary", "analog", "All",
        ]

        self.script_dir = get_base_path()
        self._create_widgets()
        self.process_queue()
        self.start_xml_scan()
        self.start_catver_scan()

    def _open_link(self, url: str) -> None:
        webbrowser.open_new(url)

    def show_splash_screen(self) -> None:
        splash = tk.Toplevel(self.root)
        splash.title("Welcome")
        splash.transient(self.root)
        splash.grab_set()

        main_frame = ttk.Frame(splash, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(
            main_frame,
            text="MAME Smart ROM Sorter v4.20",
            font=("Helvetica", 14, "bold"),
        ).pack(pady=(0, 15))

        disclaimer_text = (
            "This software is provided 'as-is' without any express or implied warranty. "
            "In no event shall the authors be held liable for any damages arising from the use "
            "of this software, including data loss or hardware issues. You are solely responsible "
            "for ensuring you have the legal right to possess and use any ROM files in accordance "
            "with the laws of your jurisdiction. By clicking 'Agree & Continue,' you acknowledge "
            "and accept these terms."
        )
        disclaimer_frame = ttk.LabelFrame(main_frame, text="Disclaimer & Agreement", padding=10)
        disclaimer_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(disclaimer_frame, text=disclaimer_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)

        instructions_text = (
            "This tool requires the following to function correctly:\n\n"
            "• A `full.xml` file generated from your MAME installation.\n"
            "• A Non-Merged ROM set so each game's zip is self-contained.\n"
            "• (Recommended) A `catver.ini` file that matches your MAME version.\n\n"
            "For modern MAME versions, CatVer files are available from progetto-SNAPS.\n"
            "For older fixed versions (e.g., MAME 0.78), legacy CatVer packs are available from Catlist / MAMEWorld.\n\n"
            "This version includes full dependency handling. It intelligently finds and copies all required BIOS sets "
            "(like `neogeo.zip`), CHDs (for games with hard drives), and Samples (for custom sounds), making your "
            "new set plug-and-play."
        )
        instructions_frame = ttk.LabelFrame(main_frame, text="First-Time Setup", padding=10)
        instructions_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(instructions_frame, text=instructions_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)

        support_frame = ttk.LabelFrame(main_frame, text="Support & Community", padding=10)
        support_frame.pack(pady=10, fill=tk.X, expand=True)

        yt_link = ttk.Label(
            support_frame,
            text="Subscribe on YouTube",
            foreground="blue",
            cursor="hand2",
        )
        yt_link.pack(anchor=tk.W)
        yt_link.bind(
            "<Button-1>",
            lambda e: self._open_link(
                "https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1"
            ),
        )

        coffee_link = ttk.Label(
            support_frame,
            text="Buy Me a Coffee",
            foreground="blue",
            cursor="hand2",
        )
        coffee_link.pack(anchor=tk.W, pady=(5, 0))
        coffee_link.bind(
            "<Button-1>",
            lambda e: self._open_link("https://buymeacoffee.com/technicallynota"),
        )

        catver_new_link = ttk.Label(
            support_frame,
            text="CatVer for modern MAME (progetto-SNAPS)",
            foreground="blue",
            cursor="hand2",
        )
        catver_new_link.pack(anchor=tk.W, pady=(5, 0))
        catver_new_link.bind(
            "<Button-1>",
            lambda e: self._open_link("https://www.progettosnaps.net/catver/"),
        )

        catver_legacy_link = ttk.Label(
            support_frame,
            text="CatVer for older sets (Catlist / MAMEWorld)",
            foreground="blue",
            cursor="hand2",
        )
        catver_legacy_link.pack(anchor=tk.W)
        catver_legacy_link.bind(
            "<Button-1>",
            lambda e: self._open_link("https://catlist.mameworld.info/"),
        )

        ttk.Button(main_frame, text="Agree & Continue", command=splash.destroy).pack(pady=20)

        splash.update_idletasks()
        
        req_width = splash.winfo_reqwidth()
        req_height = splash.winfo_reqheight()
        
        width = max(req_width, 700)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        height = min(max(req_height, 650), screen_height - 100)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        if y < 30: y = 30
        
        splash.geometry(f"{width}x{height}+{x}+{y}")
        splash.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def auto_detect_paths(self):
        root_dir = filedialog.askdirectory(title="Select MAME Root Folder")
        if not root_dir:
            return
        
        root_path = Path(root_dir)
        
        roms_path = None
        if (root_path / "roms").exists():
            roms_path = root_path / "roms"
        elif (root_path / "ROMS").exists():
            roms_path = root_path / "ROMS"
        else:
            try:
                for item in root_path.iterdir():
                    if item.is_dir() and item.name.lower() == "roms":
                        roms_path = item
                        break
            except Exception:
                pass
        
        if roms_path:
            self.roms_var.set(str(roms_path))
        else:
            self.log(f"⚠️ Warning: Could not find 'roms' folder in {root_dir}")
        
        samples_path = root_path / "samples"
        if samples_path.exists():
            self.samples_var.set(str(samples_path))
            
        xml_path = root_path / "full.xml"
        if not xml_path.exists():
            xml_path = root_path / "mame.xml"
        if xml_path.exists():
            self.xml_var.set(str(xml_path))
            self.start_xml_scan()
            
        cat_path = root_path / "catver.ini"
        if not cat_path.exists():
            cat_path = root_path / "dats" / "catver.ini"
        if not cat_path.exists():
            cat_path = root_path / "hash" / "catver.ini"
        
        if cat_path.exists():
            self.catver_var.set(str(cat_path))
            self.start_catver_scan()
            
        self.log(f"✅ Auto-detected paths from: {root_dir}")

    def _create_widgets(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        scrollable_outer_frame = ScrollableFrame(paned_window)
        main_frame = scrollable_outer_frame.scrollable_frame

        paths_frame = ttk.LabelFrame(main_frame, text="1. Paths & Configuration", padding="10")
        paths_frame.pack(fill=tk.X, expand=True, pady=5, padx=10)
        
        ttk.Button(paths_frame, text="✨ Auto-Select MAME Root Folder", command=self.auto_detect_paths).pack(fill=tk.X, pady=(0, 10))
        
        paths_grid = ttk.Frame(paths_frame)
        paths_grid.pack(fill=tk.X)
        paths_grid.columnconfigure(1, weight=1)

        default_roms = str(self.script_dir)
        if (self.script_dir / "roms").exists():
            default_roms = str(self.script_dir / "roms")
        elif (self.script_dir / "ROMS").exists():
             default_roms = str(self.script_dir / "ROMS")

        self.roms_var = tk.StringVar(value=default_roms)
        self.samples_var = tk.StringVar(value=str(self.script_dir / "samples"))
        self.xml_var = tk.StringVar(value=str(self.script_dir / "full.xml"))
        self.catver_var = tk.StringVar(value=str(self.script_dir / "catver.ini"))
        self.out_var = tk.StringVar(value="filtered_mame_set")

        ttk.Label(paths_grid, text="ROMs:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(paths_grid, textvariable=self.roms_var).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(paths_grid, text="Browse", command=self.browse_roms).grid(row=0, column=2)
        
        ttk.Label(paths_grid, text="Samples:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(paths_grid, textvariable=self.samples_var).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(paths_grid, text="Browse", command=self.browse_samples).grid(row=1, column=2)

        ttk.Label(paths_grid, text="XML:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(paths_grid, textvariable=self.xml_var).grid(row=2, column=1, sticky=tk.EW)
        ttk.Button(paths_grid, text="Browse", command=self.browse_xml).grid(row=2, column=2)

        ttk.Label(paths_grid, text="CatVer:").grid(row=3, column=0, sticky=tk.W)
        ttk.Entry(paths_grid, textvariable=self.catver_var).grid(row=3, column=1, sticky=tk.EW)
        ttk.Button(paths_grid, text="Browse", command=self.browse_catver).grid(row=3, column=2)

        ttk.Label(paths_grid, text="Output:").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(paths_grid, textvariable=self.out_var).grid(row=4, column=1, sticky=tk.EW, columnspan=2)

        mid_frame = ttk.Frame(main_frame)
        mid_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        left_panel = ttk.Frame(mid_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        controls_frame = ttk.LabelFrame(left_panel, text="🎮 Controls", padding=5)
        controls_frame.pack(fill=tk.X, pady=5)
        
        p_b_frame = ttk.Frame(controls_frame)
        p_b_frame.pack(fill=tk.X, pady=5)
        
        self.players_var = tk.StringVar(value="2")
        self.buttons_var = tk.StringVar(value="6")
        ttk.Label(p_b_frame, text="Players:").pack(side=tk.LEFT)
        ttk.Combobox(p_b_frame, textvariable=self.players_var, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=(5,10))
        ttk.Label(p_b_frame, text="Buttons:").pack(side=tk.LEFT)
        ttk.Combobox(p_b_frame, textvariable=self.buttons_var, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=5)

        types_frame = ttk.LabelFrame(controls_frame, text="Input Types")
        types_frame.pack(fill=tk.X, pady=5)
        self.control_vars: Dict[str, tk.BooleanVar] = {}
        for i, val in enumerate(self.control_values):
            self.control_vars[val] = tk.BooleanVar()
            chk = ttk.Checkbutton(types_frame, text=val.title(), variable=self.control_vars[val])
            chk.grid(row=i//2, column=i%2, sticky='w')

        dirs_frame = ttk.LabelFrame(controls_frame, text="Joystick Directions")
        dirs_frame.pack(fill=tk.X, pady=5)
        self.dir_vars: Dict[str, tk.BooleanVar] = {}
        for i, val in enumerate(self.direction_values):
            self.dir_vars[val] = tk.BooleanVar()
            chk = ttk.Checkbutton(dirs_frame, text=val, variable=self.dir_vars[val])
            chk.grid(row=i//2, column=i%2, sticky='w')

        self.strict_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Strict Mode", variable=self.strict_var).pack(pady=5)

        filters_frame = ttk.LabelFrame(left_panel, text="Other Filters", padding=5)
        filters_frame.pack(fill=tk.X, pady=5)
        
        self.orientation_var = tk.StringVar(value="horizontal")
        ttk.Radiobutton(filters_frame, text="Horizontal", variable=self.orientation_var, value="horizontal").pack(anchor=tk.W)
        ttk.Radiobutton(filters_frame, text="Vertical", variable=self.orientation_var, value="vertical").pack(anchor=tk.W)
        ttk.Radiobutton(filters_frame, text="Both", variable=self.orientation_var, value="both").pack(anchor=tk.W)
        
        self.working_var = tk.BooleanVar(value=True)
        self.mature_var = tk.BooleanVar(value=False)
        self.clones_var = tk.BooleanVar(value=False)
        self.bootlegs_var = tk.BooleanVar(value=False)
        self.prototypes_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(filters_frame, text="Working Only", variable=self.working_var).pack(anchor=tk.W)
        ttk.Checkbutton(filters_frame, text="Mature", variable=self.mature_var).pack(anchor=tk.W)
        ttk.Checkbutton(filters_frame, text="Clones", variable=self.clones_var).pack(anchor=tk.W)
        ttk.Checkbutton(filters_frame, text="Bootlegs", variable=self.bootlegs_var).pack(anchor=tk.W)
        ttk.Checkbutton(filters_frame, text="Prototypes", variable=self.prototypes_var).pack(anchor=tk.W)

        right_panel = ttk.Frame(mid_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        genre_frame = ttk.LabelFrame(right_panel, text="🎲 Genres (Auto-Detected)", padding=5)
        genre_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.genre_canvas = tk.Canvas(genre_frame, highlightthickness=0)
        genre_scroll = ttk.Scrollbar(genre_frame, orient="vertical", command=self.genre_canvas.yview)
        self.genre_canvas.config(yscrollcommand=genre_scroll.set)
        
        self.genre_inner_frame = ttk.Frame(self.genre_canvas)
        self.genre_canvas.create_window((0,0), window=self.genre_inner_frame, anchor="nw")
        
        self.genre_inner_frame.bind("<Configure>", lambda e: self.genre_canvas.config(scrollregion=self.genre_canvas.bbox("all")))
        
        g_btns = ttk.Frame(genre_frame)
        g_btns.pack(side=tk.BOTTOM, fill=tk.X)
        def toggle_genres(state: bool):
            for var in self.genre_vars.values(): var.set(state)
        ttk.Button(g_btns, text="All", width=5, command=lambda: toggle_genres(True)).pack(side=tk.LEFT)
        ttk.Button(g_btns, text="None", width=5, command=lambda: toggle_genres(False)).pack(side=tk.LEFT)
        
        self.genre_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        genre_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        locale_frame = ttk.LabelFrame(right_panel, text="🌍 Locale Priority", padding=5)
        locale_frame.pack(fill=tk.X, pady=5)
        
        self.region_list_avail, self.region_list_pref = self._create_dual_listbox(locale_frame, "Regions")
        self.lang_list_avail, self.lang_list_pref = self._create_dual_listbox(locale_frame, "Languages")

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.run_button = ttk.Button(action_frame, text="🚀 RUN SORT", command=self.start_sort)
        self.run_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(action_frame, text="💾 Save Preset", command=self.save_preset_gui).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📂 Load Preset", command=self.load_preset_gui).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.Frame(paned_window)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        paned_window.add(scrollable_outer_frame, weight=4)
        paned_window.add(log_frame, weight=1)
        
    def _create_dual_listbox(self, parent, title: str):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=2, padx=2)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Label(frame, text=f"{title}:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text="Preferred:").grid(row=0, column=2, sticky=tk.W)

        list_avail = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=4)
        list_avail.grid(row=1, column=0, sticky=tk.NSEW, rowspan=2)

        list_pref = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=4)
        list_pref.grid(row=1, column=2, sticky=tk.NSEW, rowspan=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=1, rowspan=2, padx=2, sticky=tk.NS)

        def move_items(src, dst):
            selection = src.curselection()
            if not selection: return
            for i in selection[::-1]:
                dst.insert(tk.END, src.get(i))
                src.delete(i)

        def move_up(lst):
            selection = lst.curselection()
            if not selection: return
            for i in selection:
                if i > 0:
                    lst.insert(i - 1, lst.get(i))
                    lst.delete(i + 1)
                    lst.selection_set(i - 1)

        def move_down(lst):
            selection = lst.curselection()
            if not selection: return
            for i in selection[::-1]:
                if i < lst.size() - 1:
                    lst.insert(i + 2, lst.get(i))
                    lst.delete(i)
                    lst.selection_set(i + 1)

        ttk.Button(btn_frame, text=">", width=2, command=lambda: move_items(list_avail, list_pref)).pack(pady=1)
        ttk.Button(btn_frame, text="<", width=2, command=lambda: move_items(list_pref, list_avail)).pack(pady=1)
        ttk.Button(btn_frame, text="▲", width=2, command=lambda: move_up(list_pref)).pack(pady=1)
        ttk.Button(btn_frame, text="▼", width=2, command=lambda: move_down(list_pref)).pack(pady=1)

        return list_avail, list_pref

    def browse_roms(self):
        d = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME ROMs Folder")
        if d:
            self.roms_var.set(d)

    def browse_samples(self):
        d = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME Samples Folder")
        if d:
            self.samples_var.set(d)

    def browse_xml(self):
        f = filedialog.askopenfilename(
            initialdir=self.script_dir,
            title="Select full.xml",
            filetypes=(("XML files", "*.xml"), ("All files", "*.*")),
        )
        if f:
            self.xml_var.set(f)
            self.start_xml_scan()

    def browse_catver(self):
        f = filedialog.askopenfilename(
            initialdir=self.script_dir,
            title="Select catver.ini",
            filetypes=(("INI files", "*.ini"), ("All files", "*.*")),
        )
        if f:
            self.catver_var.set(f)
            self.start_catver_scan()

    def log(self, msg: str):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_xml_scan(self):
        xml_path_str = self.xml_var.get()
        if not xml_path_str:
            return
        xml_path = Path(xml_path_str)
        if not xml_path.exists():
            self.log(f"⚠️ full.xml not found at: {xml_path}")
            return

        self.log(f"🔄 Scanning {xml_path.name} for locales...")

        def worker():
            regions, languages = scan_xml_for_locales(xml_path)
            self.status_q.put(("locales_done", (regions, languages)))

        threading.Thread(target=worker, daemon=True).start()

    def start_catver_scan(self):
        catver_path_str = self.catver_var.get()
        if not catver_path_str:
            return
        catver_path = Path(catver_path_str)
        if not catver_path.exists():
            return

        self.log(f"🔄 Scanning {catver_path.name} for genres...")
        
        def worker():
            genres = scan_catver_for_genres(catver_path)
            self.status_q.put(("genres_done", genres))
        
        threading.Thread(target=worker, daemon=True).start()

    def build_config(self) -> Dict[str, Any]:
        c = [val for val, var in self.control_vars.items() if var.get()]
        d = [val for val, var in self.dir_vars.items() if var.get()]
        p = self.players_var.get()
        b = self.buttons_var.get()

        selected_genres = [g for g, var in self.genre_vars.items() if var.get()]
        
        r_order = list(self.region_list_pref.get(0, tk.END))
        l_order = list(self.lang_list_pref.get(0, tk.END))

        return {
            "rom_dir": self.roms_var.get().strip(),
            "sample_dir": self.samples_var.get().strip(),
            "full_xml": self.xml_var.get().strip(),
            "output_path": (self.out_var.get() or "filtered_mame_set").strip(),
            "players": 99 if str(p).lower() == "all" else int(p),
            "max_buttons": 99 if str(b).lower() == "all" else int(b),
            "controls": [] if any(str(x).lower() == "all" for x in c) else c,
            "directions": [] if any(str(x).lower() == "all" for x in d) else d,
            "strict_controls": self.strict_var.get(),
            "orientation": self.orientation_var.get(),
            "working_only": self.working_var.get(),
            "mature": self.mature_var.get(),
            "include_clones": self.clones_var.get(),
            "include_bootlegs": self.bootlegs_var.get(),
            "include_prototypes": self.prototypes_var.get(),
            "region_order": r_order,
            "language_order": l_order,
            "catver_path": self.catver_var.get().strip(),
            "genres": selected_genres,
        }

    def apply_config_to_gui(self, cfg: Dict[str, Any]) -> None:
        self.roms_var.set(cfg.get("rom_dir", ""))
        self.samples_var.set(cfg.get("sample_dir", ""))
        self.xml_var.set(cfg.get("full_xml", ""))
        self.out_var.set(cfg.get("output_path", "filtered_mame_set"))
        self.catver_var.set(cfg.get("catver_path", str(self.script_dir / "catver.ini")))

        p = cfg.get("players", 99)
        b = cfg.get("max_buttons", 99)
        self.players_var.set("All" if int(p) >= 99 else str(p))
        self.buttons_var.set("All" if int(b) >= 99 else str(b))

        c = cfg.get("controls", [])
        d = cfg.get("directions", [])
        if not c: c = ["all"]
        if not d: d = ["All"]
        for val, var in self.control_vars.items():
            var.set(val in c)
        for val, var in self.dir_vars.items():
            var.set(val in d)
        
        self.strict_var.set(bool(cfg.get("strict_controls", False)))

        self.orientation_var.set((cfg.get("orientation", "horizontal") or "horizontal").lower())
        self.working_var.set(bool(cfg.get("working_only", True)))
        self.mature_var.set(bool(cfg.get("mature", False)))
        self.clones_var.set(bool(cfg.get("include_clones", False)))
        self.bootlegs_var.set(bool(cfg.get("include_bootlegs", False)))
        self.prototypes_var.set(bool(cfg.get("include_prototypes", False)))

        self.start_xml_scan()
        self.start_catver_scan()
        self.status_q.put(("apply_prefs", (cfg.get("region_order", []), cfg.get("language_order", []), cfg.get("genres", []))))

    def save_preset_gui(self):
        cfg = self.build_config()
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], title="Save preset as…")
        if f:
            try:
                save_preset(Path(f), cfg)
                self.log(f"💾 Preset saved: {f}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save preset:\n{e}")

    def load_preset_gui(self):
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load preset…")
        if f:
            try:
                cfg = load_preset(Path(f))
                self.apply_config_to_gui(cfg)
                self.log(f"📂 Preset loaded: {f}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset:\n{e}")

    def start_sort(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log("⚠️ A sort is already in progress.")
            return

        cfg = self.build_config()
        self.log("Starting…")
        self.run_button.config(state=tk.DISABLED)

        def worker():
            try:
                run_sort(cfg, status_q=self.status_q)
                self.status_q.put(("done", "✅ Finished successfully. CHECK LOG FOR MISSING FILES."))
            except Exception as e:
                self.status_q.put(("error", f"❌ Error: {e}"))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def process_queue(self):
        try:
            while True:
                kind, data = self.status_q.get_nowait()
                if kind in ("status", "done", "error"):
                    self.log(data)
                if kind in ("done", "error"):
                    self.run_button.config(state=tk.NORMAL)
                
                if kind == "locales_done":
                    regions, languages = data
                    self.region_list_avail.delete(0, tk.END)
                    self.lang_list_avail.delete(0, tk.END)
                    self.region_list_pref.delete(0, tk.END)
                    self.lang_list_pref.delete(0, tk.END)
                    for r in regions:
                        self.region_list_avail.insert(tk.END, r)
                    for l in languages:
                        self.lang_list_avail.insert(tk.END, l)
                    self.log(f"✅ XML Scan complete. Found {len(regions)} regions and {len(languages)} languages.")
                
                if kind == "genres_done":
                    genres = data
                    for widget in self.genre_inner_frame.winfo_children():
                        widget.destroy()
                    self.genre_vars.clear()
                    
                    genres = sorted(genres)
                    row = 0
                    col = 0
                    max_cols = 3
                    
                    for g in genres:
                        var = tk.BooleanVar(value=True)
                        self.genre_vars[g] = var
                        display_name = GENRE_DISPLAY_MAP.get(g, g)
                        
                        chk = ttk.Checkbutton(self.genre_inner_frame, text=display_name, variable=var)
                        chk.grid(row=row, column=col, sticky='w', padx=5, pady=2)
                        
                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1
                    
                    self.log(f"✅ CatVer Scan complete. Found {len(genres)} unique genres.")

                if kind == "apply_prefs":
                    self.root.after(500, lambda: self._apply_prefs_to_gui_elements(data[0], data[1], data[2]))
                
                self.status_q.task_done()
        except queue.Empty:
            pass
        self.root.after(200, self.process_queue)

    def _apply_prefs_to_gui_elements(self, pref_regions, pref_langs, pref_genres):
        avail_regions = list(self.region_list_avail.get(0, tk.END))
        for item in pref_regions:
            if item in avail_regions:
                idx = avail_regions.index(item)
                self.region_list_pref.insert(tk.END, self.region_list_avail.get(idx))
                self.region_list_avail.delete(idx)
                avail_regions.pop(idx)

        avail_langs = list(self.lang_list_avail.get(0, tk.END))
        for item in pref_langs:
            if item in avail_langs:
                idx = avail_langs.index(item)
                self.lang_list_pref.insert(tk.END, self.lang_list_avail.get(idx))
                self.lang_list_avail.delete(idx)
                avail_langs.pop(idx)
        
        if pref_genres:
            for var in self.genre_vars.values(): var.set(False)
            for g in pref_genres:
                if g in self.genre_vars:
                    self.genre_vars[g].set(True)


def _launch_gui():
    if not GUI_AVAILABLE:
        raise ImportError("Tkinter is required to run the GUI, but it could not be imported.")
    root = tk.Tk()
    SorterApp(root)
    root.mainloop()


# -------------------------------
# Main — decide GUI vs CLI
# -------------------------------

def main():
    script_dir = get_base_path()
    if GUI_AVAILABLE:
        _launch_gui()
    else:
        verify_setup(script_dir)
        cfg = get_user_inputs_cli()
        run_sort(cfg)


if __name__ == "__main__":
    main()