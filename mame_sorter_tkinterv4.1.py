#!/usr/bin/env python3
"""
MAME Smart ROM Sorter — GUI (Tkinter) + CLI v4.1 (Expert Build)
----------------------------------------------------------------
Authors: Shawn Flanagan & Bob Cogito
Date: 2025-10-12

This single file provides BOTH a GUI and a CLI fallback for the MAME Smart
ROM Sorter. The GUI uses Tkinter to ensure portability.

v4.1 Release Notes (Final Expert Polish)
---------------------------------------------
1)  **Smarter Arcade Filtering**: Implemented a multi-factor check to reliably
    identify true arcade machines, filtering out consoles, handhelds, and
    peripherals that were previously included by mistake.
2)  **Correct Sorting Hierarchy**: Reworked the sorting logic to prioritize
    Parent ROMs > Official Clones > Bootlegs, ensuring the best version of
    a game is always preferred.
3)  **Full Dependency Handling**: The script now intelligently detects and
    copies required BIOS, CHD, and Sample files for each kept game.
4)  **MAME-Compliant Output**: The output folder now mirrors MAME's standard
    structure (`roms/`, `samples/`), making the filtered set plug-and-play.
5)  **UI Enhancements**: Updated path inputs to be more specific and intuitive
    for MAME users.
6)  **Expert Arcade Filtering**: Implemented a source-file and category-based
    blocklist to accurately filter out home consoles, computers, and handhelds,
    producing a much cleaner arcade-only set.
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

# Attempt to import GUI libraries. This will determine the mode.
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
    """ Gets the base path, accounting for PyInstaller's temp folder. """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent

# -------------------------------
# Helpers (CLI prompt utilities)
# -------------------------------
def ask_yes_no(prompt: str) -> bool:
    print(f"\n{prompt}")
    print("  A) Yes")
    print("  B) No")
    while True:
        ans = input("> ").strip().upper()
        if ans in ("A", "Y", "YES"): return True
        if ans in ("B", "N", "NO"): return False
        print("❌ Please type A or B (Yes/No).")

def ask_choice(prompt: str, choices: Dict[str, str]) -> str:
    print(f"\n{prompt}")
    for letter, desc in choices.items():
        print(f"  {letter}) {desc}")
    while True:
        answer = input("> ").strip().upper()
        if answer in choices:
            return choices[answer]
        print("❌ Invalid choice. Please enter one of: " + ", ".join(choices.keys()))

def ask_multi(prompt: str, choices: Dict[str,str]) -> List[str]:
    print(f"\n{prompt}")
    for letter, desc in choices.items():
        print(f"  {letter}) {desc}")
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
    print("  • A valid full.xml (from MAME)")
    print("  • A path to your MAME ROMs folder")
    print("  • (Optional) A path to your MAME Samples folder")

# -------------------------------
# CLI input collection (fallback)
# -------------------------------
def get_user_inputs_cli() -> Dict[str,Any]:
    script_dir = get_base_path()
    default_xml = str(script_dir / "full.xml")
    default_roms = str(script_dir)
    default_samples = str(script_dir / "samples")
    default_output = "filtered_mame_set"

    print("\nPaths (leave blank to use defaults shown in brackets)")
    full_xml = input(f"📄 Path to full.xml [default: {default_xml}]: ").strip() or default_xml
    rom_dir = input(f"🎮 Path to MAME ROMs folder [default: {default_roms}]: ").strip() or default_roms
    sample_dir = input(f"🔊 Path to MAME Samples folder (optional) [default: {default_samples}]: ").strip() or default_samples
    output_folder = input(f"📁 Main Output folder name [default: {default_output}]: ").strip() or default_output

    player_choices = dict(zip("ABCDEFGHIJKLMNOPQ", [str(i) for i in range(1, 17)] + ["All"]))
    players_ans = ask_choice("👥 Max simultaneous players on your cab?", player_choices)
    players = 99 if players_ans == "All" else int(players_ans)

    button_choices = dict(zip("ABCDEFGHIJKLMNOPQ", [str(i) for i in range(1, 17)] + ["All"]))
    buttons_ans = ask_choice("🔘 Max ACTION buttons per player? (exclude coin/start)", button_choices)
    max_buttons = 99 if buttons_ans == "All" else int(buttons_ans)

    control_letters = {"A":"joystick","B":"trackball","C":"spinner","D":"dial","E":"paddle","F":"lightgun","G":"positional","H":"mouse","I":"pedal","J":"stick (analog)","K":"keyboard","L":"buttons only","M":"other","N":"all"}
    controls_ans = ask_multi("🎮 Select control types (comma letters, or include 'N' for all):", control_letters)
    controls = [] if any(c.lower()=="all" for c in controls_ans) else controls_ans

    direction_letters = {"A":"4-way","B":"8-way","C":"2-way horizontal","D":"2-way vertical","E":"49-way","F":"rotary","G":"analog","H":"All"}
    directions_ans = ask_multi("🧭 Joystick directions? (comma letters; H for All)", direction_letters)
    directions = [] if any(d.lower()=="all" for d in directions_ans) else directions_ans

    orientation_ans = ask_choice("🖥️ Screen orientation?", {"A":"horizontal","B":"vertical","C":"both"})
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
        "full_xml": full_xml, "rom_dir": rom_dir, "sample_dir": sample_dir, "output_path": output_folder, "players": players,
        "max_buttons": max_buttons, "controls": controls, "directions": directions, "orientation": orientation_ans,
        "working_only": working_only, "mature": mature, 
        "include_clones": include_clones, "include_bootlegs": include_bootlegs, "include_prototypes": include_prototypes,
        "region_order": region_order, "language_order": language_order,
    }

# -------------------------------
# Core filtering utilities
# -------------------------------
CONTROL_KEYWORDS = {
    "joystick": {"joy", "joystick"}, "trackball": {"trackball"}, "spinner": {"spinner"}, 
    "dial": {"dial"}, "paddle": {"paddle"}, "lightgun": {"lightgun", "gun"}, 
    "positional": {"positional"}, "mouse": {"mouse"}, "pedal": {"pedal"}, 
    "stick (analog)": {"analog"}, "keyboard": {"keyboard"}, "buttons only": {"buttons only"}, 
    "other": {"other"}
}
DIRECTION_MAP = {"4-way": {"4"}, "8-way": {"8"}, "2-way horizontal": {"2h","2-h","2 horizontal"}, "2-way vertical": {"2v","2-v","2 vertical"}, "49-way": {"49"}, "rotary": {"rotary","12-way"}, "analog": {"analog"}}
KNOWN_LANGUAGES = {'english', 'japanese', 'spanish', 'french', 'german', 'italian', 'korean', 'chinese', 'dutch', 'en', 'ja', 'es', 'fr', 'de', 'it', 'ko', 'zh', 'nl'}
BOOTLEG_PATTERNS = ['bootleg', 'hack']
PROTOTYPE_PATTERNS = ['prototype', 'beta', 'demo']

# --- EXPERT MAME FILTERING ---
NON_ARCADE_SOURCE_FILES = {
    # Consoles & Handhelds
    "genesis.cpp", "nes.cpp", "snes.cpp", "gamegear.cpp", "gameboy.cpp", "lynx.cpp",
    "pce.cpp", "a2600.cpp", "coleco.cpp", "intv.cpp", "odyssey2.cpp", "vectrex.cpp",
    # Handheld LCD Games
    "hh_tms.cpp", "hh_sm510.cpp",
    # Computers
    "msx.cpp", "spectrum.cpp", "c64.cpp", "amiga.cpp", "ti99.cpp", "x1.cpp", "coco.cpp",
    "apple2.cpp", "mac.cpp", "pc.cpp", "fm7.cpp"
}

def _status(status_q, msg):
    if status_q is not None:
        status_q.put(("status", msg))

def is_actually_an_arcade_machine(machine_element) -> bool:
    """A multi-layered check to reliably identify arcade machines."""
    
    # --- Quick Rejects ---
    if machine_element.get("isdevice") == "yes": return False
    if machine_element.get("ismechanical") == "yes": return False
    if machine_element.get("isbios") == "yes": return False
    if machine_element.get("runnable") == "no": return False

    # --- Layer 1: Source File Heuristic (Most Important) ---
    source_file = machine_element.get("sourcefile")
    if source_file in NON_ARCADE_SOURCE_FILES:
        return False

    # --- Layer 2: Category Check ---
    category_tag = machine_element.find("category")
    if category_tag is not None and category_tag.text:
        category_text = category_tag.text.lower()
        if any(keyword in category_text for keyword in ["console", "handheld", "computer", "system"]):
            return False
            
    # If it passes all checks, it's very likely an arcade machine.
    return True

def _good_driver_status(driver) -> bool:
    if driver is None: return True
    status = (driver.get("status") or "").lower().strip()
    return not status or status in {"good", "perfect"}

def _match_orientation(display, want: str) -> bool:
    if want == "both" or display is None: return True
    rotate = (display.get("rotate") or "0").strip()
    try: r = int(rotate)
    except Exception: r = 0
    is_vertical = r in (90, 270)
    if want == "vertical": return is_vertical
    if want == "horizontal": return not is_vertical
    return True

def _collect_control_tokens(machine) -> (set, set):
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

def _controls_ok(config_controls: List[str], machine) -> bool:
    if not config_controls: return True
    types, _ = _collect_control_tokens(machine)
    if not types: return True
    for want in config_controls:
        kws = CONTROL_KEYWORDS.get(want.lower(), {want.lower()})
        for t in types:
            if any(kw in t.lower() for kw in kws): return True
    return False

def _directions_ok(config_dirs: List[str], machine) -> bool:
    if not config_dirs: return True
    _, dirs = _collect_control_tokens(machine)
    if not dirs: return True
    for want in config_dirs:
        tokens = DIRECTION_MAP.get(want, {want.lower()})
        for d in dirs:
            if any(tok in d.lower() for tok in tokens): return True
    return False

def _players_ok(limit: int, machine) -> bool:
    if limit >= 99 or machine.find("input") is None: return True
    try: return int(machine.find("input").get("players")) <= int(limit)
    except Exception: return True

def _buttons_ok(limit: int, machine) -> bool:
    if limit >= 99 or machine.find("input") is None: return True
    try: return int(machine.find("input").get("buttons")) <= int(limit)
    except Exception: return True

def _clone_status(machine) -> Tuple[int, bool]:
    cloneof = machine.get("cloneof")
    if not cloneof:
        return 0, False # Parent
    
    desc = machine.findtext("description", "").lower()
    
    is_bootleg = any(p in desc for p in BOOTLEG_PATTERNS)
    if is_bootleg:
        return 2, True # Bootleg
    
    is_prototype = any(p in desc for p in PROTOTYPE_PATTERNS)
    if is_prototype:
        return 3, True # Prototype
        
    return 1, False # Official Clone

def _mature_ok(include_mature: bool, machine) -> bool:
    cat = machine.find("category")
    desc = machine.findtext("description", "")
    blob = f"{cat.text if cat is not None else ''} {desc or ''}".lower()
    if any(x in blob for x in ["mature","adult","mahjong (strip)","erotic","nsfw","xxx", "(nude)"]):
        return include_mature
    return True

def _region_score(name: str, desc: str, region_order: List[str]) -> int:
    if not region_order: return 0
    text = f"{name} {desc}".lower()
    for idx, token in enumerate(region_order):
        if token.strip().lower() in text: return idx
    return len(region_order) + 1

def parse_full_xml(xml_path: Path, config: Dict[str,Any], debug_path: Path, status_q=None) -> List[Dict[str,Any]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    entries = list(root.findall("machine")) or list(root.findall("game"))
    _status(status_q, f"XML loaded: {len(entries)} entries detected…")

    matched, skip_reasons = [], Counter()
    
    for m in entries:
        clone_score, is_unwanted_type = _clone_status(m)
        if clone_score == 1 and not config.get("include_clones"): skip_reasons["clone_type"]+=1; continue
        if clone_score == 2 and not config.get("include_bootlegs"): skip_reasons["clone_type"]+=1; continue
        if clone_score == 3 and not config.get("include_prototypes"): skip_reasons["clone_type"]+=1; continue
        
        if not is_actually_an_arcade_machine(m): skip_reasons["not_arcade"] += 1; continue
        if config.get("working_only", False) and not _good_driver_status(m.find("driver")): skip_reasons["not_working"] += 1; continue
        if not _mature_ok(config.get("mature", False), m): skip_reasons["mature"] += 1; continue
        if not _match_orientation(m.find("display"), config.get("orientation","both")): skip_reasons["orientation"] += 1; continue
        if not _players_ok(config.get("players", 99), m): skip_reasons["players"] += 1; continue
        if not _buttons_ok(config.get("max_buttons", 99), m): skip_reasons["buttons"] += 1; continue
        if not _controls_ok(config.get("controls", []), m): skip_reasons["controls"] += 1; continue
        if not _directions_ok(config.get("directions", []), m): skip_reasons["directions"] += 1; continue
        
        name = m.get("name") or ""
        description = m.findtext("description", "")
        region_score_val = _region_score(name, description, config.get("region_order", []))
        language_score = 0
        if config.get("language_order"):
            langs = config["language_order"]
            text = f"{name} {description}".lower()
            for idx, l in enumerate(langs):
                if l in text:
                    language_score = idx; break
            else:
                language_score = len(langs) + 1
        
        chds = [disk.get("name") for disk in m.findall("disk")]
        samples = [s.get("name") for s in m.findall("sample")]
        if m.get("sampleof"): samples.append(m.get("sampleof"))
        
        bios = m.get("romof")
        
        matched.append({
            "name": name, "description": description, "clone_score": clone_score,
            "region_score": region_score_val, "language_score": language_score,
            "chds": chds, "samples": list(set(samples)), "bios": bios
        })

    _status(status_q, f"Matched {len(matched)} / {len(entries)} after filtering.")
    matched.sort(key=lambda r: (r["clone_score"], r["region_score"], r["language_score"], r["name"]))
    
    deduped, seen_games = [], set()
    final_roms_to_copy, final_chds_to_copy, final_samples_to_copy = set(), set(), set()
    final_log_entries = []

    for r in matched:
        if r["name"] not in seen_games:
            seen_games.add(r["name"])
            final_log_entries.append(r)
            
            final_roms_to_copy.add(r["name"])
            if r.get("bios"): final_roms_to_copy.add(r["bios"])
            for chd in r.get("chds", []): final_chds_to_copy.add(f"{r['name']}/{chd}.chd")
            for sample in r.get("samples", []): final_samples_to_copy.add(sample)

    _status(status_q, f"After dedupe: {len(final_log_entries)} unique titles ready to copy.")
    with open(debug_path, "w", encoding="utf-8") as dbg:
        dbg.write(f"Total parsed: {len(entries)}\nMatched unique: {len(final_log_entries)}\n")
        for k,v in sorted(skip_reasons.items()): dbg.write(f"Skipped {k}: {v}\n")
        dbg.write("\nKept list (best-first):\n")
        for i, r in enumerate(final_log_entries, 1): dbg.write(f"{i:4d}. {r['name']} — {r['description']}\n")
    
    return list(final_roms_to_copy), list(final_chds_to_copy), list(final_samples_to_copy)

def copy_assets(rom_list: List[str], chd_list: List[str], sample_list: List[str],
                rom_dir: Path, sample_dir: Optional[Path],
                out_rom_dir: Path, out_sample_dir: Path, status_q=None):
    
    total_assets = len(rom_list) + len(chd_list) + len(sample_list)
    copied_count = 0
    
    # 1. Copy ROMs (zips and 7z)
    for name in rom_list:
        source_zip = rom_dir / f"{name}.zip"
        source_7z = rom_dir / f"{name}.7z"
        source_file = None
        if source_zip.exists(): source_file = source_zip
        elif source_7z.exists(): source_file = source_7z
        
        if source_file:
            try:
                shutil.copy2(source_file, out_rom_dir / source_file.name)
                copied_count += 1
            except Exception as e:
                _status(status_q, f"⚠️ ROM copy failed: {e}")
        
    # 2. Copy CHDs
    for chd_path_str in chd_list:
        source_chd = rom_dir / chd_path_str
        if source_chd.exists():
            dest_folder = out_rom_dir / source_chd.parent.name
            dest_folder.mkdir(exist_ok=True)
            try:
                shutil.copy2(source_chd, dest_folder / source_chd.name)
                copied_count += 1
            except Exception as e:
                _status(status_q, f"⚠️ CHD copy failed: {e}")

    # 3. Copy Samples
    if sample_dir and sample_dir.is_dir():
        for sample_name in sample_list:
            source_sample = sample_dir / f"{sample_name}.zip"
            if source_sample.exists():
                try:
                    shutil.copy2(source_sample, out_sample_dir / source_sample.name)
                    copied_count += 1
                except Exception as e:
                    _status(status_q, f"⚠️ Sample copy failed: {e}")
    
    _status(status_q, f"✅ Copy complete. {copied_count} asset files copied.")

# -------------------------------
# Public API
# -------------------------------
def run_sort(config: Dict[str,Any], status_q: Optional[queue.Queue]=None) -> None:
    script_dir = get_base_path()
    xml_path = Path(config.get("full_xml") or (script_dir / "full.xml"))
    rom_dir = Path(config.get("rom_dir") or script_dir)
    sample_dir_str = config.get("sample_dir")
    sample_dir = Path(sample_dir_str) if sample_dir_str else None
    
    out_base_dir = Path(config.get("output_path") or "filtered_mame_set")
    if not out_base_dir.is_absolute(): out_base_dir = script_dir / out_base_dir
    
    out_rom_dir = out_base_dir / "roms"
    out_sample_dir = out_base_dir / "samples"
    out_rom_dir.mkdir(parents=True, exist_ok=True)
    out_sample_dir.mkdir(parents=True, exist_ok=True)

    debug_path = script_dir / "filter_log.txt"

    if not xml_path.exists(): raise FileNotFoundError(f"full.xml not found: {xml_path}")
    if not rom_dir.is_dir(): raise FileNotFoundError(f"ROM directory invalid: {rom_dir}")

    _status(status_q, "🔍 Parsing full.xml and applying filters…")
    roms_to_copy, chds_to_copy, samples_to_copy = parse_full_xml(xml_path, config, debug_path, status_q=status_q)
    
    total_assets = len(roms_to_copy) + len(chds_to_copy) + len(samples_to_copy)
    _status(status_q, f"📁 Found {total_assets} total assets to copy to: {out_base_dir}")
    
    copy_assets(roms_to_copy, chds_to_copy, samples_to_copy, rom_dir, sample_dir, out_rom_dir, out_sample_dir, status_q)
    _status(status_q, f"📄 Debug log written to: {debug_path}")

# -------------------------------
# Preset utilities
# -------------------------------
def save_preset(path: Path, config: Dict[str,Any]):
    with open(path, "w", encoding="utf-8") as f: json.dump(config, f, indent=2)

def load_preset(path: Path) -> Dict[str,Any]:
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

# -------------------------------
# GUI: XML Scanner
# -------------------------------
def scan_xml_for_locales(xml_path: Path) -> Tuple[List[str], List[str]]:
    KNOWN_REGIONS = {
        'argentina', 'asia', 'australia', 'austria', 'belgium', 'brazil', 'canada',
        'china', 'denmark', 'europe', 'euro', 'finland', 'france', 'germany',
        'greece', 'hispanic', 'hong kong', 'ireland', 'italy', 'japan', 'korea',
        'netherlands', 'new zealand', 'norway', 'poland', 'portugal', 'russia',
        'scandinavia', 'singapore', 'spain', 'sweden', 'switzerland', 'taiwan',
        'uk', 'usa', 'us', 'world', 'w', 'j', 'u', 'e', 'a'
    }
    regions, languages = set(), set()
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        entries = list(root.findall("machine")) or list(root.findall("game"))
        
        for m in entries:
            desc = m.findtext("description", "")
            if '(' not in desc and ')' not in desc: continue

            tags_in_desc = re.findall(r'\((.*?)\)', desc)
            for tag_group in tags_in_desc:
                parts = [p.strip().lower() for p in tag_group.split(',')]
                for part in parts:
                    if not part: continue
                    if part in KNOWN_LANGUAGES: languages.add(part)
                    elif part in KNOWN_REGIONS: regions.add(part)
    except Exception:
        return [], []
    return sorted(list(regions)), sorted(list(languages))

# -------------------------------
# GUI layer (Tkinter)
# -------------------------------
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_mouse_wheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _bind_mouse(event): canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
        def _unbind_mouse(event): canvas.unbind_all("<MouseWheel>")
        canvas.bind('<Enter>', _bind_mouse)
        canvas.bind('<Leave>', _unbind_mouse)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class SorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAME Smart ROM Sorter (Tkinter) — v4.1")
        self.root.withdraw()
        self.show_splash_screen()
        self.root.deiconify()
        self.root.state('zoomed')
        self.root.minsize(800, 700)
        
        self.status_q = queue.Queue()
        self.worker_thread = None
        self.player_values = [str(i) for i in range(1,17)] + ["All"]
        self.control_values = ["joystick","trackball","spinner","dial","paddle","lightgun","positional","mouse","pedal","stick (analog)","keyboard","buttons only","other","all"]
        self.direction_values = ["4-way","8-way","2-way horizontal","2-way vertical","49-way","rotary","analog","All"]
        self.script_dir = get_base_path()

        self._create_widgets()
        self.process_queue()
        self.start_xml_scan()

    def _open_link(self, url):
        webbrowser.open_new(url)

    def show_splash_screen(self):
        splash = tk.Toplevel(self.root)
        splash.title("Welcome")
        splash.transient(self.root)
        splash.grab_set()
        main_frame = ttk.Frame(splash, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(main_frame, text="MAME Smart ROM Sorter v4.1", font=("Helvetica", 14, "bold")).pack(pady=(0, 15))
        disclaimer_text = "This software is provided 'as-is' without any express or implied warranty. In no event shall the authors be held liable for any damages arising from the use of this software, including data loss or hardware issues. You are solely responsible for ensuring you have the legal right to possess and use any ROM files in accordance with the laws of your jurisdiction. By clicking \"Agree & Continue,\" you acknowledge and accept these terms."
        disclaimer_frame = ttk.LabelFrame(main_frame, text="Disclaimer & Agreement", padding=10)
        disclaimer_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(disclaimer_frame, text=disclaimer_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)
        
        instructions_text = "This tool requires two things from you to function correctly:\n\n• A `full.xml` file generated from your MAME installation.\n• A Non-Merged ROM set. This ensures each game's `.zip` file is self-contained.\n\nThis version now includes full dependency handling. It intelligently finds and copies all required BIOS sets (like `neogeo.zip`), CHDs (for games with hard drives), and Samples (for custom sounds), making your new set plug-and-play."

        instructions_frame = ttk.LabelFrame(main_frame, text="First-Time Setup", padding=10)
        instructions_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(instructions_frame, text=instructions_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)
        support_frame = ttk.LabelFrame(main_frame, text="Support & Community", padding=10)
        support_frame.pack(pady=10, fill=tk.X, expand=True)
        yt_link = ttk.Label(support_frame, text="Subscribe on YouTube", foreground="blue", cursor="hand2")
        yt_link.pack(anchor=tk.W)
        yt_link.bind("<Button-1>", lambda e: self._open_link("https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1"))
        coffee_link = ttk.Label(support_frame, text="Buy Me a Coffee", foreground="blue", cursor="hand2")
        coffee_link.pack(anchor=tk.W, pady=(5,0))
        coffee_link.bind("<Button-1>", lambda e: self._open_link("https://buymeacoffee.com/technicallynota"))
        ttk.Button(main_frame, text="Agree & Continue", command=splash.destroy).pack(pady=20)
        splash.update_idletasks()
        x = self.root.winfo_screenwidth() // 2 - splash.winfo_width() // 2
        y = self.root.winfo_screenheight() // 2 - splash.winfo_height() // 2
        splash.geometry(f"+{x}+{y}")
        splash.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _create_widgets(self):
        self.root.grid_rowconfigure(0, weight=1); self.root.grid_columnconfigure(0, weight=1)
        paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollable_outer_frame = ScrollableFrame(paned_window)
        main_frame = scrollable_outer_frame.scrollable_frame
        
        paths_frame = ttk.LabelFrame(main_frame, text="Paths", padding="10")
        paths_frame.pack(fill=tk.X, expand=True, pady=5, padx=10)
        paths_frame.columnconfigure(1, weight=1)
        self.roms_var = tk.StringVar(value=str(self.script_dir))
        self.samples_var = tk.StringVar(value=str(self.script_dir / "samples"))
        self.xml_var = tk.StringVar(value=str(self.script_dir / "full.xml"))
        self.out_var = tk.StringVar(value="filtered_mame_set")
        
        ttk.Label(paths_frame, text="MAME ROMs Path:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(paths_frame, textvariable=self.roms_var).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(paths_frame, text="Browse...", command=self.browse_roms).grid(row=0, column=2, padx=5)
        
        ttk.Label(paths_frame, text="MAME Samples Path:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(paths_frame, textvariable=self.samples_var).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(paths_frame, text="Browse...", command=self.browse_samples).grid(row=1, column=2, padx=5)

        ttk.Label(paths_frame, text="full.xml:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(paths_frame, textvariable=self.xml_var).grid(row=2, column=1, sticky=tk.EW)
        ttk.Button(paths_frame, text="Browse...", command=self.browse_xml).grid(row=2, column=2, padx=5)
        
        ttk.Label(paths_frame, text="Main Output Folder:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(paths_frame, textvariable=self.out_var).grid(row=3, column=1, sticky=tk.EW, columnspan=2)

        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.pack(fill=tk.X, expand=True, pady=5, padx=10)
        p_b_frame = ttk.Frame(controls_frame)
        p_b_frame.pack(fill=tk.X, expand=True, pady=5)
        self.players_var = tk.StringVar(value="2")
        self.buttons_var = tk.StringVar(value="6")
        ttk.Label(p_b_frame, text="Max Players:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Combobox(p_b_frame, textvariable=self.players_var, values=self.player_values, state="readonly", width=5).pack(side=tk.LEFT)
        ttk.Label(p_b_frame, text="Max Buttons:").pack(side=tk.LEFT, padx=(20,5))
        ttk.Combobox(p_b_frame, textvariable=self.buttons_var, values=self.player_values, state="readonly", width=5).pack(side=tk.LEFT)
        check_outer_frame = ttk.Frame(controls_frame)
        check_outer_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        check_outer_frame.columnconfigure(0, weight=1); check_outer_frame.columnconfigure(1, weight=1)
        controls_check_frame = ttk.LabelFrame(check_outer_frame, text="Control Types", padding=5)
        controls_check_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=(0,5))
        self.control_vars = {}
        for i, val in enumerate(self.control_values):
            self.control_vars[val] = tk.BooleanVar()
            ttk.Checkbutton(controls_check_frame, text=val, variable=self.control_vars[val]).grid(row=i % 7, column=i // 7, sticky=tk.W)
        dirs_check_frame = ttk.LabelFrame(check_outer_frame, text="Joystick Directions", padding=5)
        dirs_check_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=(5,0))
        self.dir_vars = {}
        for i, val in enumerate(self.direction_values):
            self.dir_vars[val] = tk.BooleanVar()
            ttk.Checkbutton(dirs_check_frame, text=val, variable=self.dir_vars[val]).grid(row=i, column=0, sticky=tk.W)

        filters_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filters_frame.pack(fill=tk.X, expand=True, pady=5, padx=10)
        game_types_frame = ttk.LabelFrame(filters_frame, text="Game Types to Include", padding=5)
        game_types_frame.pack(side=tk.RIGHT, padx=(10,0), fill=tk.Y)
        self.clones_var = tk.BooleanVar(value=False)
        self.bootlegs_var = tk.BooleanVar(value=False)
        self.prototypes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(game_types_frame, text="Official Clones", variable=self.clones_var).pack(anchor=tk.W)
        ttk.Checkbutton(game_types_frame, text="Bootlegs & Hacks", variable=self.bootlegs_var).pack(anchor=tk.W)
        ttk.Checkbutton(game_types_frame, text="Prototypes & Demos", variable=self.prototypes_var).pack(anchor=tk.W)
        other_filters_frame = ttk.Frame(filters_frame)
        other_filters_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.orientation_var = tk.StringVar(value="horizontal")
        ttk.Radiobutton(other_filters_frame, text="Horizontal", variable=self.orientation_var, value="horizontal").pack(anchor=tk.W)
        ttk.Radiobutton(other_filters_frame, text="Vertical", variable=self.orientation_var, value="vertical").pack(anchor=tk.W)
        ttk.Radiobutton(other_filters_frame, text="Both", variable=self.orientation_var, value="both").pack(anchor=tk.W)
        self.working_var = tk.BooleanVar(value=True)
        self.mature_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(other_filters_frame, text="Only Working", variable=self.working_var).pack(anchor=tk.W, pady=(10,0))
        ttk.Checkbutton(other_filters_frame, text="Include Mature", variable=self.mature_var).pack(anchor=tk.W)
        
        locale_frame = ttk.LabelFrame(main_frame, text="Locale Preferences", padding="10")
        locale_frame.pack(fill=tk.X, expand=True, pady=5, padx=10)
        self.region_list_avail, self.region_list_pref = self._create_dual_listbox(locale_frame, "Regions")
        self.lang_list_avail, self.lang_list_pref = self._create_dual_listbox(locale_frame, "Languages")

        ttk.Separator(main_frame).pack(fill=tk.X, pady=10)
        button_bar = ttk.Frame(main_frame)
        button_bar.pack(fill=tk.X, expand=True, padx=10, pady=(0,10))
        self.run_button = ttk.Button(button_bar, text="Run", command=self.start_sort)
        self.run_button.pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(button_bar, text="Save Preset", command=self.save_preset_gui).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_bar, text="Load Preset", command=self.load_preset_gui).pack(side=tk.LEFT, padx=5)
        
        log_frame = ttk.Frame(paned_window)
        log_frame.grid_rowconfigure(0, weight=1); log_frame.grid_columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        paned_window.add(scrollable_outer_frame, weight=4)
        paned_window.add(log_frame, weight=1)

    def _create_dual_listbox(self, parent, title: str):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=5)
        frame.columnconfigure(0, weight=1); frame.columnconfigure(2, weight=1)
        ttk.Label(frame, text=f"Available {title}:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text=f"Preferred {title} (in order):").grid(row=0, column=2, sticky=tk.W)
        list_avail = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=6)
        list_avail.grid(row=1, column=0, sticky=tk.NSEW, rowspan=4)
        list_pref = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=6)
        list_pref.grid(row=1, column=2, sticky=tk.NSEW, rowspan=4)
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=1, rowspan=4, padx=5, sticky=tk.NS)
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
                if i > 0: lst.insert(i - 1, lst.get(i)); lst.delete(i+1); lst.selection_set(i - 1)
        def move_down(lst):
            selection = lst.curselection()
            if not selection: return
            for i in selection[::-1]:
                if i < lst.size() - 1: lst.insert(i + 2, lst.get(i)); lst.delete(i); lst.selection_set(i + 1)
        ttk.Button(btn_frame, text=">>", command=lambda: move_items(list_avail, list_pref)).pack(pady=2)
        ttk.Button(btn_frame, text="<<", command=lambda: move_items(list_pref, list_avail)).pack(pady=2)
        ttk.Button(btn_frame, text="▲", command=lambda: move_up(list_pref)).pack(pady=2)
        ttk.Button(btn_frame, text="▼", command=lambda: move_down(list_pref)).pack(pady=2)
        return list_avail, list_pref

    def browse_roms(self):
        dir = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME ROMs Folder")
        if dir: self.roms_var.set(dir)
    
    def browse_samples(self):
        dir = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME Samples Folder")
        if dir: self.samples_var.set(dir)

    def browse_xml(self):
        file = filedialog.askopenfilename(initialdir=self.script_dir, title="Select full.xml", filetypes=(("XML files", "*.xml"),("All files", "*.*")))
        if file: self.xml_var.set(file); self.start_xml_scan()

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_xml_scan(self):
        xml_path_str = self.xml_var.get()
        if not xml_path_str: self.log("⚠️ full.xml path is empty."); return
        xml_path = Path(xml_path_str)
        if not xml_path.exists(): self.log(f"⚠️ full.xml not found at: {xml_path}"); return
        self.log(f"🔄 Scanning {xml_path.name} for locales...")
        def worker():
            regions, languages = scan_xml_for_locales(xml_path)
            self.status_q.put(("locales_done", (regions, languages)))
        threading.Thread(target=worker, daemon=True).start()

    def build_config(self):
        c = [val for val, var in self.control_vars.items() if var.get()]
        d = [val for val, var in self.dir_vars.items() if var.get()]
        p, b = self.players_var.get(), self.buttons_var.get()
        return {
            "rom_dir": self.roms_var.get().strip(), "sample_dir": self.samples_var.get().strip(),
            "full_xml": self.xml_var.get().strip(), "output_path": (self.out_var.get() or "filtered_mame_set").strip(),
            "players": 99 if str(p).lower()=="all" else int(p), "max_buttons": 99 if str(b).lower()=="all" else int(b),
            "controls": [] if any(str(x).lower()=="all" for x in c) else c, "directions": [] if any(str(x).lower()=="all" for x in d) else d,
            "orientation": self.orientation_var.get(), "working_only": self.working_var.get(), "mature": self.mature_var.get(), 
            "include_clones": self.clones_var.get(), "include_bootlegs": self.bootlegs_var.get(), "include_prototypes": self.prototypes_var.get(),
            "region_order": list(self.region_list_pref.get(0, tk.END)), "language_order": list(self.lang_list_pref.get(0, tk.END)),
        }
        
    def apply_config_to_gui(self, cfg):
        self.roms_var.set(cfg.get("rom_dir", "")); self.samples_var.set(cfg.get("sample_dir", ""));
        self.xml_var.set(cfg.get("full_xml", "")); self.out_var.set(cfg.get("output_path", "filtered_mame_set"))
        p,b = cfg.get("players", 99), cfg.get("max_buttons", 99)
        self.players_var.set("All" if int(p) >= 99 else str(p)); self.buttons_var.set("All" if int(b) >= 99 else str(b))
        c, d = cfg.get("controls", []), cfg.get("directions", [])
        if not c: c = ["all"];
        if not d: d = ["All"]
        for val, var in self.control_vars.items(): var.set(val in c)
        for val, var in self.dir_vars.items(): var.set(val in d)
        self.orientation_var.set((cfg.get("orientation","horizontal") or "horizontal").lower())
        self.working_var.set(bool(cfg.get("working_only", True))); self.mature_var.set(bool(cfg.get("mature", False)))
        self.clones_var.set(bool(cfg.get("include_clones", False))); self.bootlegs_var.set(bool(cfg.get("include_bootlegs", False)))
        self.prototypes_var.set(bool(cfg.get("include_prototypes", False)))
        self.start_xml_scan()
        self.status_q.put(("apply_prefs", (cfg.get("region_order", []), cfg.get("language_order", []))))

    def save_preset_gui(self):
        cfg = self.build_config()
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], title="Save preset as…")
        if file:
            try: save_preset(Path(file), cfg); self.log(f"💾 Preset saved: {file}")
            except Exception as e: messagebox.showerror("Error", f"Failed to save preset:\n{e}")

    def load_preset_gui(self):
        file = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load preset…")
        if file:
            try: cfg = load_preset(Path(file)); self.apply_config_to_gui(cfg); self.log(f"📂 Preset loaded: {file}")
            except Exception as e: messagebox.showerror("Error", f"Failed to load preset:\n{e}")

    def start_sort(self):
        if self.worker_thread and self.worker_thread.is_alive(): self.log("⚠️ A sort is already in progress."); return
        cfg = self.build_config()
        self.log("Starting…")
        self.run_button.config(state=tk.DISABLED)
        def worker():
            try: run_sort(cfg, status_q=self.status_q); self.status_q.put(("done","✅ Finished successfully."))
            except Exception as e: self.status_q.put(("error", f"❌ Error: {e}"))
        self.worker_thread = threading.Thread(target=worker, daemon=True); self.worker_thread.start()

    def process_queue(self):
        try:
            while True:
                kind, data = self.status_q.get_nowait()
                if kind in ("status", "done", "error"): self.log(data)
                if kind in ("done", "error"): self.run_button.config(state=tk.NORMAL)
                if kind == "locales_done":
                    regions, languages = data
                    self.region_list_avail.delete(0, tk.END); self.lang_list_avail.delete(0, tk.END)
                    self.region_list_pref.delete(0, tk.END); self.lang_list_pref.delete(0, tk.END)
                    for r in regions: self.region_list_avail.insert(tk.END, r)
                    for l in languages: self.lang_list_avail.insert(tk.END, l)
                    self.log(f"✅ Scan complete. Found {len(regions)} regions and {len(languages)} languages.")
                if kind == "apply_prefs":
                    self.root.after(500, lambda: self._apply_prefs_to_listboxes(data[0], data[1]))
                self.status_q.task_done()
        except queue.Empty: pass
        self.root.after(200, self.process_queue)
        
    def _apply_prefs_to_listboxes(self, pref_regions, pref_langs):
        avail_regions = list(self.region_list_avail.get(0, tk.END))
        for item in pref_regions:
            if item in avail_regions:
                idx = avail_regions.index(item)
                self.region_list_pref.insert(tk.END, self.region_list_avail.get(idx))
                self.region_list_avail.delete(idx); avail_regions.pop(idx)
        avail_langs = list(self.lang_list_avail.get(0, tk.END))
        for item in pref_langs:
            if item in avail_langs:
                idx = avail_langs.index(item)
                self.lang_list_pref.insert(tk.END, self.lang_list_avail.get(idx))
                self.lang_list_avail.delete(idx); avail_langs.pop(idx)

def _launch_gui():
    if not GUI_AVAILABLE: raise ImportError("Tkinter is required to run the GUI, but it could not be imported.")
    root = tk.Tk()
    app = SorterApp(root)
    root.mainloop()

# -------------------------------
# Main — decide GUI vs CLI
# -------------------------------
def main():
    script_dir = get_base_path()
    if GUI_AVAILABLE: _launch_gui()
    else:
        verify_setup(script_dir)
        print("\nℹ️ GUI library (Tkinter) not available — falling back to terminal mode.")
        cfg = get_user_inputs_cli()
        try: run_sort(cfg); print("\n✅ Done. See filter_log.txt for details.")
        except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()