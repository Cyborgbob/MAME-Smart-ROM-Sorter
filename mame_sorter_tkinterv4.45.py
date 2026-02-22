#!/usr/bin/env python3

"""
MAME Smart ROM Sorter — GUI (Tkinter) + CLI v4.45 (The WarGames Audio Update)

----------------------------------------------------------------
Authors: Shawn Flanagan & Bob Cogito

Base: v4.44
v4.45 Changes:
    - ADDED: Built-in Windows audio support (winsound) for Easter egg sound cues.
    - UX: Plays 'play_game.wav' when the Welcome Splash Screen loads.
    - UX: Plays 'game_over.wav' when the copy process successfully finishes.
    - LOGIC: Sound function fails silently and gracefully on non-Windows platforms.
"""

from __future__ import annotations

import os
import sys
import re
import shutil
import queue
import threading
import json
import datetime
import webbrowser
import time
import zipfile
import errno  
import urllib.request
import subprocess
import xml.etree.ElementTree as ET
import platform
from dataclasses import dataclass, field

from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Native Windows Audio (Fails gracefully on Linux/Mac)
try:
    import winsound
except ImportError:
    winsound = None


# -------------------------------
# PyInstaller Path Helper & Globals
# -------------------------------

def get_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent

SCRIPT_DIR = get_base_path()
CURRENT_VERSION = "4.45"

def play_audio_cue(filename: str):
    """Plays a WAV file asynchronously if on Windows."""
    try:
        if winsound and platform.system() == "Windows":
            snd_path = str(SCRIPT_DIR / filename)
            if os.path.exists(snd_path):
                # SND_ASYNC plays in background, SND_NODEFAULT prevents beep on missing file
                winsound.PlaySound(snd_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass  # Silently ignore audio errors


# -------------------------------
# DEFAULT CONFIGURATION 
# -------------------------------

DEFAULT_CONFIG = {
  "schema_version": 1.0,
  "rom_dir": str(SCRIPT_DIR / "roms"),
  "sample_dir": str(SCRIPT_DIR / "samples"),
  "full_xml": str(SCRIPT_DIR / "full.xml"),
  "output_path": str(SCRIPT_DIR / "filtered_mame_set"),
  "players": 2,
  "max_buttons": 8,
  "controls": [
    "joystick",
    "stick (analog)",
    "buttons only"
  ],
  "directions": [
    "4-way",
    "8-way",
    "2-way horizontal",
    "2-way vertical",
    "analog"
  ],
  "strict_controls": False,
  "orientation": "both",
  "emulation_status": "Working & Imperfect",
  "mature": False,
  "include_clones": False,
  "include_bootlegs": True,
  "include_prototypes": False,
  "one_game_one_rom": True,
  "locale_order": [
    "USA", "World", "Australia", "Canada", "UK", "Europe", "Export", "Japan", 
    "Asia", "Southeast Asia", "Hong Kong", "Taiwan", "China", "Korea", "Germany", 
    "Spain", "Italy", "France", "Brazil", "English", "Spanish", "German", 
    "French", "Italian", "Chinese", "Korean", "Japanese", "Portuguese", "Dutch", 
    "Russian", "Arabic", "Hebrew", "Swedish", "Norwegian", "Danish", "Finnish", 
    "Polish", "Czech", "Hungarian", "Greek", "Turkish", "Unknown"
  ],
  "region_order": [
    "USA", "World", "Australia", "Canada", "UK", "Europe", "Export", "Japan", 
    "Asia", "Southeast Asia", "Hong Kong", "Taiwan", "China", "Korea", "Germany", 
    "Spain", "Italy", "France", "Brazil", "Unknown"
  ],
  "language_order": [
    "English", "Spanish", "German", "French", "Italian", "Chinese", "Korean", 
    "Japanese", "Portuguese", "Dutch", "Russian", "Arabic", "Hebrew", "Swedish", 
    "Norwegian", "Danish", "Finnish", "Polish", "Czech", "Hungarian", "Greek", 
    "Turkish", "Unknown"
  ],
  "catver_path": str(SCRIPT_DIR / "catver.ini"),
  "genres": [], 
  "decades": ["Pre-1970s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s", "Unknown"],
  "verbose_log": True
}


# -------------------------------
# CONSTANTS & LINKS
# -------------------------------

GITHUB_API_URL = "https://api.github.com/repos/Cyborgbob/MAME-Smart-ROM-Sorter/releases/latest"
GITHUB_LATEST_URL = "https://github.com/Cyborgbob/MAME-Smart-ROM-Sorter/releases/latest"
GITHUB_URL = "https://github.com/Cyborgbob/MAME-Smart-ROM-Sorter"
YOUTUBE_URL = "https://www.youtube.com/channel/UCRZx8k-2Wxi9-5EEKHCpVlQ/?sub_confirmation=1"
COFFEE_URL = "https://buymeacoffee.com/technicallynota"
MAMEDEV_URL = "https://www.mamedev.org/"
MAMEWIKI_URL = "https://wiki.mamedev.org/index.php?title=Main_Page"
ADB_URL = "http://adb.arcadeitalia.net/"
PROGETTO_URL = "https://www.progettosnaps.net/index.php"
CLRMAME_VID_URL = "https://youtu.be/miXMtHDUeb0"
TNT_WEBSITE_URL = "https://www.technicallynotatechnician.com/"
TNT_USER_GUIDE_URL = "https://youtu.be/GAOdZ947ofs"
TNT_FILTER_GUIDE_URL = "https://youtu.be/IXWbLji_5Jo"
TNT_ROM_EASY_URL = "https://youtu.be/KvEklx52CsI"

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
    "Unknown": "Unknown / No Category",
}

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
    "2-way horizontal": {"2h", "2-h", "2 horizontal", "2"},
    "2-way vertical": {"2v", "2-v", "2 vertical", "2"},
    "49-way": {"49"},
    "rotary": {"rotary", "12-way"},
    "analog": {"analog"},
}

BOOTLEG_PATTERNS = ["bootleg", "hack"]
PROTOTYPE_PATTERNS = ["prototype", "beta", "demo"]

NON_ARCADE_SOURCE_FILES = {
    "genesis.cpp", "nes.cpp", "snes.cpp", "gamegear.cpp", "gameboy.cpp", "lynx.cpp",
    "pce.cpp", "a2600.cpp", "coleco.cpp", "intv.cpp", "odyssey2.cpp", "vectrex.cpp",
    "hh_tms.cpp", "hh_sm510.cpp", "msx.cpp", "spectrum.cpp", "c64.cpp", "amiga.cpp",
    "ti99.cpp", "x1.cpp", "coco.cpp", "apple2.cpp", "mac.cpp", "pc.cpp", "fm7.cpp",
}

MATURE_CAT_MARKERS = ("Mature", "Adult", "XXX", "Erotic")


# -------------------------------
# Data Structures
# -------------------------------

@dataclass
class MachineData:
    name: str
    description: str = ""
    cloneof: Optional[str] = None
    romof: Optional[str] = None
    is_bios: bool = False
    is_mechanical: bool = False
    is_device: bool = False
    runnable: bool = True
    source_file: str = ""
    year: str = ""
    decade_bucket: str = "Unknown" 
    manufacturer: str = ""
    players: int = 0
    buttons: int = 0
    controls: Set[str] = field(default_factory=set)
    directions: Set[str] = field(default_factory=set)
    rotate: int = 0
    driver_status: str = ""
    is_bootleg: bool = False
    is_prototype: bool = False
    chds: List[str] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)
    device_refs: Set[str] = field(default_factory=set)
    rom_count: int = 0  


# -------------------------------
# LOGIC ENGINE
# -------------------------------

class MameSorter:
    def __init__(self, config: Dict[str, Any], status_q: Optional[queue.Queue] = None):
        self.config = config
        self.status_q = status_q
        self.script_dir = SCRIPT_DIR
        self.catver_map = {}
        
        self.summary_log = list(config.get("gui_log_history", []))
        self.verbose_log = config.get("verbose_log", True)
        
        self.user_decision = None 
        self.decision_event = threading.Event()  
        
        self.xml_path = Path(config.get("full_xml") or (self.script_dir / "full.xml"))
        self.rom_dir = Path(config.get("rom_dir") or (self.script_dir / "roms"))
        sample_dir_str = config.get("sample_dir")
        self.sample_dir = Path(sample_dir_str) if sample_dir_str else None
        
        out_base_dir = Path(config.get("output_path") or "filtered_mame_set")
        if not out_base_dir.is_absolute():
            out_base_dir = self.script_dir / out_base_dir
        
        self.out_base_dir = out_base_dir
        self.out_rom_dir = out_base_dir / "roms"
        self.out_sample_dir = out_base_dir / "samples"
        self.debug_path = self.script_dir / "filter_log.txt"

        self.all_machines: Dict[str, MachineData] = {}
        self.skip_reasons = Counter()

    def _log(self, msg: str):
        self.summary_log.append(msg)
        if self.status_q:
            self.status_q.put(("status", msg))
        else:
            print(msg)

    def load_resources(self):
        catver_path = Path(self.config.get("catver_path") or (self.script_dir / "catver.ini"))
        if catver_path.exists():
            self._log(f"📚 Loading CatVer from {catver_path.name}...")
            self.catver_map = load_catver(catver_path, log_cb=self._log)
        else:
            self._log("⚠️ catver.ini not found. Genre filtering will be limited.")

    def parse_xml_iterative(self):
        self._log(f"🔄 Streaming {self.xml_path.name}... (Iterparse Enabled)")
        
        context = ET.iterparse(self.xml_path, events=("end",))
        count = 0
        
        for event, elem in context:
            if elem.tag == "machine" or elem.tag == "game":
                m = self._extract_machine_data(elem)
                self.all_machines[m.name] = m
                count += 1
                if count % 5000 == 0:
                    self._log(f"   Scanned {count} machines...")
                elem.clear()
        
        self._log(f"✅ Indexed {len(self.all_machines)} machines.")

    def _extract_machine_data(self, elem) -> MachineData:
        name = elem.get("name")
        desc = elem.findtext("description", "")
        year = elem.findtext("year", "")
        
        decade_bucket = "Unknown"
        year_str = year[:4] if year else ""
        if year_str.isdigit():
            y = int(year_str)
            if y < 1970: decade_bucket = "Pre-1970s"
            elif 1970 <= y < 1980: decade_bucket = "1970s"
            elif 1980 <= y < 1990: decade_bucket = "1980s"
            elif 1990 <= y < 2000: decade_bucket = "1990s"
            elif 2000 <= y < 2010: decade_bucket = "2000s"
            elif 2010 <= y < 2020: decade_bucket = "2010s"
            else: decade_bucket = "2020s"

        cloneof = elem.get("cloneof")
        romof = elem.get("romof")
        is_bios = elem.get("isbios") == "yes"
        is_mech = elem.get("ismechanical") == "yes"
        is_dev = elem.get("isdevice") == "yes"
        runnable = elem.get("runnable") != "no"
        source = elem.get("sourcefile", "")
        
        rom_count = len([r for r in elem.findall("rom") if r.get("name")])
        
        input_node = elem.find("input")
        players = 0
        buttons = 0
        controls = set()
        directions = set()
        
        if input_node is not None:
            try: players = int(input_node.get("players", "0"))
            except: pass
            try: buttons = int(input_node.get("buttons", "0"))
            except: pass
            
            for ctrl in input_node.findall("control"):
                ctype = (ctrl.get("type") or "").lower()
                ways = (ctrl.get("ways") or ctrl.get("ways2") or "").lower()
                if ctype: controls.add(ctype)
                if ways: directions.add(ways)
                try:
                    btns = int(ctrl.get("buttons", "0"))
                    if btns > buttons: buttons = btns
                except: pass

        disp = elem.find("display")
        rotate = 0
        if disp is not None:
            try: rotate = int(disp.get("rotate", "0"))
            except: pass
            
        driver = elem.find("driver")
        status = "good"
        if driver is not None:
            status = driver.get("status", "good")
            
        chds = [d.get("name") for d in elem.findall("disk") if d.get("name")]
        
        samples = []
        sampleof_attr = elem.get("sampleof")
        if sampleof_attr:
            samples.append(sampleof_attr)
        elif elem.find("sample") is not None:
            samples.append(name)
            
        device_refs = set()
        for dref in elem.findall("device_ref"):
            if dref.get("name"):
                device_refs.add(dref.get("name"))

        is_bootleg = any(p in desc.lower() for p in BOOTLEG_PATTERNS)
        is_prototype = any(p in desc.lower() for p in PROTOTYPE_PATTERNS)

        return MachineData(
            name=name, description=desc, year=year, decade_bucket=decade_bucket, 
            cloneof=cloneof, romof=romof, is_bios=is_bios, is_mechanical=is_mech, 
            is_device=is_dev, runnable=runnable, source_file=source,
            players=players, buttons=buttons, controls=controls, directions=directions,
            rotate=rotate, driver_status=status,
            is_bootleg=is_bootleg, is_prototype=is_prototype,
            chds=chds, samples=samples, device_refs=device_refs, rom_count=rom_count
        )

    def detect_set_type(self) -> str:
        self._log("🕵️‍♂️ Running Set Type Detector...")
        clones_checked = 0
        
        for m in self.all_machines.values():
            if clones_checked >= 5: break
            if not m.cloneof or m.is_bios or m.is_device or not m.runnable:
                continue

            clone_zip = self.rom_dir / f"{m.name}.zip"
            clone_7z = self.rom_dir / f"{m.name}.7z"
            parent_zip = self.rom_dir / f"{m.cloneof}.zip"
            parent_7z = self.rom_dir / f"{m.cloneof}.7z"

            clone_exists = clone_zip.exists() or clone_7z.exists()
            parent_exists = parent_zip.exists() or parent_7z.exists()

            if not clone_exists and parent_exists:
                return "Merged"

            if clone_zip.exists():
                try:
                    with zipfile.ZipFile(clone_zip, 'r') as zf:
                        count = len(zf.namelist())
                    if count < m.rom_count:
                        return "Split"
                    clones_checked += 1
                except zipfile.BadZipFile:
                    pass 
            elif clone_7z.exists():
                clones_checked += 1

        return "Non-Merged"

    def filter_candidates(self) -> List[MachineData]:
        self._log("🔍 Applying filters...")
        candidates = []
        selected_genres = set(self.config.get("genres", []))
        selected_decades = set(self.config.get("decades", []))
        strict_controls = self.config.get("strict_controls", False)
        
        status_ranks = {"good": 0, "perfect": 0, "imperfect": 1, "preliminary": 2}
        user_selection = self.config.get("emulation_status", "Working")
        max_rank_allowed = {
            "Working": 0,
            "Working & Imperfect": 1,
            "All (Incl. Preliminary)": 2
        }.get(user_selection, 0)
        
        for m in self.all_machines.values():
            if m.is_bios or m.is_device or m.is_mechanical:
                continue
            
            if not m.runnable:
                self.skip_reasons["Not Runnable"] += 1
                continue
                
            if m.source_file in NON_ARCADE_SOURCE_FILES:
                self.skip_reasons["Non-Arcade Platform Source"] += 1
                continue
                
            m_status = m.driver_status.lower().strip()
            m_rank = status_ranks.get(m_status, 2)
            if m_rank > max_rank_allowed:
                self.skip_reasons[f"Emulation Status ({m_status})"] += 1
                continue

            if selected_decades:
                if m.decade_bucket not in selected_decades:
                    self.skip_reasons[f"Filtered Decade ({m.decade_bucket})"] += 1
                    continue
                
            cat_str = self.catver_map.get(m.name, "Unknown")
            genre = get_main_genre(cat_str)
            
            if selected_genres and genre not in selected_genres:
                self.skip_reasons["Unselected Genre"] += 1
                continue
            
            if genre in EXCLUDED_GENRES:
                self.skip_reasons["Excluded/Non-Game Genre"] += 1
                continue

            if not catver_allows_arcade(m.name, self.catver_map):
                self.skip_reasons["Non-Arcade Categorization"] += 1
                continue

            is_mature_cat = catver_marks_mature(m.name, self.catver_map)
            is_mature_desc = _mature_ok(True, m.description) == False 
            if not self.config.get("mature") and (is_mature_cat or is_mature_desc):
                self.skip_reasons["Mature/Adult Theme"] += 1
                continue

            want_orient = self.config.get("orientation", "both")
            is_vert = m.rotate in (90, 270)
            if want_orient == "horizontal" and is_vert:
                self.skip_reasons["Wrong Orientation (Filtered Vertical)"] += 1
                continue
            if want_orient == "vertical" and not is_vert:
                self.skip_reasons["Wrong Orientation (Filtered Horizontal)"] += 1
                continue

            if not _controls_ok(self.config.get("controls", []), m.controls, strict_controls):
                self.skip_reasons["Filtered Control Type"] += 1
                continue
            if not _directions_ok(self.config.get("directions", []), m.directions):
                self.skip_reasons["Filtered Joystick Direction"] += 1
                continue
            if m.players > self.config.get("players", 99):
                self.skip_reasons["Filtered Player Count"] += 1
                continue
            if m.buttons > self.config.get("max_buttons", 99):
                self.skip_reasons["Filtered Button Count"] += 1
                continue

            use_1g1r = self.config.get("one_game_one_rom", False)
            if not use_1g1r:
                if m.cloneof:
                    if not self.config.get("include_clones"):
                        self.skip_reasons["Filtered Clone"] += 1
                        continue
                if m.is_bootleg and not self.config.get("include_bootlegs"):
                    self.skip_reasons["Filtered Bootleg"] += 1
                    continue
                if m.is_prototype and not self.config.get("include_prototypes"):
                    self.skip_reasons["Filtered Prototype"] += 1
                    continue
            
            candidates.append(m)

        self._log(f"✅ Found {len(candidates)} candidates before 1G1R/Optimization.")
        return candidates

    def apply_1g1r(self, candidates: List[MachineData]) -> List[MachineData]:
        if not self.config.get("one_game_one_rom", False):
            return candidates
        
        self._log("🥇 Applying 1G1R Optimization...")
        
        families = defaultdict(list)
        for m in candidates:
            root = self._get_root_parent(m.name)
            families[root].append(m)
            
        final_list = []

        locale_order = self.config.get("locale_order")
        if not locale_order:
            locale_order = list(self.config.get("region_order", [])) + list(self.config.get("language_order", []))
            seen = set()
            locale_order = [x for x in locale_order if not (x in seen or seen.add(x))]

        if not locale_order:
            locale_order = [
                "World","USA","Europe","Export",
                "Canada","UK","Australia",
                "Germany","France","Spain","Italy",
                "Asia","Southeast Asia","Hong Kong","Taiwan","China","Korea","Japan",
                "English","Spanish","German","French","Italian","Chinese","Korean","Japanese","Czech",
                "Unknown"
            ]

        REGION_MAP = {
            "world": "World", "usa": "USA", "us": "USA", "u s": "USA", "u.s": "USA", "u.s.": "USA",
            "europe": "Europe", "export": "Export", "japan": "Japan", "korea": "Korea", "asia": "Asia",
            "southeast asia": "Southeast Asia", "hong Kong": "Hong Kong", "taiwan": "Taiwan", "china": "China",
            "germany": "Germany", "spain": "Spain", "italy": "Italy", "france": "France", "uk": "UK",
            "u k": "UK", "u.k.": "UK", "canada": "Canada", "brazil": "Brazil", "australia": "Australia",
        }
        LANG_WORDS = [
            "English","Spanish","German","Italian","French", "Chinese","Korean","Japanese","Portuguese","Dutch",
            "Russian","Arabic","Hebrew","Swedish","Norwegian","Danish", "Finnish","Polish","Czech","Hungarian","Greek","Turkish",
        ]

        def _norm(s: str) -> str:
            s = s.lower().replace(".", " ")
            return re.sub(r"\s+", " ", s).strip()

        single_region_keys = [k for k in REGION_MAP.keys() if " " not in k]
        single_region_re = re.compile(r"\b(" + "|".join(map(re.escape, single_region_keys)) + r")\b", re.IGNORECASE)
        multi_region_keys = [k for k in REGION_MAP.keys() if " " in k]
        lang_re = re.compile(r"\b(" + "|".join(map(re.escape, LANG_WORDS)) + r")\b", re.IGNORECASE)
        ger_eng_re = re.compile(r"\bGER\s*/\s*ENG\b", re.IGNORECASE)
        jpn_re = re.compile(r"\bJPN\b", re.IGNORECASE)
        cn_re = re.compile(r"\bCN\b", re.IGNORECASE)

        def extract_locale_tags(desc: str) -> Set[str]:
            tags: Set[str] = set()
            if not desc: return tags
            for tag_group in re.findall(r"\((.*?)\)", desc):
                g = _norm(tag_group)
                for mk in multi_region_keys:
                    if mk in g: tags.add(REGION_MAP[mk])
                for hit in single_region_re.findall(g):
                    tags.add(REGION_MAP[_norm(hit)])
                for hit in lang_re.findall(g):
                    tags.add(hit.capitalize())
                if ger_eng_re.search(tag_group): tags.update(["German","English"])
                if jpn_re.search(tag_group): tags.add("Japan")
                if cn_re.search(tag_group): tags.add("China")
            return tags

        for root, members in families.items():
            def get_score(m: MachineData):
                tags = extract_locale_tags(m.description)
                if not tags: tags = {"Unknown"}

                locale_rank = 999
                for i, opt in enumerate(locale_order):
                    if opt in tags:
                        locale_rank = i
                        break
                if locale_rank == 999 and "Unknown" in locale_order:
                    locale_rank = locale_order.index("Unknown")

                is_parent = (m.name == root)
                status_score = 0 if is_parent else 1
                boot_penalty = 1 if m.is_bootleg else 0
                return (locale_rank, boot_penalty, status_score)

            members.sort(key=get_score)
            best = members[0]
            final_list.append(best)
            
            skipped_members = members[1:]
            if skipped_members:
                self.skip_reasons["Filtered by 1G1R Rule (Lower Priority Clone/Locale)"] += len(skipped_members)
            
        self._log(f"✅ Reduced to {len(final_list)} games after 1G1R.")
        return final_list

    def _get_root_parent(self, name: str) -> str:
        curr = name
        depth = 0
        while depth < 5:
            if curr not in self.all_machines: return curr
            m = self.all_machines[curr]
            if not m.cloneof: return curr
            curr = m.cloneof
            depth += 1
        return curr

    def resolve_dependencies(self, games: List[MachineData]) -> Tuple[Set[str], Set[str], Set[str]]:
        self._log("🔗 Resolving dependencies (Parents, BIOS, Devices)...")
        
        required_sets = set()
        required_chds = set()
        required_samples = set()
        
        check_queue = [m.name for m in games]
        processed = set()
        
        while check_queue:
            curr_name = check_queue.pop(0)
            if curr_name in processed: continue
            processed.add(curr_name)
            
            if curr_name not in self.all_machines: continue
            
            m = self.all_machines[curr_name]
            required_sets.add(curr_name)
            
            if m.cloneof and m.cloneof not in processed:
                if m.cloneof in self.all_machines:
                    parent_m = self.all_machines[m.cloneof]
                    if parent_m.is_bios or parent_m.is_device:
                        check_queue.append(m.cloneof)
            
            if m.romof and m.romof not in processed:
                if m.romof in self.all_machines:
                    romof_m = self.all_machines[m.romof]
                    if romof_m.is_bios or romof_m.is_device:
                        check_queue.append(m.romof)
                        
            for dev in m.device_refs:
                if dev not in processed:
                    check_queue.append(dev)
            for chd in m.chds:
                required_chds.add(f"{m.name}/{chd}.chd")
            for samp in m.samples:
                required_samples.add(samp)

        return required_sets, required_chds, required_samples

    def execute_copy(self, required_sets: Set[str], required_chds: Set[str], required_samples: Set[str]) -> Tuple[List[str], List[str]]:
        self._log(f"📦 Copying assets for {len(required_sets)} sets...")
        
        meta_map = {}
        valid_rom_sets = set()
        
        for name in required_sets:
            desc = "Unknown"
            if name in self.all_machines:
                m = self.all_machines[name]
                desc = m.description
                
                # 10/90 BUG FIX: Only look for a ZIP if the device actually contains physical ROMs.
                if m.rom_count > 0:
                    valid_rom_sets.add(name)
            else:
                valid_rom_sets.add(name)
                
            meta_map[f"{name}.zip"] = desc
        
        self.out_rom_dir.mkdir(parents=True, exist_ok=True)
        self.out_sample_dir.mkdir(parents=True, exist_ok=True)
        
        def _prog_cb(curr: int, tot: int):
            if self.status_q:
                self.status_q.put(("progress", (curr, tot)))

        return copy_assets(
            list(valid_rom_sets), [], list(required_chds), list(required_samples),
            meta_map, self.rom_dir, self.sample_dir,
            self.out_rom_dir, self.out_sample_dir,
            log_cb=self._log,
            progress_cb=_prog_cb
        )

    def _write_log(self, copied: List[str], missing: List[str]):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.debug_path, "w", encoding="utf-8") as f:
            f.write("MAME Smart Sorter Log\n")
            f.write("============================================================\n\n")
            
            f.write("[RUN HEADER]\n")
            f.write(f"Tool version: MAME Smart ROM Sorter v{CURRENT_VERSION}\n")
            f.write(f"Timestamp:    {timestamp}\n")
            f.write(f"XML Path:     {self.xml_path}\n")
            f.write(f"ROMs path:    {self.rom_dir}\n")
            f.write(f"CHD root:     {self.rom_dir}\n")
            f.write(f"Samples path: {self.sample_dir if self.sample_dir else 'Not Configured'}\n")
            f.write(f"Output Base:  {self.out_base_dir} (Creates /roms and /samples here)\n")
            
            preset_path = self.config.get("preset_path")
            if preset_path:
                preset_name = Path(preset_path).name
                f.write(f"Preset info:  {preset_path}, {preset_name}\n")
            f.write("\n")
            
            f.write("[FILTER CHOICES]\n")
            genres = self.config.get("genres", [])
            f.write(f"Enabled Genres:    {len(genres)} selected\n")
            
            decades = self.config.get("decades", [])
            f.write(f"Selected Decades:  {', '.join(decades) if decades else 'None'}\n")
            
            locales = self.config.get("locale_order", [])
            loc_str = ', '.join(locales[:10]) + ('...' if len(locales) > 10 else '')
            f.write(f"Selected Locales:  {loc_str if locales else 'Default'}\n")
            f.write(f"1G1R Optimization: {'ON' if self.config.get('one_game_one_rom') else 'OFF'}\n")
            f.write(f"Emulation Status:  {self.config.get('emulation_status', 'Working')}\n")
            f.write(f"Strict Controls:   {'ON' if self.config.get('strict_controls') else 'OFF'}\n")
            f.write(f"Max Players:       {self.config.get('players', 'All')}\n")
            f.write(f"Max Buttons:       {self.config.get('max_buttons', 'All')}\n")
            
            controls = self.config.get("controls", [])
            if controls: f.write(f"Control Types:     {', '.join(controls)}\n")
            
            dirs = self.config.get("directions", [])
            if dirs: f.write(f"Directions:        {', '.join(dirs)}\n")
            f.write("\n")
            
            f.write("[PIPELINE SUMMARY]\n")
            for line in self.summary_log:
                f.write(f"{line}\n")
            f.write("\n")
            
            f.write(f"[COPIED ASSETS] ({len(copied)})\n")
            if self.verbose_log:
                if copied:
                    for item in sorted(copied):
                        f.write(f" - {item}\n")
                else:
                    f.write(" - None.\n")
            else:
                f.write(" - List omitted (Verbose Logging Disabled in Preset).\n")
            f.write("\n")
            
            if self.skip_reasons:
                f.write("[SKIPPED ASSETS SUMMARY] (Filter Debugging)\n")
                for reason, count in self.skip_reasons.most_common():
                    f.write(f" - {reason}: {count} games skipped\n")
                f.write("\n")
                
            f.write(f"[MISSING ASSETS] ({len(missing)})\n")
            if missing:
                for item in sorted(missing):
                    f.write(f" - {item}\n")
            else:
                f.write(" - SUCCESS: All assets were found and copied successfully.\n")

    def run(self):
        self.load_resources()
        self.parse_xml_iterative()
        
        set_type = self.detect_set_type()
        if set_type in ["Split", "Merged"]:
            self._log(f"⚠️ Warning: {set_type} set detected. Waiting for user input...")
            if self.status_q:
                self.status_q.put(("show_set_warning", set_type))
            
            self.decision_event.wait()
                
            if self.user_decision == "quit":
                self._log("❌ Run aborted by user due to incompatible ROM set.")
                if self.status_q: self.status_q.put(("error", "Sort aborted."))
                return
            else:
                self._log("⚠️ User chose to proceed despite incompatible set warning.")
        else:
            self._log(f"✅ Set Type Confirmed: {set_type} set detected.")

        candidates = self.filter_candidates()
        final_games = self.apply_1g1r(candidates)
        req_sets, req_chds, req_samps = self.resolve_dependencies(final_games)
        
        try:
            copied, missing = self.execute_copy(req_sets, req_chds, req_samps)
            self._log("✅ Finished successfully. CHECK LOG FOR MISSING FILES.")
            self._write_log(copied, missing)
        except Exception as e:
            self._log(f"❌ SORT ABORTED: {e}")
            if self.status_q: self.status_q.put(("error", f"Sort aborted: {e}"))


# -------------------------------
# UTILITIES & LOGIC
# -------------------------------

def load_catver(catver_path: Path, log_cb=None) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not catver_path or not catver_path.exists():
        if log_cb: log_cb(f"⚠️ catver.ini not found at: {catver_path}")
        return mapping

    current_section: Optional[str] = None
    try:
        with catver_path.open("r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(("#", ";")): continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip().lower()
                    continue
                if "=" in line and current_section in (None, "", "category", "catver"):
                    name, cat = line.split("=", 1)
                    mapping[name.strip()] = cat.strip()
    except Exception as e:
        if log_cb: log_cb(f"⚠️ Failed to parse catver.ini: {e}")
        return {}

    if log_cb: log_cb(f"📚 Loaded {len(mapping)} CatVer entries")
    return mapping

def get_main_genre(cat_string: str) -> str:
    if not cat_string: return "Unknown"
    main = cat_string.split(" / ")[0].strip()
    if main.startswith("TTL * "): main = main.replace("TTL * ", "").strip()
    return main

def catver_allows_arcade(name: str, catver_map: Dict[str, str]) -> bool:
    if not catver_map: return True
    cat = catver_map.get(name)
    if not cat: return True
    main = get_main_genre(cat)
    if main in EXCLUDED_GENRES: return False
    return True

def catver_marks_mature(name: str, catver_map: Dict[str, str]) -> bool:
    if not catver_map: return False
    cat = catver_map.get(name)
    if not cat: return False
    return any(m.lower() in cat.lower() for m in MATURE_CAT_MARKERS)

def _mature_ok(include_mature: bool, desc: str) -> bool:
    blob = desc.lower()
    if any(x in blob for x in ["mature", "adult", "mahjong (strip)", "erotic", "nsfw", "xxx", "(nude)"]):
        return include_mature
    return True

def _controls_ok(config_controls: List[str], controls: Set[str], strict: bool) -> bool:
    if not config_controls: return True
    if not controls: return True
    has_allowed = False
    for want in config_controls:
        kws = CONTROL_KEYWORDS.get(want.lower(), {want.lower()})
        for c in controls:
            if any(kw in c.lower() for kw in kws):
                has_allowed = True
                break
        if has_allowed: break
    if not has_allowed: return False
    
    if strict:
        for c in controls:
            is_permitted = False
            for want in config_controls:
                kws = CONTROL_KEYWORDS.get(want.lower(), {want.lower()})
                if any(kw in c.lower() for kw in kws):
                    is_permitted = True
                    break
            if not is_permitted: return False
    return True

def _directions_ok(config_dirs: List[str], directions: Set[str]) -> bool:
    if not config_dirs: return True
    if not directions: return True
    for want in config_dirs:
        tokens = DIRECTION_MAP.get(want, {want.lower()})
        for d in directions:
            d_clean = d.lower()
            if d_clean == "2":
                if "2" in tokens: return True
            if any(tok in d_clean for tok in tokens):
                return True
    return False

def copy_assets(
    rom_list: List[str], bios_list: List[str], chd_list: List[str], sample_list: List[str],
    metadata_map: Dict[str, str], rom_dir: Path, sample_dir: Optional[Path],
    out_rom_dir: Path, out_sample_dir: Path, log_cb=None, progress_cb=None
) -> Tuple[List[str], List[str]]:
    
    total_ops = len(rom_list) + len(bios_list) + len(chd_list) + len(sample_list)
    current_op = 0
    copied_count = 0
    copied_assets = []
    missing_assets = []

    if log_cb: log_cb(f"📦 Processing {total_ops} asset checks...")

    combined_roms = rom_list + bios_list
    for name in combined_roms:
        found = False
        for ext in [".zip", ".7z"]:
            source = rom_dir / f"{name}{ext}"
            if source.exists():
                try:
                    dest_file = out_rom_dir / source.name
                    if not dest_file.exists():
                        shutil.copy2(source, dest_file)
                    copied_count += 1
                    copied_assets.append(f"ROM/BIOS: {source.name}")
                    found = True
                    break
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        if log_cb: log_cb("❌ CRITICAL ERROR: Hard drive is full! Aborting copy.")
                        raise Exception("Hard drive is full!")
                    else:
                        if log_cb: log_cb(f"⚠️ OS Error copying {source.name}: {e}")
                except Exception: 
                    pass
        if not found:
            desc = metadata_map.get(f"{name}.zip", "Unknown Asset")
            missing_assets.append(f"ROM/BIOS: {name}.zip - {desc}")
            
        current_op += 1
        if progress_cb: progress_cb(current_op, total_ops)

    for chd_rel_path in chd_list:
        source_chd = rom_dir / chd_rel_path
        if source_chd.exists():
            dest_folder = out_rom_dir / Path(chd_rel_path).parent.name
            dest_folder.mkdir(exist_ok=True, parents=True)
            try:
                dest_file = dest_folder / source_chd.name
                if not dest_file.exists():
                    shutil.copy2(source_chd, dest_file)
                copied_count += 1
                copied_assets.append(f"CHD: {chd_rel_path}")
            except OSError as e:
                if e.errno == errno.ENOSPC:
                    if log_cb: log_cb("❌ CRITICAL ERROR: Hard drive is full! Aborting copy.")
                    raise Exception("Hard drive is full!")
                else:
                    if log_cb: log_cb(f"⚠️ OS Error copying {source_chd.name}: {e}")
            except Exception: 
                pass
        else:
            missing_assets.append(f"CHD: {chd_rel_path}")
            
        current_op += 1
        if progress_cb: progress_cb(current_op, total_ops)

    if sample_dir and sample_dir.is_dir():
        for sample_name in sample_list:
            source_sample = sample_dir / f"{sample_name}.zip"
            if source_sample.exists():
                try:
                    dest_file = out_sample_dir / source_sample.name
                    if not dest_file.exists():
                        shutil.copy2(source_sample, dest_file)
                    copied_count += 1
                    copied_assets.append(f"Sample Pack: {source_sample.name}")
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        if log_cb: log_cb("❌ CRITICAL ERROR: Hard drive is full! Aborting copy.")
                        raise Exception("Hard drive is full!")
                    else:
                        if log_cb: log_cb(f"⚠️ OS Error copying {source_sample.name}: {e}")
                except Exception: 
                    pass
            else:
                missing_assets.append(f"Sample Pack: {sample_name}.zip")
                
            current_op += 1
            if progress_cb: progress_cb(current_op, total_ops)
    else:
        for sample_name in sample_list:
            missing_assets.append(f"Sample Pack: {sample_name}.zip (Sample dir not set)")
            current_op += 1
            if progress_cb: progress_cb(current_op, total_ops)

    if log_cb: log_cb(f"✅ Operation complete. {copied_count} files copied.")
    return copied_assets, missing_assets


# -------------------------------
# GUI: SCANNERS 
# -------------------------------

def scan_xml_for_locales(xml_path: Path) -> List[str]:
    REGION_MAP = {
        "world": "World", "usa": "USA", "us": "USA", "u s": "USA", "u.s": "USA", "u.s.": "USA",
        "europe": "Europe", "export": "Export", "japan": "Japan", "korea": "Korea",
        "asia": "Asia", "southeast asia": "Southeast Asia", "hong kong": "Hong Kong",
        "taiwan": "Taiwan", "china": "China", "germany": "Germany", "spain": "Spain",
        "italy": "Italy", "france": "France", "uk": "UK", "u k": "UK", "u.k.": "UK",
        "canada": "Canada", "brazil": "Brazil", "australia": "Australia",
    }
    LANG_WORDS = [
        "English", "Spanish", "German", "Italian", "French", "Chinese", "Korean", "Japanese", 
        "Portuguese", "Dutch", "Russian", "Arabic", "Hebrew", "Swedish", "Norwegian",
        "Danish", "Finnish", "Polish", "Czech", "Hungarian", "Greek", "Turkish",
    ]

    def norm(s: str) -> str:
        s = s.lower().replace(".", " ")
        return re.sub(r"\s+", " ", s).strip()

    single_region_keys = [k for k in REGION_MAP.keys() if " " not in k]
    single_region_re = re.compile(r"\b(" + "|".join(map(re.escape, single_region_keys)) + r")\b", re.IGNORECASE)
    multi_region_keys = [k for k in REGION_MAP.keys() if " " in k]
    lang_re = re.compile(r"\b(" + "|".join(map(re.escape, LANG_WORDS)) + r")\b", re.IGNORECASE)
    ger_eng_re = re.compile(r"\bGER\s*/\s*ENG\b", re.IGNORECASE)
    jpn_re = re.compile(r"\bJPN\b", re.IGNORECASE)
    cn_re = re.compile(r"\bCN\b", re.IGNORECASE)

    locales: Set[str] = set()
    try:
        context = ET.iterparse(xml_path, events=("end",))
        for event, elem in context:
            if elem.tag in ("machine", "game"):
                desc = elem.findtext("description", "")
                if desc and "(" in desc and ")" in desc:
                    for tag_group in re.findall(r"\((.*?)\)", desc):
                        g = norm(tag_group)
                        for mk in multi_region_keys:
                            if mk in g: locales.add(REGION_MAP[mk])
                        for hit in single_region_re.findall(g):
                            locales.add(REGION_MAP[norm(hit)])
                        for hit in lang_re.findall(g):
                            locales.add(hit.capitalize())
                        if ger_eng_re.search(tag_group): locales.update(["German", "English"])
                        if jpn_re.search(tag_group): locales.add("Japan")
                        if cn_re.search(tag_group): locales.add("China")
                elem.clear()
    except Exception:
        return ["Unknown"]

    locales.add("Unknown")
    return sorted(locales)

def scan_catver_for_genres(catver_path: Path) -> List[str]:
    if not catver_path.exists(): return []
    mapping = load_catver(catver_path)
    unique_genres = set()
    for cat_str in mapping.values():
        main_genre = get_main_genre(cat_str)
        if main_genre in EXCLUDED_GENRES: continue
        if main_genre: unique_genres.add(main_genre)
    unique_genres.add("Unknown") 
    return sorted(list(unique_genres))


# -------------------------------
# GUI: SorterApp (TABBED UI)
# -------------------------------

class SorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"MAME Smart ROM Sorter v{CURRENT_VERSION} - TNT Edition")
        
        self.status_q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.current_sorter: Optional[MameSorter] = None 
        self.gui_log_history: List[str] = []
        self.script_dir = SCRIPT_DIR
        self.wizard = None
        
        self._last_scanned_xml = None
        self._last_scanned_catver = None
        
        # Styles
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except:
            pass
        self.style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'))

        # Lifecycle Phase 1: Setup variables
        self.setup_variables()
        
        # Lifecycle Phase 2: Build UI (In background)
        self.build_ui()
        
        # Lifecycle Phase 3: Show Splash
        self.root.state("zoomed")
        self.root.minsize(1024, 768)
        self.show_splash_screen()
        
        self.process_queue()
        
    def setup_variables(self):
        # Paths
        self.roms_var = tk.StringVar(value=DEFAULT_CONFIG["rom_dir"])
        self.samples_var = tk.StringVar(value=DEFAULT_CONFIG["sample_dir"])
        self.xml_var = tk.StringVar(value=DEFAULT_CONFIG["full_xml"])
        self.catver_var = tk.StringVar(value=DEFAULT_CONFIG["catver_path"])
        self.out_var = tk.StringVar(value=DEFAULT_CONFIG["output_path"])

        # Controls
        p_val = DEFAULT_CONFIG["players"]; p_str = "All" if p_val == 99 else str(p_val)
        b_val = DEFAULT_CONFIG["max_buttons"]; b_str = "All" if b_val == 99 else str(b_val)
        self.players_var = tk.StringVar(value=p_str)
        self.buttons_var = tk.StringVar(value=b_str) 
        
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
        self.decade_values = ["Pre-1970s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s", "Unknown"]

        self.control_vars = {}
        default_controls = set(DEFAULT_CONFIG["controls"])
        for val in self.control_values:
            is_checked = val.lower() in default_controls or "all" in default_controls
            self.control_vars[val] = tk.BooleanVar(value=is_checked)

        self.dir_vars = {}
        default_dirs = set(DEFAULT_CONFIG["directions"])
        for val in self.direction_values:
            is_checked = val.lower() in default_dirs or "all" in default_dirs
            self.dir_vars[val] = tk.BooleanVar(value=is_checked)

        self.strict_var = tk.BooleanVar(value=DEFAULT_CONFIG["strict_controls"])

        # Filters
        self.orientation_var = tk.StringVar(value=DEFAULT_CONFIG["orientation"])
        self.status_tier_var = tk.StringVar(value=DEFAULT_CONFIG["emulation_status"])
        self.mature_var = tk.BooleanVar(value=DEFAULT_CONFIG["mature"])
        self.clones_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_clones"])
        self.bootlegs_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_bootlegs"])
        self.prototypes_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_prototypes"])
        self.one_game_one_rom_var = tk.BooleanVar(value=DEFAULT_CONFIG["one_game_one_rom"])
        self.verbose_log_var = tk.BooleanVar(value=DEFAULT_CONFIG["verbose_log"])
        
        # Decades
        self.decade_vars = {}
        saved_decades = set(DEFAULT_CONFIG["decades"])
        for val in self.decade_values:
            self.decade_vars[val] = tk.BooleanVar(value=val in saved_decades)

        # Genres & Locales
        self.genre_vars: Dict[str, tk.BooleanVar] = {}
        
        pref_locales = DEFAULT_CONFIG.get("locale_order")
        if pref_locales:
            seen=set()
            self.pending_pref_locales = [x for x in pref_locales if not (x in seen or seen.add(x))]
        else:
            self.pending_pref_locales = None
            
        self.pending_pref_genres = DEFAULT_CONFIG.get("genres", [])
        
        self.nav_buttons = {}

    def _open_link(self, url: str) -> None:
        webbrowser.open_new(url)

    # -------------------------------
    # LIFECYCLE (Welcome Screen & Update Check) 
    # -------------------------------
    def show_splash_screen(self) -> None:
        splash = tk.Toplevel(self.root)
        splash.title("Welcome")
        splash.transient(self.root)
        splash.grab_set()

        main_frame = ttk.Frame(splash, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(
            main_frame,
            text=f"MAME Smart ROM Sorter v{CURRENT_VERSION} - TNT Edition",
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
            "If dropped directly in your MAME root folder, the app can automatically fetch or generate these files for you!"
        )
        instructions_frame = ttk.LabelFrame(main_frame, text="First-Time Setup", padding=10)
        instructions_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(instructions_frame, text=instructions_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)

        # Support Frame
        support_frame = ttk.LabelFrame(main_frame, text="Support & Community", padding=10)
        support_frame.pack(pady=10, fill=tk.X, expand=True)

        yt_link = ttk.Label(support_frame, text="🔗 Subscribe on YouTube", foreground="blue", cursor="hand2")
        yt_link.pack(anchor=tk.W)
        yt_link.bind("<Button-1>", lambda e: self._open_link(YOUTUBE_URL))

        coffee_link = ttk.Label(support_frame, text="☕ Buy Me a Coffee", foreground="blue", cursor="hand2")
        coffee_link.pack(anchor=tk.W, pady=(5, 0))
        coffee_link.bind("<Button-1>", lambda e: self._open_link(COFFEE_URL))

        def on_agree():
            splash.destroy()
            self.prompt_update_check()

        ttk.Button(main_frame, text="Agree & Continue", command=on_agree).pack(pady=20)

        splash.update_idletasks()
        width = max(splash.winfo_reqwidth(), 700)
        height = min(splash.winfo_reqheight(), 650)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        splash.geometry(f"{width}x{height}+{x}+{y}")
        splash.protocol("WM_DELETE_WINDOW", self.root.destroy)
        
        # EASTER EGG: Play greeting sound
        play_audio_cue("play_game.wav")

    # -------------------------------
    # GITHUB UPDATE CHECKER 
    # -------------------------------
    def prompt_update_check(self):
        """Asks the user if they want to hit the GitHub API on startup."""
        ans = messagebox.askyesno("Check for Updates?", "Do you want to check GitHub for a newer version of this tool before starting?")
        if ans:
            self._perform_update_check(startup=True)
        else:
            self.check_prerequisites(self.script_dir)

    def _perform_update_check(self, startup=False):
        """Hits the GitHub releases API in a non-blocking thread."""
        def check():
            try:
                # Add dummy query param to bypass aggressive caching
                url = f"{GITHUB_API_URL}?t={int(time.time())}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    latest_tag = data.get("tag_name", "")
                    
                    def get_v_tuple(v_str):
                        clean = re.sub(r'[^0-9.]', '', str(v_str))
                        parts = [int(x) for x in clean.split('.') if x]
                        return tuple(parts) if parts else (0,)
                    
                    curr_v = get_v_tuple(CURRENT_VERSION)
                    latest_v = get_v_tuple(latest_tag)
                    
                    if latest_v > curr_v:
                        def prompt_dl():
                            dl = messagebox.askyesno("Update Available!", f"Version {latest_tag} is available!\nYou are currently running v{CURRENT_VERSION}.\n\nWould you like to download the update?")
                            if dl:
                                webbrowser.open(GITHUB_LATEST_URL)
                            if startup:
                                self.check_prerequisites(self.script_dir)
                        self.root.after(0, prompt_dl)
                    else:
                        def prompt_ok():
                            messagebox.showinfo("Up to Date", f"You are running the latest version (v{CURRENT_VERSION}).")
                            if startup:
                                self.check_prerequisites(self.script_dir)
                        self.root.after(0, prompt_ok)
                        
            except Exception as e:
                def prompt_err():
                    if not startup:
                        messagebox.showwarning("Offline / Error", f"Could not check for updates. Are you offline?\n\nDetails: {e}")
                    else:
                        self.log("[NET] ⚠️ Could not reach GitHub for updates. Proceeding offline.")
                        self.check_prerequisites(self.script_dir)
                self.root.after(0, prompt_err)

        threading.Thread(target=check, daemon=True).start()


    def check_prerequisites(self, root_path: Path):
        mame_exe = root_path / "mame.exe"
        xml_path = Path(self.xml_var.get())
        cat_path = Path(self.catver_var.get())
        
        missing_xml = not xml_path.exists()
        missing_ini = not cat_path.exists()

        if mame_exe.exists():
            self.log("[SYS] ✅ MAME.exe found in directory.")
            if missing_xml or missing_ini:
                self.show_setup_wizard(root_path, missing_xml, missing_ini)
            else:
                self.start_xml_scan()
                self.start_catver_scan()
        else:
            self.log("[SYS] ⚠️ MAME.exe not found in current directory. Setup Wizard bypassed.")
            if xml_path.exists(): self.start_xml_scan()
            if cat_path.exists(): self.start_catver_scan()

    def show_setup_wizard(self, root_path: Path, missing_xml: bool, missing_ini: bool):
        self.wizard = tk.Toplevel(self.root)
        self.wizard.title("🛠️ MAME Folder Preparation Required")
        self.wizard.transient(self.root)
        self.wizard.grab_set() 
        
        main_frame = ttk.Frame(self.wizard, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="We noticed a few files are missing to get the most out of your Smart ROM Sorter.", wraplength=450).pack(anchor=tk.W, pady=(0, 15))
        
        self.wiz_dl_ini_var = tk.BooleanVar(value=True)
        self.wiz_gen_xml_var = tk.BooleanVar(value=True)
        
        if missing_ini:
            ttk.Label(main_frame, text="1. Category File (catver.ini is missing)", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
            ttk.Checkbutton(main_frame, text="Download the newest version from GitHub for me. (Recommended)", variable=self.wiz_dl_ini_var).pack(anchor=tk.W, padx=10)
            ttk.Label(main_frame, text="(If unchecked, you must drop your own catver.ini into the MAME root)", font=("Helvetica", 8)).pack(anchor=tk.W, padx=25, pady=(0,10))
        
        if missing_xml:
            ttk.Label(main_frame, text="2. Database File (full.xml is missing)", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
            ttk.Checkbutton(main_frame, text="Generate this now from your local MAME.exe", variable=self.wiz_gen_xml_var).pack(anchor=tk.W, padx=10)
            ttk.Label(main_frame, text="(Note: This can take 3-5 minutes depending on your CPU)", font=("Helvetica", 8)).pack(anchor=tk.W, padx=25, pady=(0,10))
        
        self.wiz_progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.wiz_progress.pack(fill=tk.X, pady=(15, 10))
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.wiz_start_btn = ttk.Button(btn_frame, text="[ START PREPARATION ]", command=lambda: self.execute_wizard_tasks(root_path, missing_ini, missing_xml))
        self.wiz_start_btn.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Skip for Now", command=self.wizard.destroy).pack(side=tk.RIGHT, padx=10)

        self.wizard.update_idletasks()
        width = max(self.wizard.winfo_reqwidth(), 500)
        height = min(self.wizard.winfo_reqheight(), 500)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.wizard.geometry(f"{width}x{height}+{x}+{y}")

    def execute_wizard_tasks(self, root_path: Path, missing_ini: bool, missing_xml: bool):
        self.wiz_start_btn.config(state=tk.DISABLED)
        self.wiz_progress.start(15)
        
        dl_ini = self.wiz_dl_ini_var.get() if missing_ini else False
        gen_xml = self.wiz_gen_xml_var.get() if missing_xml else False
        
        threading.Thread(target=self._wizard_worker, args=(root_path, dl_ini, gen_xml), daemon=True).start()

    def _wizard_worker(self, root_path: Path, dl_ini: bool, gen_xml: bool):
        mame_exe = root_path / "mame.exe"
        xml_path = root_path / "full.xml"
        ini_path = root_path / "catver.ini"
        
        if dl_ini:
            self.status_q.put(("status", "[NET] Downloading latest catver.ini from GitHub..."))
            urls = [
                "https://raw.githubusercontent.com/mamesupport/catver.ini/master/catver.ini",
                "https://raw.githubusercontent.com/mamesupport/catver.ini/main/catver.ini",
                "https://raw.githubusercontent.com/libretro/mame2003-plus-libretro/master/metadata/catver.ini"
            ]
            success = False
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, timeout=10) as response, open(ini_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                    success = True
                    break
                except Exception:
                    continue
                    
            if success:
                self.status_q.put(("status", "[NET] Download complete!"))
                self.status_q.put(("set_catver_var", str(ini_path)))
            else:
                self.status_q.put(("status", f"[NET] ERROR: Could not connect to GitHub mirrors. Please download manually."))
                
        if gen_xml:
            self.status_q.put(("status", "[SYS] Commanding MAME to generate full.xml... (This will take a few minutes)"))
            try:
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                with open(xml_path, "w", encoding="utf-8") as f:
                    subprocess.run([str(mame_exe), "-listxml"], stdout=f, startupinfo=startupinfo, check=True)
                
                self.status_q.put(("status", "[SYS] full.xml generated successfully!"))
                self.status_q.put(("set_xml_var", str(xml_path)))
            except Exception as e:
                self.status_q.put(("status", f"[SYS] ERROR generating full.xml: {e}"))
                
        self.status_q.put(("wizard_done", None))

    def auto_detect_paths(self):
        root_dir = filedialog.askdirectory(title="Select MAME Root Folder")
        if not root_dir: return
        root_path = Path(root_dir)
        
        roms_path = None
        if (root_path / "roms").exists(): roms_path = root_path / "roms"
        elif (root_path / "ROMS").exists(): roms_path = root_path / "ROMS"
        if roms_path: self.roms_var.set(str(roms_path))
        
        samples_path = root_path / "samples"
        if samples_path.exists(): self.samples_var.set(str(samples_path))
            
        xml_path = root_path / "full.xml"
        if not xml_path.exists(): xml_path = root_path / "mame.xml"
        if xml_path.exists(): self.xml_var.set(str(xml_path))
            
        cat_path = root_path / "catver.ini"
        if cat_path.exists(): self.catver_var.set(str(cat_path))
            
        self.check_prerequisites(root_path)


    # -------------------------------
    # GUI LAYOUT 
    # -------------------------------
    def build_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.top_pane = ttk.Frame(self.paned)
        self.bottom_pane = ttk.Frame(self.paned)
        self.paned.add(self.top_pane, weight=3)
        self.paned.add(self.bottom_pane, weight=1)

        # Sidebar
        self.sidebar = tk.Frame(self.top_pane, bg="#2c3e50", width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        try:
            logo_path = self.script_dir / "TNTLogo400by400.png"
            raw_img = tk.PhotoImage(file=str(logo_path))
            
            target_size = 135
            scale_factor = max(1, (raw_img.height() + target_size - 1) // target_size)
            self.logo_img = raw_img.subsample(scale_factor, scale_factor) 
            
            logo_lbl = tk.Label(self.sidebar, image=self.logo_img, bg="#2c3e50")
        except Exception:
            logo_lbl = tk.Label(self.sidebar, text="MAME\nSmart Sorter", font=('Segoe UI', 16, 'bold'), bg="#2c3e50", fg="white")
            
        logo_lbl.pack(pady=(20, 15), padx=10)

        # Content Area
        self.content_area = ttk.Frame(self.top_pane)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self.frames = {}
        tabs = [
            ("Paths & Config", self._build_paths_tab), 
            ("Controls", self._build_controls_tab), 
            ("Filters", self._build_filters_tab), 
            ("Genres", self._build_genres_tab), 
            ("Decades", self._build_decades_tab), 
            ("Locales", self._build_locales_tab), 
            ("Operations", self._build_operations_tab)
        ]

        for text, func in tabs:
            btn = tk.Button(self.sidebar, text=text, font=('Segoe UI', 11, 'bold'), bg="#34495e", fg="white", 
                            relief="flat", anchor="w", padx=20, pady=12, bd=0,
                            activebackground="#2980b9", activeforeground="white",
                            command=lambda t=text: self.show_frame(t))
            btn.pack(fill=tk.X, pady=2)
            self.nav_buttons[text] = btn
            
            frame = ttk.Frame(self.content_area, padding=20)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[text] = frame
            func(frame)

        # Log & Progress (Bottom Pane)
        self.log_text = tk.Text(self.bottom_pane, height=8, bg="#1e1e1e", fg="#00ff00", font=('Consolas', 10), state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5,0))
        
        status_frame = ttk.Frame(self.bottom_pane)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100.0)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.progress_label = ttk.Label(status_frame, text="Ready", width=25, anchor="e")
        self.progress_label.pack(side=tk.RIGHT)

        self.show_frame("Paths & Config")

    def show_frame(self, frame_name):
        for name, btn in self.nav_buttons.items(): 
            btn.config(bg="#34495e")
        self.nav_buttons[frame_name].config(bg="#2980b9")
        self.frames[frame_name].tkraise()

    def _build_paths_tab(self, parent):
        ttk.Label(parent, text="Paths & Configuration", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        ttk.Button(parent, text="✨ Auto-Select MAME Root Folder", command=self.auto_detect_paths).pack(fill=tk.X, pady=(0, 20))
        
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)
        
        fields = [
            ("ROMs path:", self.roms_var, self.browse_roms), 
            ("Samples path:", self.samples_var, self.browse_samples), 
            ("XML path:", self.xml_var, self.browse_xml), 
            ("CatVer path:", self.catver_var, self.browse_catver), 
            ("Output Dir:", self.out_var, self.browse_output)
        ]
        
        for i, (txt, var, cmd) in enumerate(fields):
            ttk.Label(grid, text=txt, font=('Segoe UI', 10)).grid(row=i, column=0, sticky='e', pady=10, padx=5)
            ttk.Entry(grid, textvariable=var, font=('Segoe UI', 10)).grid(row=i, column=1, sticky='we', pady=10, padx=5)
            ttk.Button(grid, text="Browse", command=cmd).grid(row=i, column=2, padx=5)

    def _build_controls_tab(self, parent):
        ttk.Label(parent, text="Controls & Inputs", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        p_frame = ttk.Frame(parent)
        p_frame.pack(fill=tk.X, pady=10)
        ttk.Label(p_frame, text="Players:").pack(side=tk.LEFT)
        ttk.Combobox(p_frame, textvariable=self.players_var, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=(5,20))
        ttk.Label(p_frame, text="Buttons:").pack(side=tk.LEFT)
        ttk.Combobox(p_frame, textvariable=self.buttons_var, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=5)
        
        inp_lf = ttk.LabelFrame(parent, text="Input Types", padding=10)
        inp_lf.pack(fill=tk.X, pady=10)
        for i, k in enumerate(self.control_vars.keys()):
            ttk.Checkbutton(inp_lf, text=k.title(), variable=self.control_vars[k]).grid(row=i//4, column=i%4, sticky='w', padx=15, pady=5)
        
        joy_lf = ttk.LabelFrame(parent, text="Directions", padding=10)
        joy_lf.pack(fill=tk.X, pady=10)
        for i, k in enumerate(self.dir_vars.keys()):
            ttk.Checkbutton(joy_lf, text=k, variable=self.dir_vars[k]).grid(row=i//4, column=i%4, sticky='w', padx=15, pady=5)
            
        ttk.Checkbutton(parent, text="Strict Control Filtering (Must match exactly)", variable=self.strict_var).pack(anchor="w", pady=15)

    def _build_filters_tab(self, parent):
        ttk.Label(parent, text="Game Filters", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=10)
        ttk.Label(f, text="Minimum Emulation Status:").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Combobox(f, textvariable=self.status_tier_var, values=["Working", "Working & Imperfect", "All (Incl. Preliminary)"], state="readonly", width=30).pack(side=tk.LEFT)
        
        ori_f = ttk.Frame(parent)
        ori_f.pack(fill=tk.X, pady=10)
        ttk.Label(ori_f, text="Screen Orientation:").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(ori_f, text="Both", variable=self.orientation_var, value="both").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ori_f, text="Horizontal", variable=self.orientation_var, value="horizontal").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ori_f, text="Vertical", variable=self.orientation_var, value="vertical").pack(side=tk.LEFT, padx=5)

        lf = ttk.LabelFrame(parent, text="Inclusions", padding=10)
        lf.pack(fill=tk.X, pady=15)
        ttk.Checkbutton(lf, text="Include Clones", variable=self.clones_var).grid(row=0, column=0, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Include Bootlegs", variable=self.bootlegs_var).grid(row=0, column=1, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Include Prototypes", variable=self.prototypes_var).grid(row=0, column=2, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Mature Content", variable=self.mature_var).grid(row=1, column=0, sticky='w', padx=20, pady=10)
        
        ttk.Checkbutton(parent, text="Enable 1G1R (One Game, One ROM) - Highly Recommended", variable=self.one_game_one_rom_var).pack(anchor="w", pady=15)
        ttk.Checkbutton(parent, text="Enable Verbose Logging (List all copied files in text log)", variable=self.verbose_log_var).pack(anchor="w", pady=5)

    def _build_genres_tab(self, parent):
        ttk.Label(parent, text="Genres (Auto-Detected from catver.ini)", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        btn_f = ttk.Frame(parent)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="Select All", command=lambda: [v.set(True) for v in self.genre_vars.values()]).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_f, text="Clear All", command=lambda: [v.set(False) for v in self.genre_vars.values()]).pack(side=tk.LEFT)

        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.genre_inner_frame = ttk.Frame(canvas)
        self.genre_inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.genre_inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        
        canvas.pack(side="left", fill="both", expand=True, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

    def _build_decades_tab(self, parent):
        ttk.Label(parent, text="Release Decades", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        btn_f = ttk.Frame(parent)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="Select All", command=lambda: [v.set(True) for v in self.decade_vars.values()]).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_f, text="Clear All", command=lambda: [v.set(False) for v in self.decade_vars.values()]).pack(side=tk.LEFT)

        dec_f = ttk.Frame(parent)
        dec_f.pack(fill=tk.BOTH, expand=True, pady=15)
        for i, dec in enumerate(self.decade_values):
            ttk.Checkbutton(dec_f, text=dec, variable=self.decade_vars[dec]).grid(row=i//4, column=i%4, sticky='w', padx=20, pady=15)

    def _build_locales_tab(self, parent):
        ttk.Label(parent, text="Locale Priority (Used for 1G1R Optimization)", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(parent, text="Move items to the right box and order them from top (Highest Priority) to bottom.", foreground="#7f8c8d").pack(anchor="w", pady=(0, 15))
        
        self.locale_list_avail, self.locale_list_pref = self._create_dual_listbox(parent, "Available Locales")

    def _build_operations_tab(self, parent):
        ttk.Label(parent, text="Operations & Commands", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        top_ops = ttk.Frame(parent)
        top_ops.pack(fill=tk.X, pady=10)

        pr_lf = ttk.LabelFrame(top_ops, text="Presets", padding=15)
        pr_lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        ttk.Button(pr_lf, text="📂 Load Config Preset", command=self.load_preset_gui).pack(fill=tk.X, pady=5)
        ttk.Button(pr_lf, text="💾 Save Config Preset", command=self.save_preset_gui).pack(fill=tk.X, pady=5)
        
        tl_lf = ttk.LabelFrame(top_ops, text="Manual Updates", padding=15)
        tl_lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        ttk.Button(tl_lf, text="🔄 Check for App Updates", command=lambda: self._perform_update_check(startup=False)).pack(fill=tk.X, pady=5)
        ttk.Button(tl_lf, text="⚙️ Generate full.xml", command=self.manual_generate_xml).pack(fill=tk.X, pady=5)
        ttk.Button(tl_lf, text="🌐 Download catver.ini", command=self.manual_download_catver).pack(fill=tk.X, pady=5)
        
        run_f = tk.Frame(parent, bg="#d35400", pady=3, padx=3)
        run_f.pack(fill=tk.X, pady=20)
        self.run_button = tk.Button(run_f, text="🚀 RUN MAME SMART SORTER", font=('Segoe UI', 16, 'bold'), bg="#e67e22", fg="white", bd=0, pady=10, command=self.start_sort)
        self.run_button.pack(fill=tk.BOTH, expand=True)

        eco_lf = ttk.LabelFrame(parent, text="Guides-MAME-Shoutouts-Resources", padding=15)
        eco_lf.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # Row 0: TNT Main Hub & Project Links
        ttk.Button(eco_lf, text="🌐 TNT Official Website", command=lambda: webbrowser.open(TNT_WEBSITE_URL)).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🎥 TNT YouTube Channel", command=lambda: webbrowser.open(YOUTUBE_URL)).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="💻 GitHub Repo", command=lambda: webbrowser.open(GITHUB_URL)).grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="☕ Buy Me a Coffee", command=lambda: webbrowser.open(COFFEE_URL)).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        # Row 1: TNT Specific Video Guides
        ttk.Button(eco_lf, text="▶️ Smart ROM Sorter Guide", command=lambda: webbrowser.open(TNT_USER_GUIDE_URL)).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="▶️ ROMLister Guide", command=lambda: webbrowser.open(TNT_FILTER_GUIDE_URL)).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="▶️ Arcade Database Hack!", command=lambda: webbrowser.open(TNT_ROM_EASY_URL)).grid(row=1, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🛠️ ClrMamePro Guide", command=lambda: webbrowser.open(CLRMAME_VID_URL)).grid(row=1, column=3, sticky="ew", padx=5, pady=5)

        # Row 2: Essential MAME Links (Community)
        ttk.Button(eco_lf, text="👾 MAMEdev Official", command=lambda: webbrowser.open(MAMEDEV_URL)).grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="📖 MAME Wiki", command=lambda: webbrowser.open(MAMEWIKI_URL)).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🗄️ ArcadeItalia (ADB)", command=lambda: webbrowser.open(ADB_URL)).grid(row=2, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🖼️ ProgettoSnaps", command=lambda: webbrowser.open(PROGETTO_URL)).grid(row=2, column=3, sticky="ew", padx=5, pady=5)

        # Row 3: Arcade Community Shoutouts
        ttk.Button(eco_lf, text="🔥 Team Encoder", command=lambda: webbrowser.open("https://www.team-encoder.com/")).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🚀 Rogue Synapse", command=lambda: webbrowser.open("http://www.roguesynapse.com/games/last_starfighter.php")).grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="👁️ Sinnesloschen (Polybius)", command=lambda: webbrowser.open("http://www.sinnesloschen.com/")).grid(row=3, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🕹️ Houston Arcade Expo", command=lambda: webbrowser.open("https://www.houstonarcadeexpo.com/")).grid(row=3, column=3, sticky="ew", padx=5, pady=5)
        
        for i in range(4):
            eco_lf.columnconfigure(i, weight=1)

    def _create_dual_listbox(self, parent, title):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=2, padx=2)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Label(frame, text=f"{title}:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text="Preferred:").grid(row=0, column=2, sticky=tk.W)

        list_avail = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=15)
        list_avail.grid(row=1, column=0, sticky=tk.NSEW, rowspan=2)

        list_pref = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=15)
        list_pref.grid(row=1, column=2, sticky=tk.NSEW, rowspan=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=1, rowspan=2, padx=10, sticky=tk.NS)

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

        ttk.Button(btn_frame, text=">", width=3, command=lambda: move_items(list_avail, list_pref)).pack(pady=5)
        ttk.Button(btn_frame, text="<", width=3, command=lambda: move_items(list_pref, list_avail)).pack(pady=5)
        ttk.Button(btn_frame, text="▲", width=3, command=lambda: move_up(list_pref)).pack(pady=5)
        ttk.Button(btn_frame, text="▼", width=3, command=lambda: move_down(list_pref)).pack(pady=5)

        return list_avail, list_pref

    # --- MANUAL WIZARD TRIGGERS ---
    def manual_generate_xml(self):
        base_dir = Path(self.xml_var.get()).parent
        mame_exe = base_dir / "mame.exe"
        if not mame_exe.exists():
            messagebox.showerror("Error", f"mame.exe not found in:\n{base_dir}\n\nPlease set correct Paths.")
            return
        threading.Thread(target=self._wizard_worker, args=(base_dir, False, True), daemon=True).start()

    def manual_download_catver(self):
        base_dir = Path(self.catver_var.get()).parent
        threading.Thread(target=self._wizard_worker, args=(base_dir, True, False), daemon=True).start()


    # --- FILE BROWSERS ---
    def browse_roms(self):
        d = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME ROMs Folder")
        if d: self.roms_var.set(d)

    def browse_samples(self):
        d = filedialog.askdirectory(initialdir=self.script_dir, title="Select MAME Samples Folder")
        if d: self.samples_var.set(d)

    def browse_xml(self):
        f = filedialog.askopenfilename(initialdir=self.script_dir, title="Select full.xml", filetypes=(("XML files", "*.xml"), ("All files", "*.*")))
        if f:
            self.xml_var.set(f)
            self.start_xml_scan()

    def browse_catver(self):
        f = filedialog.askopenfilename(initialdir=self.script_dir, title="Select catver.ini", filetypes=(("INI files", "*.ini"), ("All files", "*.*")))
        if f:
            self.catver_var.set(f)
            self.start_catver_scan()

    def browse_output(self):
        d = filedialog.askdirectory(initialdir=self.script_dir, title="Select Output Base Folder")
        if d: self.out_var.set(d)

    def log(self, msg: str):
        self.gui_log_history.append(msg)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # --- SCANNERS & QUEUE LOOP ---
    def start_xml_scan(self):
        xml_path_str = self.xml_var.get().strip()
        if not xml_path_str: return
        if getattr(self, '_last_scanned_xml', None) == xml_path_str:
            self.status_q.put(("apply_pending_locales", None))
            return
        xml_path = Path(xml_path_str)
        if not xml_path.exists():
            self.log(f"⚠️ full.xml not found at: {xml_path}")
            return
        self._last_scanned_xml = xml_path_str
        self.log(f"🔄 Scanning {xml_path.name} for locales...")
        def worker():
            locales = scan_xml_for_locales(xml_path)
            self.status_q.put(("locales_done", locales))
        threading.Thread(target=worker, daemon=True).start()

    def start_catver_scan(self):
        catver_path_str = self.catver_var.get().strip()
        if not catver_path_str: return
        if getattr(self, '_last_scanned_catver', None) == catver_path_str:
            self.status_q.put(("apply_pending_genres", None))
            return
        catver_path = Path(catver_path_str)
        if not catver_path.exists(): return
        self._last_scanned_catver = catver_path_str
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
        selected_decades = [val for val, var in self.decade_vars.items() if var.get()] 
        
        locale_order = list(self.locale_list_pref.get(0, tk.END))
        _REGION_OPTS = {"World","USA","Japan","Europe","Export","Korea","Asia","Southeast Asia","Hong Kong","Taiwan","China","Germany","Spain","Italy","France","UK","Canada","Brazil","Australia","Unknown"}
        _LANG_OPTS = {"English","Spanish","German","Italian","French","Chinese","Korean","Japanese","Portuguese","Dutch","Russian","Arabic","Hebrew","Swedish","Norwegian","Danish","Finnish","Polish","Czech","Hungarian","Greek","Turkish","Unknown"}
        r_order = [x for x in locale_order if x in _REGION_OPTS]
        l_order = [x for x in locale_order if x in _LANG_OPTS]
        cfg = {
            "schema_version": 1.0,
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
            "emulation_status": self.status_tier_var.get(),
            "mature": self.mature_var.get(),
            "include_clones": self.clones_var.get(),
            "include_bootlegs": self.bootlegs_var.get(),
            "include_prototypes": self.prototypes_var.get(),
            "one_game_one_rom": self.one_game_one_rom_var.get(),
            "locale_order": locale_order,
            "region_order": r_order,
            "language_order": l_order,
            "catver_path": self.catver_var.get().strip(),
            "genres": selected_genres,
            "decades": selected_decades, 
            "verbose_log": self.verbose_log_var.get(),
        }
        if hasattr(self, 'loaded_preset_path'): cfg["preset_path"] = self.loaded_preset_path
        cfg["gui_log_history"] = list(self.gui_log_history)
        return cfg

    def save_preset_gui(self):
        cfg = self.build_config()
        cfg.pop("gui_log_history", None); cfg.pop("preset_path", None)
        f = filedialog.asksaveasfilename(
            initialfile=f"preset_v{CURRENT_VERSION}.json", 
            defaultextension=".json", 
            filetypes=[("JSON files", "*.json")], 
            title="Save preset as…"
        )
        if f:
            try:
                with open(f, "w", encoding="utf-8") as file: json.dump(cfg, file, indent=2)
                self.loaded_preset_path = f
                self.log(f"💾 Preset saved: {Path(f).name}")
            except Exception as e: messagebox.showerror("Error", f"Failed to save preset:\n{e}")

    def load_preset_gui(self):
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load preset…")
        if f:
            try:
                self.loaded_preset_path = f
                with open(f, "r", encoding="utf-8") as file: cfg = json.load(file)
                schema_ver = cfg.get("schema_version", "Legacy")
                self.log(f"⚙️ Detected Preset Schema: v{schema_ver}")
                loaded_rom_dir = cfg.get("rom_dir", "")
                if loaded_rom_dir:
                    p_rom = Path(loaded_rom_dir)
                    if p_rom.is_dir() and p_rom.name.lower() != "roms":
                        if (p_rom / "roms").exists(): loaded_rom_dir = str(p_rom / "roms")
                        elif (p_rom / "ROMS").exists(): loaded_rom_dir = str(p_rom / "ROMS")
                self.roms_var.set(loaded_rom_dir or str(self.script_dir / "roms"))
                self.samples_var.set(cfg.get("sample_dir") or str(self.script_dir / "samples"))
                self.xml_var.set(cfg.get("full_xml") or str(self.script_dir / "full.xml"))
                self.out_var.set(cfg.get("output_path") or str(self.script_dir / "filtered_mame_set"))
                self.catver_var.set(cfg.get("catver_path") or str(self.script_dir / "catver.ini"))
                p_val = cfg.get("players", 2); self.players_var.set("All" if p_val == 99 else str(p_val))
                b_val = cfg.get("max_buttons", 8); self.buttons_var.set("All" if b_val == 99 else str(b_val))
                self.orientation_var.set(cfg.get("orientation", "both"))
                self.status_tier_var.set(cfg.get("emulation_status", "Working"))
                self.strict_var.set(cfg.get("strict_controls", False))
                self.mature_var.set(cfg.get("mature", False))
                self.clones_var.set(cfg.get("include_clones", False))
                self.bootlegs_var.set(cfg.get("include_bootlegs", False))
                self.prototypes_var.set(cfg.get("include_prototypes", False))
                self.one_game_one_rom_var.set(cfg.get("one_game_one_rom", False))
                self.verbose_log_var.set(cfg.get("verbose_log", True))
                saved_controls = cfg.get("controls", [])
                for val, var in self.control_vars.items(): var.set(val in saved_controls if saved_controls else val.lower() == "all")
                saved_dirs = cfg.get("directions", [])
                for val, var in self.dir_vars.items(): var.set(val in saved_dirs if saved_dirs else val.lower() == "all")
                
                saved_decades = cfg.get("decades", self.decade_values)
                for val, var in self.decade_vars.items(): var.set(val in saved_decades)

                pref_locales = cfg.get("locale_order")
                if not pref_locales:
                    pref_locales = list(cfg.get("region_order", [])) + list(cfg.get("language_order", []))
                    seen=set(); pref_locales=[x for x in pref_locales if not (x in seen or seen.add(x))]
                self.pending_pref_locales = pref_locales; self.pending_pref_genres = cfg.get("genres", [])
                self.log(f"📂 Preset loaded: {Path(f).name} (Verifying lists...)")
                self.start_xml_scan(); self.start_catver_scan()
            except Exception as e: messagebox.showerror("Error", f"Failed to load preset:\n{e}")

    def show_set_warning_popup(self, set_type: str):
        popup = tk.Toplevel(self.root)
        popup.title("⚠️ Warning: Incompatible ROM Set")
        popup.geometry("450x300")
        popup.transient(self.root)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"We detected a {set_type} set.", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        warn_msg = (
            "This tool physically copies zip files and explicitly requires a Non-Merged set. "
            "Proceeding with your current setup may result in broken or unplayable games due to missing parent files."
        )
        ttk.Label(frame, text=warn_msg, wraplength=400, justify=tk.LEFT).pack(pady=(0, 15))

        ttk.Label(frame, text="Action Required:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="Please use ClrMamePro to rebuild your collection into a Non-Merged set.", wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 10))

        link1 = ttk.Label(frame, text="🔗 Download ClrMamePro", foreground="blue", cursor="hand2")
        link1.pack(anchor=tk.W)
        link1.bind("<Button-1>", lambda e: self._open_link("https://mamedev.emulab.it/clrmamepro/"))

        link2 = ttk.Label(frame, text="🔗 Watch: How to convert your ROMs", foreground="blue", cursor="hand2")
        link2.pack(anchor=tk.W, pady=(5, 15))
        link2.bind("<Button-1>", lambda e: self._open_link("https://youtu.be/miXMtHDUeb0"))

        def on_proceed():
            if self.current_sorter: 
                self.current_sorter.user_decision = "proceed"
                self.current_sorter.decision_event.set()
            popup.destroy()

        def on_quit():
            if self.current_sorter: 
                self.current_sorter.user_decision = "quit"
                self.current_sorter.decision_event.set()
            popup.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        ttk.Button(btn_frame, text="Ignore & Proceed", command=on_proceed).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel Sort", command=on_quit).pack(side=tk.RIGHT, padx=5)

        popup.protocol("WM_DELETE_WINDOW", on_quit)

    def start_sort(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log("⚠️ A sort is already in progress.")
            return
            
        self.log(f"🚀 Starting MameSorter Engine (v{CURRENT_VERSION} Logic)...")
        self.run_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label.config(text="Scanning...")
        
        cfg = self.build_config()
        
        def worker():
            try:
                self.current_sorter = MameSorter(cfg, self.status_q)
                self.current_sorter.run()
                self.current_sorter = None
                self.status_q.put(("done", None))
            except Exception as e:
                self.status_q.put(("error", f"❌ Error: {e}"))
                import traceback; traceback.print_exc()
                
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def process_queue(self):
        try:
            while True:
                kind, data = self.status_q.get_nowait()
                
                if kind in ("status", "error"): 
                    self.log(data)
                
                # Progress Bar Updates
                if kind == "progress":
                    curr, tot = data
                    if tot > 0:
                        pct = (curr / tot) * 100.0
                        self.progress_var.set(pct)
                        self.progress_label.config(text=f"Copying: {curr} / {tot}")
                        
                # End of Sort Handling
                if kind in ("done", "error"):
                    self.run_button.config(state=tk.NORMAL)
                    if kind == "done":
                        self.progress_label.config(text="Complete!")
                        self.progress_var.set(100.0)
                        # EASTER EGG: Play Game Over sound
                        play_audio_cue("game_over.wav")
                    else:
                        self.progress_label.config(text="Error / Aborted")
                
                # Setup Wizard Handling
                if kind == "set_catver_var":
                    self.catver_var.set(data)
                if kind == "set_xml_var":
                    self.xml_var.set(data)
                if kind == "wizard_done":
                    if self.wizard:
                        self.wizard.destroy()
                        self.wizard = None
                    self.start_xml_scan()
                    self.start_catver_scan()
                    self.progress_label.config(text="Ready")
                    self.progress_var.set(0)
                
                # Background Scan Handling
                if kind == "show_set_warning":
                    self.show_set_warning_popup(data)
                if kind == "locales_done":
                    locales = data; self.locale_list_avail.delete(0, tk.END); self.locale_list_pref.delete(0, tk.END)
                    for x in locales: self.locale_list_avail.insert(tk.END, x)
                    self.log(f"✅ XML Scan complete. Found {len(locales)} locale options.")
                    self.status_q.put(("apply_pending_locales", None))
                if kind == "apply_pending_locales":
                    if getattr(self, "pending_pref_locales", None) is not None:
                        avail = list(self.locale_list_avail.get(0, tk.END))
                        for item in self.pending_pref_locales:
                            if item in avail:
                                idx = avail.index(item); self.locale_list_pref.insert(tk.END, self.locale_list_avail.get(idx))
                                self.locale_list_avail.delete(idx); avail.pop(idx)
                        self.pending_pref_locales = None
                if kind == "genres_done":
                    genres = data; [w.destroy() for w in self.genre_inner_frame.winfo_children()]; self.genre_vars.clear()
                    genres = sorted(genres); row = 0; col = 0; max_cols = 3
                    for g in genres:
                        var = tk.BooleanVar(value=True); self.genre_vars[g] = var
                        chk = ttk.Checkbutton(self.genre_inner_frame, text=GENRE_DISPLAY_MAP.get(g, g), variable=var)
                        chk.grid(row=row, column=col, sticky='w', padx=5, pady=2)
                        col += 1
                        if col >= max_cols: col = 0; row += 1
                    self.log(f"✅ CatVer Scan complete. Found {len(genres)} unique genres.")
                    self.status_q.put(("apply_pending_genres", None))
                if kind == "apply_pending_genres":
                    if getattr(self, "pending_pref_genres", None) is not None:
                        want_all = len(self.pending_pref_genres) == 0
                        for g, var in self.genre_vars.items():
                            if want_all or g in self.pending_pref_genres:
                                var.set(True)
                            else:
                                var.set(False)
                        self.pending_pref_genres = None
                        
                self.status_q.task_done()
        except queue.Empty: pass
        self.root.after(100, self.process_queue) 


if __name__ == "__main__":
    if GUI_AVAILABLE:
        root = tk.Tk()
        try: root.tk.call('tk', 'windowingsystem')
        except tk.TclError: pass
        SorterApp(root)
        root.mainloop()
    else: print("Tkinter not found. Install tkinter to run GUI.")