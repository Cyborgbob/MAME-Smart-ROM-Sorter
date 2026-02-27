#!/usr/bin/env python3

"""
MAME Smart ROM Sorter — GUI (Tkinter) + CLI v4.74 (Community & Couch Preset Update)

----------------------------------------------------------------
Authors: Shawn Flanagan & Bob Cogito

Base: v4.73
v4.74 Changes:
    - UI: Added mouse wheel scrolling to the Genres tab.
    - CONFIG: Baked in the 'Couch Co-op' preset as the default state for modern controllers.
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
import io 
import errno  
import urllib.request
import subprocess
import xml.etree.ElementTree as ET
import platform
from dataclasses import dataclass, field
from collections import Counter, defaultdict, OrderedDict

from pathlib import Path
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

def get_user_dir() -> Path:
    """Gets the folder where the .exe is running from (for user ROMs/XMLs)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent

def get_asset_path(filename: str) -> Path:
    """Gets the path for bundled assets (logo, sounds) hidden inside the .exe."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename
    else:
        return Path(__file__).resolve().parent / filename

SCRIPT_DIR = get_user_dir()
CURRENT_VERSION = "4.74"

# -------------------------------
# ARCADE PURITY FILTER CONSTANTS
# -------------------------------
JUNK_GENRE_KEYWORDS = [
    "system / device", 
    "slot machine", 
    "pinball", 
    "electromechanical", 
    "game console", 
    "handheld", 
    "computer", 
    "calculator", 
    "tabletop", 
    "casino",
    "fruit machine",
    "coin pusher",
    "utilities",
    "microcomputer"
]

def play_audio_cue(filename: str):
    """Plays a WAV file asynchronously if on Windows."""
    try:
        if winsound and platform.system() == "Windows":
            snd_path = str(get_asset_path(filename))
            if os.path.exists(snd_path):
                winsound.PlaySound(snd_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass  


# -------------------------------
# CONSTANTS & DEFAULTS
# -------------------------------

_REGION_OPTS = [
    "USA", "Canada", "Australia", "World", "UK", "Europe", "Export", "Japan", 
    "Asia", "Southeast Asia", "Hong Kong", "Taiwan", "China", "Korea", "Germany", 
    "Spain", "Italy", "France", "Brazil", "Unknown"
]

_LANG_OPTS = [
    "English", "Spanish", "German", "French", "Italian", "Chinese", "Korean", 
    "Japanese", "Portuguese", "Dutch", "Russian", "Arabic", "Hebrew", "Swedish", 
    "Norwegian", "Danish", "Finnish", "Polish", "Czech", "Hungarian", "Greek", 
    "Turkish", "Unknown"
]

DEFAULT_CONFIG = {
  "schema_version": 1.5,
  "rom_dir": str(SCRIPT_DIR / "roms"),
  "sample_dir": str(SCRIPT_DIR / "samples"),
  "full_xml": str(SCRIPT_DIR / "full.xml"),
  "output_path": str(SCRIPT_DIR / "filtered_mame_set"),
  "catver_path": str(SCRIPT_DIR / "folders" / "catver.ini"),
  "languages_path": str(SCRIPT_DIR / "folders" / "languages.ini"),
  "mature_path": str(SCRIPT_DIR / "folders" / "mature.ini"),
  "players_path": str(SCRIPT_DIR / "folders" / "players.ini"),
  "bootlegs_path": str(SCRIPT_DIR / "folders" / "Bootlegs.ini"),
  "prototype_path": str(SCRIPT_DIR / "folders" / "Prototype.ini"),
  "bestgames_path": str(SCRIPT_DIR / "folders" / "bestgames.ini"),
  "series_path": str(SCRIPT_DIR / "folders" / "series.ini"),
  "monochrome_path": str(SCRIPT_DIR / "folders" / "monochrome.ini"),
  "controls_path": str(SCRIPT_DIR / "folders" / "controls.ini"),
  "mess_path": str(SCRIPT_DIR / "folders" / "mess.ini"),
  "working_arcade_path": str(SCRIPT_DIR / "folders" / "working_arcade.ini"),
  "not_working_arcade_path": str(SCRIPT_DIR / "folders" / "not_working_arcade.ini"),
  "players": 4,
  "max_buttons": 8,
  "controls": ["joystick", "twin stick", "270 wheel", "360 wheel", "pedal", "stick (analog)", "buttons only"],
  "directions": ["4-way", "8-way", "2-way horizontal", "2-way vertical", "analog"],
  "strict_controls": True,
  "require_coop": False,
  "orientation": "both",
  "display_type": "All",
  "emulation_status": "Working & Imperfect",
  "min_score": 0,
  "consolidate_series": False,
  "mature": False,
  "include_clones": True,
  "include_bootlegs": True,
  "include_prototypes": True,
  "one_game_one_rom": True,
  "region_order": _REGION_OPTS.copy(),
  "language_order": _LANG_OPTS.copy(),
  "genres": [
    "Fighter / 2.5D", "Fighter / 2D", "Fighter / 3D", "Fighter / Compilation", "Fighter / Field", 
    "Fighter / Misc.", "Fighter / Versus", "Fighter / Versus Co-op", "Fighter / Vertical",
    "Shooter / 1st Person", "Shooter / 3rd Person", "Shooter / Command", "Shooter / Driving", 
    "Shooter / Driving (chase view)", "Shooter / Driving 1st Person", "Shooter / Driving Diagonal", 
    "Shooter / Driving Horizontal", "Shooter / Driving Vertical", "Shooter / Field", "Shooter / Firelock", 
    "Shooter / Flying", "Shooter / Flying (chase view)", "Shooter / Flying 1st Person", 
    "Shooter / Flying Diagonal", "Shooter / Flying Horizontal", "Shooter / Flying Vertical", 
    "Shooter / Gallery", "Shooter / Gun", "Shooter / Misc.", "Shooter / Misc. Horizontal", 
    "Shooter / Misc. Vertical", "Shooter / Motorbike", "Shooter / Outline", "Shooter / Tank Driving", 
    "Shooter / Underwater", "Shooter / Versus", "Shooter / Walking", "Platform / Fighter", 
    "Platform / Fighter Scrolling", "Platform / Maze", "Platform / Run Jump", 
    "Platform / Run, Jump & Scrolling", "Platform / Shooter", "Platform / Shooter Scrolling",
    "Maze / Ball Guide", "Maze / Blocks", "Maze / Change Surface", "Maze / Collect", 
    "Maze / Collect & Put", "Maze / Cross", "Maze / Defeat Enemies", "Maze / Digging", 
    "Maze / Driving", "Maze / Escape", "Maze / Fighter", "Maze / Integrate", "Maze / Ladders", 
    "Maze / Misc.", "Maze / Move and Sort", "Maze / Outline", "Maze / Paint", "Maze / Shooter Large", 
    "Maze / Shooter Small", "Maze / Surround", "Puzzle / Cards", "Puzzle / Drop", "Puzzle / Match", 
    "Puzzle / Maze", "Puzzle / Misc.", "Puzzle / Multi-Games", "Puzzle / Outline", 
    "Puzzle / Reconstruction", "Puzzle / Sliding", "Puzzle / Solved Game", "Puzzle / Toss",
    "Driving / 1st Person", "Driving / Boat", "Driving / Demolition Derby", "Driving / FireTruck Guide", 
    "Driving / Guide and Collect", "Driving / Landing", "Driving / Misc.", "Driving / Motorbike", 
    "Driving / Motorbike (Motocross)", "Driving / Plane", "Driving / Race", "Driving / Race (chase view)", 
    "Driving / Race (chase view) Bike", "Driving / Race 1st Person", "Driving / Race Bike", 
    "Driving / Race Track", "Sports / Arm Wrestling", "Sports / Baseball", "Sports / Basketball", 
    "Sports / Bowling", "Sports / Boxing", "Sports / Bull Fighting", "Sports / Cards", "Sports / Darts", 
    "Sports / Dodgeball", "Sports / Fishing", "Sports / Football", "Sports / Golf", "Sports / Handball", 
    "Sports / Hang Gliding", "Sports / Hockey", "Sports / Horse Racing", "Sports / Horseshoes", 
    "Sports / Misc.", "Sports / Multiplay", "Sports / Ping Pong", "Sports / Pool", "Sports / Rugby Football", 
    "Sports / Shuffleboard", "Sports / Skateboarding", "Sports / Skiing", "Sports / SkyDiving", 
    "Sports / Soccer", "Sports / Sumo", "Sports / Swimming", "Sports / Tennis", "Sports / Track & Field", 
    "Sports / Volley - Soccer", "Sports / Volleyball", "Sports / Wrestling", "Card Games / Solitaire", 
    "MultiGame / Compilation", "MultiGame / Mini-Games", "Multiplay / Mini-Games", "Multiplay / Misc."
  ], 
  "decades": ["Pre-1970s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s", "Unknown"],
  "verbose_log": True
}


# -------------------------------
# LINKS & MAPS
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

# v4.73 New Community Links
ARCADE_CONTROLS_URL = "https://controls.arcadecontrols.com/"
NPLAYERS_URL = "https://nplayers.arcadebelgium.be/"
ANTO_PISA_URL = "https://github.com/AntoPISA/MAME_SupportFiles"
POLYBIUS_ARCHIVE_URL = "https://www.coinop.org/game/103223/polybius"

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
    "joystick": {"joy", "joystick", "stick"},
    "twin stick": {"dual", "twin"},
    "trackball": {"trackball"},
    "spinner": {"spinner"},
    "dial": {"dial"},
    "paddle": {"paddle"},
    "270 wheel": {"270 steering", "270 wheel", "270 degree"},
    "360 wheel": {"360 steering", "360 wheel", "360 degree"},
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
# Data Structures (The God Object)
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
    chds: List[str] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)
    device_refs: Set[str] = field(default_factory=set)
    rom_count: int = 0  
    
    # --- GOD MODE METADATA ---
    category: str = "Unknown"
    subcategory: str = ""
    is_mature: bool = False
    is_bootleg: bool = False
    is_prototype: bool = False
    regions: Set[str] = field(default_factory=set)
    languages: Set[str] = field(default_factory=set)
    series: str = ""
    bestgames_score: int = 0
    simultaneous_players: int = 0
    display_type: str = "Color"
    
    
# -------------------------------
# INI PARSING ENGINE 
# -------------------------------

@dataclass(frozen=True)
class IniData:
    sections: OrderedDict[str, list[str]]

def load_ini_sections(path: Path, log_cb=None) -> IniData:
    sections = OrderedDict()
    current = None
    
    if not path or not path.exists():
        if log_cb: log_cb(f"⚠️ Missing INI: {path.name}")
        return IniData(sections=sections)

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith((";", "#")):
                    continue

                if line.startswith("[") and line.endswith("]"):
                    current = line[1:-1].strip()
                    sections.setdefault(current, [])
                    continue

                if current is None:
                    continue

                sections[current].append(line)
    except Exception as e:
        if log_cb: log_cb(f"⚠️ Failed to parse {path.name}: {e}")
        
    return IniData(sections=sections)

def parse_folder_list(ini: IniData) -> Set[str]:
    out = set()
    for sec, lines in ini.sections.items():
        if sec.upper() == "FOLDER_SETTINGS":
            continue
        for ln in lines:
            if "=" not in ln:
                out.add(ln.strip())
    return out

def parse_mapping_section(ini: IniData, section_name: str) -> Dict[str, str]:
    lines = ini.sections.get(section_name, [])
    out = {}
    for ln in lines:
        if "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip()
    return out

def parse_categorical_ini(ini: IniData) -> Dict[str, str]:
    mapping = {}
    for section, roms in ini.sections.items():
        if section in ["FOLDER_SETTINGS", "ROOT_FOLDER"]: continue
        category_name = section.strip()
        for rom in roms:
            clean_rom = rom.split("=")[0].strip()
            if clean_rom:
                mapping[clean_rom] = category_name
    return mapping

_bestgames_re = re.compile(r"^\s*(\d+)\s*to\s*(\d+)\s*\(")

def parse_bestgames(ini: IniData) -> Dict[str, int]:
    out = {}
    for sec, lines in ini.sections.items():
        if sec.upper() in ("FOLDER_SETTINGS", "ROOT_FOLDER"):
            continue
        m = _bestgames_re.match(sec)
        if not m:
            continue
        hi = int(m.group(2))
        for rom in lines:
            if "=" in rom: continue
            out[rom.strip()] = hi
    return out

def parse_players(ini: IniData) -> Tuple[Dict[str, int], Set[str]]:
    player_counts = {}
    alt_games = set()
    for sec, lines in ini.sections.items():
        if sec.upper() in ("FOLDER_SETTINGS", "ROOT_FOLDER"): continue
        match = re.match(r"^(\d+)", sec)
        p_count = int(match.group(1)) if match else 0
        is_alt = "alt" in sec.lower()
        
        for rom in lines:
            if "=" in rom: continue
            r = rom.strip()
            if p_count > player_counts.get(r, 0):
                player_counts[r] = p_count
            if is_alt:
                alt_games.add(r)
    return player_counts, alt_games

def parse_series(ini: IniData) -> Dict[str, str]:
    out = {}
    for sec, lines in ini.sections.items():
        if sec.upper() in ("FOLDER_SETTINGS", "ROOT_FOLDER"): continue
        for rom in lines:
            if "=" in rom: continue
            out[rom.strip()] = sec.strip()
    return out

def parse_languages(ini: IniData) -> Dict[str, Set[str]]:
    out = defaultdict(set)
    for sec, lines in ini.sections.items():
        if sec.upper() in ("FOLDER_SETTINGS", "ROOT_FOLDER"): continue
        lang = sec.strip()
        for rom in lines:
            if "=" in rom: continue
            out[rom.strip()].add(lang)
    return dict(out)

def parse_controls_data(ini: IniData) -> Dict[str, Tuple[Set[str], Set[str], Optional[int], Optional[bool]]]:
    out = {}
    for rom_name, lines in ini.sections.items():
        if rom_name.upper() in ("FOLDER_SETTINGS", "ROOT_FOLDER"): continue
        
        controls = set()
        directions = set()
        num_buttons = None
        alternating = None
        
        for line in lines:
            line_lower = line.lower()
            if line_lower.startswith("p1numbuttons="):
                try: num_buttons = int(line.split("=")[1].strip())
                except: pass
                continue
            if line_lower.startswith("alternating="):
                try: alternating = bool(int(line.split("=")[1].strip()))
                except: pass
                continue
                
            if line.startswith("P1Controls=") or line.startswith("Controls="):
                val = line.split("=", 1)[1].strip().lower()
                parts = val.split("|")
                for part in parts:
                    subparts = part.split("+")
                    for sub in subparts:
                        sub = sub.strip()
                        if not sub: continue
                        for main_ctrl, keywords in CONTROL_KEYWORDS.items():
                            if any(kw in sub for kw in keywords):
                                controls.add(main_ctrl)
                        for main_dir, keywords in DIRECTION_MAP.items():
                            if sub == "2":
                                if "2" in keywords: directions.add(main_dir)
                            elif any(kw in sub for kw in keywords):
                                directions.add(main_dir)
                                
        if controls or directions or (num_buttons is not None) or (alternating is not None):
            out[rom_name] = (controls, directions, num_buttons, alternating)
            
    return out


# -------------------------------
# LOGIC ENGINE
# -------------------------------

class MameSorter:
    def __init__(self, config: Dict[str, Any], status_q: Optional[queue.Queue] = None):
        self.config = config
        self.status_q = status_q
        self.script_dir = SCRIPT_DIR
        
        self.catver_map = {}
        self.languages_map = {}
        self.mature_set = set()
        self.players_map = {}
        self.alt_players_set = set()
        self.bootlegs_set = set()
        self.prototype_set = set()
        self.bestgames_map = {}
        self.series_map = {}
        self.monochrome_map = {}
        self.controls_map = {}
        
        # --- VIP Bouncers ---
        self.mess_set = set() 
        self.working_arcade_set = set()
        self.not_working_arcade_set = set()
        
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
        def _get_path(key, default_name):
            val = self.config.get(key)
            if val and Path(val).exists(): return Path(val)
            p = self.script_dir / "folders" / default_name
            if p.exists(): return p
            p_root = self.script_dir / default_name
            if p_root.exists(): return p_root
            return Path(val) if val else p 

        self._log(f"📚 Loading God Mode Metadata Databases...")
        
        catver_ini = load_ini_sections(_get_path("catver_path", "catver.ini"), log_cb=self._log)
        lang_ini = load_ini_sections(_get_path("languages_path", "languages.ini"), log_cb=self._log)
        mature_ini = load_ini_sections(_get_path("mature_path", "mature.ini"), log_cb=self._log)
        players_ini = load_ini_sections(_get_path("players_path", "players.ini"), log_cb=self._log)
        boot_ini = load_ini_sections(_get_path("bootlegs_path", "Bootlegs.ini"), log_cb=self._log)
        proto_ini = load_ini_sections(_get_path("prototype_path", "Prototype.ini"), log_cb=self._log)
        best_ini = load_ini_sections(_get_path("bestgames_path", "bestgames.ini"), log_cb=self._log)
        series_ini = load_ini_sections(_get_path("series_path", "series.ini"), log_cb=self._log)
        mono_ini = load_ini_sections(_get_path("monochrome_path", "monochrome.ini"), log_cb=self._log)
        ctrl_ini = load_ini_sections(_get_path("controls_path", "controls.ini"), log_cb=self._log)
        mess_ini = load_ini_sections(_get_path("mess_path", "mess.ini"), log_cb=self._log)
        
        # --- VIP Lists ---
        work_arc_ini = load_ini_sections(_get_path("working_arcade_path", "working_arcade.ini"), log_cb=self._log)
        not_work_arc_ini = load_ini_sections(_get_path("not_working_arcade_path", "not_working_arcade.ini"), log_cb=self._log)

        self.catver_map = parse_mapping_section(catver_ini, "Category")
        self.languages_map = parse_languages(lang_ini)
        self.mature_set = parse_folder_list(mature_ini)
        self.players_map, self.alt_players_set = parse_players(players_ini)
        self.bootlegs_set = parse_folder_list(boot_ini)
        self.prototype_set = parse_folder_list(proto_ini)
        self.bestgames_map = parse_bestgames(best_ini)
        self.series_map = parse_series(series_ini)
        self.monochrome_map = parse_categorical_ini(mono_ini)
        self.controls_map = parse_controls_data(ctrl_ini)
        self.mess_set = parse_folder_list(mess_ini)
        self.working_arcade_set = parse_folder_list(work_arc_ini)
        self.not_working_arcade_set = parse_folder_list(not_work_arc_ini)

        self._log("✅ Unified Metadata Loaded successfully.")

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
        
        self._log(f"✅ Indexed {len(self.all_machines)} machines with Unified Metadata attached.")

    def detect_set_type(self) -> str:
        self._log("🕵️‍♂️ Running Set Type Detector...")
        clones_checked = 0
        for m in self.all_machines.values():
            if clones_checked >= 5: break
            if not m.cloneof or m.is_bios or m.is_device or not m.runnable: continue
            clone_zip, clone_7z = self.rom_dir / f"{m.name}.zip", self.rom_dir / f"{m.name}.7z"
            parent_zip, parent_7z = self.rom_dir / f"{m.cloneof}.zip", self.rom_dir / f"{m.cloneof}.7z"
            if not (clone_zip.exists() or clone_7z.exists()) and (parent_zip.exists() or parent_7z.exists()): return "Merged"
            if clone_zip.exists():
                try:
                    with zipfile.ZipFile(clone_zip, 'r') as zf:
                        if len(zf.namelist()) < m.rom_count: return "Split"
                    clones_checked += 1
                except zipfile.BadZipFile: pass 
            elif clone_7z.exists(): clones_checked += 1
        return "Non-Merged"

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
            elif 2000 <= y < 2010: decade_bucket = "2010s"
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

        simultaneous_players = self.players_map.get(name, players)
        if name in self.alt_players_set:
            simultaneous_players = 1

        if name in self.controls_map:
            ini_ctrls, ini_dirs, ini_btns, ini_alt = self.controls_map[name]
            if ini_ctrls: controls.update(ini_ctrls)
            if ini_dirs: directions.update(ini_dirs)
            if ini_btns is not None: buttons = ini_btns
            if ini_alt is not None: simultaneous_players = 1 if ini_alt else simultaneous_players

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

        raw_cat = self.catver_map.get(name, "Unknown")
        
        # --- v4.69 FIX: Restored missing logic leak ---
        is_mature = (name in self.mature_set) or ("* Mature *" in raw_cat)
        is_bootleg = (name in self.bootlegs_set)
        is_prototype = (name in self.prototype_set)
        
        # --- v4.68 FIX: Mature UI Scrub ---
        clean_cat = raw_cat.replace("* Mature *", "").strip()
        clean_cat = re.sub(r'\s+', ' ', clean_cat).strip()
        if clean_cat.endswith("/"):
            clean_cat = clean_cat[:-1].strip()
            
        cat_parts = clean_cat.split(" / ")
        cat_main = cat_parts[0].strip()
        cat_sub = cat_parts[1].strip() if len(cat_parts) > 1 else ""
        if cat_main.startswith("TTL * "): cat_main = cat_main.replace("TTL * ", "").strip()
        
        if not self.mature_set and not is_mature:
            blob = desc.lower()
            is_mature = any(x in blob for x in ["mature", "adult", "mahjong (strip)", "erotic", "nsfw", "xxx", "(nude)"])
        if not self.bootlegs_set and not is_bootleg:
            is_bootleg = any(p in desc.lower() for p in BOOTLEG_PATTERNS)
        if not self.prototype_set and not is_prototype:
            is_prototype = any(p in desc.lower() for p in PROTOTYPE_PATTERNS)

        display_type = self.monochrome_map.get(name, "Color")

        ext_regions, ext_langs = extract_locale_tags(desc)
        final_langs = self.languages_map.get(name, set()).copy()
        final_langs.update(ext_langs)

        return MachineData(
            name=name, description=desc, year=year, decade_bucket=decade_bucket, 
            cloneof=cloneof, romof=romof, is_bios=is_bios, is_mechanical=is_mech, 
            is_device=is_dev, runnable=runnable, source_file=source,
            players=players, buttons=buttons, controls=controls, directions=directions,
            rotate=rotate, driver_status=status,
            chds=chds, samples=samples, device_refs=device_refs, rom_count=rom_count,
            category=cat_main, subcategory=cat_sub,
            is_mature=is_mature,
            is_bootleg=is_bootleg,
            is_prototype=is_prototype,
            regions=ext_regions,
            languages=final_langs,
            series=self.series_map.get(name, ""),
            bestgames_score=self.bestgames_map.get(name, 0),
            simultaneous_players=simultaneous_players,
            display_type=display_type
        )

    def filter_candidates(self) -> List[MachineData]:
        self._log("🔍 Applying filters...")
        candidates = []
        selected_genres = set(self.config.get("genres", []))
        selected_decades = set(self.config.get("decades", []))
        strict_controls = self.config.get("strict_controls", False)
        require_coop = self.config.get("require_coop", False)
        min_score = self.config.get("min_score", 0)
        target_display = self.config.get("display_type", "All")
        
        status_ranks = {"good": 0, "perfect": 0, "imperfect": 1, "preliminary": 2}
        user_selection = self.config.get("emulation_status", "Working")
        max_rank_allowed = {
            "Working": 0,
            "Working & Imperfect": 1,
            "All (Incl. Preliminary)": 2
        }.get(user_selection, 0)
        
        vip_arcade_set = self.working_arcade_set | self.not_working_arcade_set
        
        for m in self.all_machines.values():
            if m.is_bios or m.is_device or m.is_mechanical: continue
            
            # --- VIP ARCADE BOUNCER ---
            if vip_arcade_set and m.name not in vip_arcade_set:
                self.skip_reasons["Filtered by VIP List (Non-Arcade/Junk)"] += 1
                continue
            
            # --- OFFLINE/FALLBACK MESS BOUNCER ---
            if not vip_arcade_set and m.name in self.mess_set:
                self.skip_reasons["Filtered by MESS.ini (Non-Arcade/Console)"] += 1
                continue
                
            if not m.runnable:
                self.skip_reasons["Not Runnable"] += 1
                continue
            if m.source_file in NON_ARCADE_SOURCE_FILES:
                self.skip_reasons["Non-Arcade Platform Source"] += 1
                continue
                
            m_status = m.driver_status.lower().strip()
            m_rank = status_ranks.get(m_status, 2)
            
            # --- VIP STATUS OVERRIDE ---
            if self.working_arcade_set and m.name in self.working_arcade_set:
                m_rank = 0
            elif self.not_working_arcade_set and m.name in self.not_working_arcade_set:
                m_rank = 2
                
            if m_rank > max_rank_allowed:
                self.skip_reasons[f"Emulation Status (Not Working)"] += 1
                continue

            if selected_decades:
                if m.decade_bucket not in selected_decades:
                    self.skip_reasons[f"Filtered Decade ({m.decade_bucket})"] += 1
                    continue
            
            if selected_genres:
                full_cat = f"{m.category} / {m.subcategory}" if m.subcategory else m.category
                if full_cat not in selected_genres and m.category not in selected_genres:
                    self.skip_reasons["Unselected Genre"] += 1
                    continue
            
            if m.category in EXCLUDED_GENRES:
                self.skip_reasons["Excluded/Non-Game Genre"] += 1
                continue

            if not self.config.get("mature") and m.is_mature:
                self.skip_reasons["Mature/Adult Theme"] += 1
                continue
                
            if min_score > 0 and m.bestgames_score < min_score:
                self.skip_reasons[f"Game Quality Below {min_score}"] += 1
                continue

            want_orient = self.config.get("orientation", "both")
            is_vert = m.rotate in (90, 270)
            if want_orient == "horizontal" and is_vert:
                self.skip_reasons["Wrong Orientation (Filtered Vertical)"] += 1
                continue
            if want_orient == "vertical" and not is_vert:
                self.skip_reasons["Wrong Orientation (Filtered Horizontal)"] += 1
                continue

            if target_display != "All":
                is_bw = m.display_type in ["Black & White", "Monochromatic", "Black & White Vectorial"]
                if target_display == "Color Only" and is_bw:
                    self.skip_reasons["Filtered Display Type (Not Color)"] += 1
                    continue
                if target_display == "Black & White Only" and not is_bw:
                    self.skip_reasons["Filtered Display Type (Color)"] += 1
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

            if require_coop and m.players > 1 and m.simultaneous_players < 2:
                self.skip_reasons["Alternating Multiplayer"] += 1
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
        
        region_order = self.config.get("region_order", [])
        if not region_order: region_order = _REGION_OPTS.copy()
            
        language_order = self.config.get("language_order", [])
        if not language_order: language_order = _LANG_OPTS.copy()

        best_games_by_family = []
        for root, members in families.items():
            def get_score(m: MachineData):
                reg_tags = m.regions if m.regions else {"Unknown"}
                lang_tags = m.languages if m.languages else {"Unknown"}

                reg_rank = 999
                for i, opt in enumerate(region_order):
                    if opt in reg_tags:
                        reg_rank = i
                        break
                if reg_rank == 999 and "Unknown" in region_order:
                    reg_rank = region_order.index("Unknown")

                lang_rank = 999
                for i, opt in enumerate(language_order):
                    if opt in lang_tags:
                        lang_rank = i
                        break
                if lang_rank == 999 and "Unknown" in language_order:
                    lang_rank = language_order.index("Unknown")

                is_parent = (m.name == root)
                status_score = 0 if is_parent else 1
                boot_penalty = 1 if m.is_bootleg else 0
                
                return (reg_rank, lang_rank, boot_penalty, status_score)

            members.sort(key=get_score)
            best = members[0]
            best_games_by_family.append(best)
            
            skipped_members = members[1:]
            if skipped_members:
                self.skip_reasons["Filtered by 1G1R Rule (Lower Priority Clone/Locale)"] += len(skipped_members)
                
        if self.config.get("consolidate_series", False):
            self._log("🧬 Consolidating Franchises (Keeping only the best game per series)...")
            series_groups = defaultdict(list)
            standalone_games = []
            
            for m in best_games_by_family:
                if m.series:
                    series_groups[m.series].append(m)
                else:
                    standalone_games.append(m)
                    
            for s_name, s_members in series_groups.items():
                s_members.sort(key=lambda x: (x.bestgames_score, x.year), reverse=True)
                best_in_series = s_members[0]
                standalone_games.append(best_in_series)
                
                skipped = s_members[1:]
                if skipped:
                    self.skip_reasons["Filtered by Series Consolidator"] += len(skipped)
                    
            final_list = standalone_games
        else:
            final_list = best_games_by_family
            
        self._log(f"✅ Reduced to {len(final_list)} games after optimizations.")
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
            
            regions = self.config.get("region_order", [])
            langs = self.config.get("language_order", [])
            reg_str = ', '.join(regions[:5]) + ('...' if len(regions) > 5 else '')
            lang_str = ', '.join(langs[:5]) + ('...' if len(langs) > 5 else '')
            f.write(f"Region Priority:   {reg_str if regions else 'Default'}\n")
            f.write(f"Lang. Priority:    {lang_str if langs else 'Default'}\n")
            f.write(f"1G1R Optimization: {'ON' if self.config.get('one_game_one_rom') else 'OFF'}\n")
            f.write(f"Emulation Status:  {self.config.get('emulation_status', 'Working')}\n")
            f.write(f"Strict Controls:   {'ON' if self.config.get('strict_controls') else 'OFF'}\n")
            f.write(f"Simult. Co-op:     {'ON' if self.config.get('require_coop') else 'OFF'}\n")
            f.write(f"Min Game Quality:  {self.config.get('min_score', 0)}+\n")
            f.write(f"Max Players:       {self.config.get('players', 'All')}\n")
            f.write(f"Max Buttons:       {self.config.get('max_buttons', 'All')}\n")
            f.write(f"Display Type:      {self.config.get('display_type', 'All')}\n")
            
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

def extract_locale_tags(desc: str) -> Tuple[Set[str], Set[str]]:
    REGION_MAP = {
        "world": "World", "usa": "USA", "us": "USA", "u s": "USA", "u.s": "USA", "u.s.": "USA",
        "europe": "Europe", "export": "Export", "japan": "Japan", "korea": "Korea", "asia": "Asia",
        "southeast asia": "Southeast Asia", "hong kong": "Hong Kong", "taiwan": "Taiwan", "china": "China",
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
    
    regions: Set[str] = set()
    languages: Set[str] = set()
    
    if not desc: return regions, languages
    for tag_group in re.findall(r"\((.*?)\)", desc):
        g = _norm(tag_group)
        for mk in multi_region_keys:
            if mk in g: regions.add(REGION_MAP[mk])
        for hit in single_region_re.findall(g):
            regions.add(REGION_MAP[_norm(hit)])
        for hit in lang_re.findall(g):
            languages.add(hit.capitalize())
        if ger_eng_re.search(tag_group): languages.update(["German","English"])
        if jpn_re.search(tag_group): regions.add("Japan")
        if cn_re.search(tag_group): regions.add("China")
        
    return regions, languages

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

def scan_xml_for_regions_and_languages(xml_path: Path) -> Tuple[List[str], List[str]]:
    regions: Set[str] = set()
    languages: Set[str] = set()
    try:
        context = ET.iterparse(xml_path, events=("end",))
        for event, elem in context:
            if elem.tag in ("machine", "game"):
                desc = elem.findtext("description", "")
                if desc and "(" in desc and ")" in desc:
                    r_tags, l_tags = extract_locale_tags(desc)
                    regions.update(r_tags)
                    languages.update(l_tags)
                elem.clear()
    except Exception:
        pass

    regions.add("Unknown")
    languages.add("Unknown")
    return sorted(regions), sorted(languages)

def scan_catver_for_genres(
    catver_path: Path, 
    mess_path: Optional[Path] = None,
    working_path: Optional[Path] = None,
    not_working_path: Optional[Path] = None
) -> List[str]:
    if not catver_path.exists(): return []
    ini = load_ini_sections(catver_path)
    mapping = parse_mapping_section(ini, "Category")
    
    mess_set = set()
    if mess_path and mess_path.exists():
        mess_ini = load_ini_sections(mess_path)
        mess_set = parse_folder_list(mess_ini)
        
    vip_set = set()
    if working_path and working_path.exists():
        vip_set.update(parse_folder_list(load_ini_sections(working_path)))
    if not_working_path and not_working_path.exists():
        vip_set.update(parse_folder_list(load_ini_sections(not_working_path)))
    
    unique_genres = set()
    for rom_name, raw_cat in mapping.items():
        
        # --- v4.67 VIP BOUNCER (GUI Scanner) ---
        if vip_set:
            if rom_name not in vip_set:
                continue 
        else:
            # Fallback if VIP missing
            if rom_name in mess_set:
                continue 
            
        # --- v4.68 FIX: Mature UI Scrub ---
        clean_cat = raw_cat.replace("* Mature *", "").strip()
        clean_cat = re.sub(r'\s+', ' ', clean_cat).strip()
        if clean_cat.endswith("/"):
            clean_cat = clean_cat[:-1].strip()
            
        if clean_cat.startswith("TTL * "): clean_cat = clean_cat.replace("TTL * ", "").strip()
        main_genre = clean_cat.split(" / ")[0].strip()
        
        genre_lower = clean_cat.lower()
        is_junk = any(keyword in genre_lower for keyword in JUNK_GENRE_KEYWORDS)
        if "music" in genre_lower and "music games" not in genre_lower:
            is_junk = True
            
        if is_junk:
            continue
        
        if main_genre and main_genre not in EXCLUDED_GENRES: 
            unique_genres.add(clean_cat) 
            
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
        
        self._last_scanned_catver = None
        self._last_scanned_xml = None
        
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except:
            pass
        self.style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'))

        self.setup_variables()
        self.build_ui()
        
        self.root.state("zoomed")
        self.root.minsize(1024, 768)
        self.show_splash_screen()
        
        self.process_queue()
        
    def setup_variables(self):
        # Paths
        self.roms_var = tk.StringVar(value=DEFAULT_CONFIG["rom_dir"])
        self.samples_var = tk.StringVar(value=DEFAULT_CONFIG["sample_dir"])
        self.xml_var = tk.StringVar(value=DEFAULT_CONFIG["full_xml"])
        self.out_var = tk.StringVar(value=DEFAULT_CONFIG["output_path"])
        
        self.catver_var = tk.StringVar(value=DEFAULT_CONFIG["catver_path"])
        self.languages_var = tk.StringVar(value=DEFAULT_CONFIG["languages_path"])
        self.mature_var = tk.StringVar(value=DEFAULT_CONFIG["mature_path"])
        self.players_var = tk.StringVar(value=DEFAULT_CONFIG["players_path"])
        self.bootlegs_var = tk.StringVar(value=DEFAULT_CONFIG["bootlegs_path"])
        self.prototype_var = tk.StringVar(value=DEFAULT_CONFIG["prototype_path"])
        self.bestgames_var = tk.StringVar(value=DEFAULT_CONFIG["bestgames_path"])
        self.series_var = tk.StringVar(value=DEFAULT_CONFIG["series_path"])
        self.monochrome_var = tk.StringVar(value=DEFAULT_CONFIG["monochrome_path"])
        self.controls_path_var = tk.StringVar(value=DEFAULT_CONFIG["controls_path"])
        self.mess_var = tk.StringVar(value=DEFAULT_CONFIG["mess_path"])
        
        self.working_arcade_var = tk.StringVar(value=DEFAULT_CONFIG["working_arcade_path"])
        self.not_working_arcade_var = tk.StringVar(value=DEFAULT_CONFIG["not_working_arcade_path"])

        # Controls
        p_val = DEFAULT_CONFIG["players"]; p_str = "All" if p_val == 99 else str(p_val)
        b_val = DEFAULT_CONFIG["max_buttons"]; b_str = "All" if b_val == 99 else str(b_val)
        self.players_var_dropdown = tk.StringVar(value=p_str)
        self.buttons_var_dropdown = tk.StringVar(value=b_str) 
        
        self.player_values = [str(i) for i in range(1, 17)] + ["All"]
        
        self.control_values = [
            "joystick", "twin stick", "trackball", "spinner", "dial", "paddle",
            "270 wheel", "360 wheel", "lightgun", "positional", "mouse", "pedal",
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
        self.require_coop_var = tk.BooleanVar(value=DEFAULT_CONFIG["require_coop"])

        # Filters
        self.orientation_var = tk.StringVar(value=DEFAULT_CONFIG["orientation"])
        self.display_type_var = tk.StringVar(value=DEFAULT_CONFIG["display_type"])
        self.status_tier_var = tk.StringVar(value=DEFAULT_CONFIG["emulation_status"])
        self.mature_filter_var = tk.BooleanVar(value=DEFAULT_CONFIG["mature"])
        self.clones_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_clones"])
        self.bootlegs_filter_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_bootlegs"])
        self.prototypes_filter_var = tk.BooleanVar(value=DEFAULT_CONFIG["include_prototypes"])
        self.one_game_one_rom_var = tk.BooleanVar(value=DEFAULT_CONFIG["one_game_one_rom"])
        self.verbose_log_var = tk.BooleanVar(value=DEFAULT_CONFIG["verbose_log"])
        
        score_val = DEFAULT_CONFIG.get("min_score", 0)
        self.min_score_var = tk.StringVar()
        if score_val == 0: self.min_score_var.set("0 (All Games)")
        elif score_val == 40: self.min_score_var.set("40 (Good+)")
        elif score_val == 70: self.min_score_var.set("70 (Excellent+)")
        elif score_val == 90: self.min_score_var.set("90 (Masterpieces)")
        else: self.min_score_var.set("0 (All Games)")
        
        self.consolidate_series_var = tk.BooleanVar(value=DEFAULT_CONFIG.get("consolidate_series", False))
        
        # Decades
        self.decade_vars = {}
        saved_decades = set(DEFAULT_CONFIG["decades"])
        for val in self.decade_values:
            self.decade_vars[val] = tk.BooleanVar(value=val in saved_decades)

        # Genres & Regions & Languages
        self.genre_vars: Dict[str, tk.BooleanVar] = {}
        
        pref_regions = DEFAULT_CONFIG.get("region_order")
        if pref_regions:
            seen = set()
            self.pending_pref_regions = [x for x in pref_regions if not (x in seen or seen.add(x))]
        else:
            self.pending_pref_regions = None

        pref_langs = DEFAULT_CONFIG.get("language_order")
        if pref_langs:
            seen = set()
            self.pending_pref_languages = [x for x in pref_langs if not (x in seen or seen.add(x))]
        else:
            self.pending_pref_languages = None
            
        self.pending_pref_genres = DEFAULT_CONFIG.get("genres", [])
        
        self.nav_buttons = {}

    def _open_link(self, url: str) -> None:
        webbrowser.open_new(url)

    # -------------------------------
    # LIFECYCLE 
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
            "• (Recommended) The ProgettoSnaps metadata files (catver.ini, languages.ini, etc.).\n"
            "• (Recommended) Controls.ini data from controls.arcadecontrols.com.\n\n"
            "If dropped directly in your MAME root folder, the app can automatically fetch or generate these files for you!"
        )
        instructions_frame = ttk.LabelFrame(main_frame, text="First-Time Setup", padding=10)
        instructions_frame.pack(pady=10, fill=tk.X, expand=True)
        ttk.Label(instructions_frame, text=instructions_text, wraplength=550, justify=tk.LEFT).pack(fill=tk.X)

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
            
        def on_close():
            if messagebox.askyesno("Exit", "You must Agree to the terms to use this tool. Are you sure you want to exit?"):
                self.root.destroy()

        ttk.Button(main_frame, text="Agree & Continue", command=on_agree).pack(pady=20)

        splash.update_idletasks()
        width = max(splash.winfo_reqwidth(), 700)
        height = min(splash.winfo_reqheight(), 650)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        splash.geometry(f"{width}x{height}+{x}+{y}")
        
        splash.protocol("WM_DELETE_WINDOW", on_close)
        play_audio_cue("play_game.wav")

    def prompt_update_check(self):
        ans = messagebox.askyesno("Check for Updates?", "Do you want to check GitHub for a newer version of this tool before starting?")
        if ans:
            self._perform_update_check(startup=True)
        else:
            self.check_prerequisites(self.script_dir)

    def _perform_update_check(self, startup=False):
        def check():
            try:
                url = f"{GITHUB_API_URL}?t={int(time.time())}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
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
                            if dl: webbrowser.open(GITHUB_LATEST_URL)
                            if startup: self.check_prerequisites(self.script_dir)
                        self.root.after(0, prompt_dl)
                    else:
                        def prompt_ok():
                            messagebox.showinfo("Up to Date", f"You are running the latest version (v{CURRENT_VERSION}).")
                            if startup: self.check_prerequisites(self.script_dir)
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
        
        ini_checks = [
            ("catver.ini", self.catver_var),
            ("languages.ini", self.languages_var),
            ("mature.ini", self.mature_var),
            ("players.ini", self.players_var),
            ("Bootlegs.ini", self.bootlegs_var),
            ("Prototype.ini", self.prototype_var),
            ("bestgames.ini", self.bestgames_var),
            ("series.ini", self.series_var),
            ("monochrome.ini", self.monochrome_var),
            ("controls.ini", self.controls_path_var),
            ("mess.ini", self.mess_var),
            ("working_arcade.ini", self.working_arcade_var),
            ("not_working_arcade.ini", self.not_working_arcade_var)
        ]
        
        missing_inis = []
        for filename, var in ini_checks:
            if not Path(var.get()).exists():
                missing_inis.append(filename)

        missing_xml = not Path(self.xml_var.get()).exists()

        if mame_exe.exists():
            self.log("[SYS] ✅ MAME.exe found in directory.")
            if missing_xml or missing_inis:
                self.show_setup_wizard(root_path, missing_xml, missing_inis)
            else:
                self.start_xml_scan()
                self.start_catver_scan()
        else:
            self.log("[SYS] ⚠️ MAME.exe not found in current directory. Setup Wizard bypassed.")
            if not missing_xml: self.start_xml_scan()
            self.start_catver_scan()

    def show_setup_wizard(self, root_path: Path, missing_xml: bool, missing_inis: List[str]):
        self.wizard = tk.Toplevel(self.root)
        self.wizard.title("🛠️ MAME Folder Preparation Required")
        self.wizard.transient(self.root)
        self.wizard.grab_set() 
        
        main_frame = ttk.Frame(self.wizard, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="We noticed a few files are missing to get the most out of your Smart ROM Sorter.", wraplength=450).pack(anchor=tk.W, pady=(0, 15))
        
        self.wiz_gen_xml_var = tk.BooleanVar(value=missing_xml)
        
        if missing_inis:
            ttk.Label(main_frame, text="1. God Mode Metadata Databases (Missing)", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
            ttk.Label(main_frame, text="Select the files you wish to download from GitHub:", font=("Helvetica", 9)).pack(anchor=tk.W, padx=10, pady=(0, 2))
            ttk.Label(main_frame, text="(Metadata curated and provided by progettosnaps.net & controls.arcadecontrols.com)", font=("Helvetica", 8, "italic"), foreground="blue").pack(anchor=tk.W, padx=10, pady=(0, 5))
            
            ini_frame = ttk.Frame(main_frame)
            ini_frame.pack(anchor=tk.W, padx=25, fill=tk.X)
            
            self.wiz_ini_vars = {}
            ini_list = [
                "catver.ini", "languages.ini", "mature.ini", "players.ini", 
                "Bootlegs.ini", "Prototype.ini", "series.ini", "bestgames.ini", 
                "monochrome.ini", "controls.ini", "mess.ini", 
                "working_arcade.ini", "not_working_arcade.ini"
            ]
            
            for i, ini_name in enumerate(ini_list):
                is_missing = ini_name in missing_inis
                var = tk.BooleanVar(value=is_missing)
                self.wiz_ini_vars[ini_name] = var
                cb = ttk.Checkbutton(ini_frame, text=ini_name, variable=var)
                cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=5, pady=2)
                
            ttk.Label(main_frame, text="(Downloads directly to the /folders dir)", font=("Helvetica", 8)).pack(anchor=tk.W, padx=25, pady=(10,10))
        
        if missing_xml:
            ttk.Label(main_frame, text="2. Database File (full.xml is missing)", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
            ttk.Checkbutton(main_frame, text="Generate this now from your local MAME.exe", variable=self.wiz_gen_xml_var).pack(anchor=tk.W, padx=10)
            ttk.Label(main_frame, text="(Note: This can take 3-5 minutes depending on your CPU)", font=("Helvetica", 8)).pack(anchor=tk.W, padx=25, pady=(0,10))
        
        self.wiz_progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.wiz_progress.pack(fill=tk.X, pady=(15, 10))
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.wiz_start_btn = ttk.Button(btn_frame, text="[ START PREPARATION ]", command=lambda: self.execute_wizard_tasks(root_path, missing_inis, missing_xml))
        self.wiz_start_btn.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Skip for Now", command=self.wizard.destroy).pack(side=tk.RIGHT, padx=10)

        self.wizard.update_idletasks()
        width = max(self.wizard.winfo_reqwidth(), 550)
        height = min(self.wizard.winfo_reqheight(), 600)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.wizard.geometry(f"{width}x{height}+{x}+{y}")

    def execute_wizard_tasks(self, root_path: Path, missing_inis: List[str], missing_xml: bool):
        self.wiz_start_btn.config(state=tk.DISABLED)
        self.wiz_progress.start(15)
        
        selected_inis = [ini for ini, var in getattr(self, 'wiz_ini_vars', {}).items() if var.get()] if missing_inis else []
        gen_xml = self.wiz_gen_xml_var.get() if missing_xml else False
        
        threading.Thread(target=self._wizard_worker, args=(root_path, selected_inis, gen_xml), daemon=True).start()

    def _wizard_worker(self, root_path: Path, selected_inis: List[str], gen_xml: bool):
        mame_exe = root_path / "mame.exe"
        xml_path = root_path / "full.xml"
        folders_dir = root_path / "folders"
        
        if selected_inis:
            folders_dir.mkdir(exist_ok=True)
            self.status_q.put(("status", f"[NET] Downloading {len(selected_inis)} God Mode files from GitHub..."))
            
            metadata_payload = {
                "catver.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/catver.ini/catver.ini",
                    "https://raw.githubusercontent.com/mamesupport/catver.ini/master/catver.ini"
                ],
                "languages.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/languages.ini/languages.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/languages.ini"
                ],
                "series.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/series.ini/series.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/series.ini"
                ],
                "bestgames.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/bestgames.ini/bestgames.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/bestgames.ini"
                ],
                "mature.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/catver.ini/mature.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/mature.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/mature.ini"
                ],
                "players.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/players.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/players.ini"
                ],
                "Bootlegs.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/Bootlegs.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/Bootlegs.ini"
                ],
                "Prototype.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/Prototype.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/Prototype.ini"
                ],
                "monochrome.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/monochrome.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/monochrome.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/catver.ini/monochrome.ini"
                ],
                "mess.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/mess.ini",
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/mess.ini"
                ],
                "controls.ini": [
                    "http://www.ledblinky.net/downloads/controls.ini.0.141.1.zip",
                    "https://controls.arcadecontrols.com/controls.ini.0.141.1.zip"
                ],
                "working_arcade.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/Working%20Arcade.ini"
                ],
                "not_working_arcade.ini": [
                    "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/category.ini/Not%20Working%20Arcade.ini"
                ]
            }

            success_count = 0
            for filename, urls in metadata_payload.items():
                if filename not in selected_inis: 
                    continue
                    
                target_path = folders_dir / filename
                self.status_q.put(("status", f"   -> Fetching {filename}..."))
                
                success = False
                for url in urls:
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=10) as response:
                            if filename == "controls.ini" and url.endswith(".zip"):
                                with io.BytesIO(response.read()) as zip_buffer:
                                    with zipfile.ZipFile(zip_buffer) as zf:
                                        target_file = next((f for f in zf.namelist() if f.lower().endswith("controls.ini")), None)
                                        if not target_file:
                                            target_file = next((f for f in zf.namelist() if f.lower().endswith(".ini")), None)
                                        
                                        if target_file:
                                            with zf.open(target_file) as source, open(target_path, "wb") as dest:
                                                shutil.copyfileobj(source, dest)
                                            success = True
                            else:
                                with open(target_path, 'wb') as out_file:
                                    shutil.copyfileobj(response, out_file)
                                success = True
                        if success: break 
                    except Exception as e:
                        continue 
                
                if success:
                    success_count += 1
                else:
                    self.status_q.put(("status", f"   ❌ Failed {filename}: Could not locate on GitHub/Mirrors."))
            
            if success_count > 0:
                self.status_q.put(("status", f"[NET] Successfully fetched {success_count} metadata files!"))
                self.status_q.put(("set_ini_paths", str(folders_dir)))
            else:
                self.status_q.put(("status", "[NET] Offline Mode Detected or downloads failed. Falling back to internal engine."))
                
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
        else: self.roms_var.set(str(root_path / "roms"))
        
        samples_path = root_path / "samples"
        if samples_path.exists(): self.samples_var.set(str(samples_path))
        else: self.samples_var.set(str(root_path / "samples"))
            
        xml_path = root_path / "full.xml"
        if not xml_path.exists() and (root_path / "mame.xml").exists(): 
            xml_path = root_path / "mame.xml"
        self.xml_var.set(str(xml_path))
            
        folders_path = root_path / "folders"
        def _check_ini(var, name):
            p1 = folders_path / name
            p2 = root_path / name
            if p1.exists(): var.set(str(p1))
            elif p2.exists(): var.set(str(p2))
            else: var.set(str(p1)) 

        _check_ini(self.catver_var, "catver.ini")
        _check_ini(self.languages_var, "languages.ini")
        _check_ini(self.mature_var, "mature.ini")
        _check_ini(self.players_var, "players.ini")
        _check_ini(self.bootlegs_var, "Bootlegs.ini")
        _check_ini(self.prototype_var, "Prototype.ini")
        _check_ini(self.bestgames_var, "bestgames.ini")
        _check_ini(self.series_var, "series.ini")
        _check_ini(self.monochrome_var, "monochrome.ini")
        _check_ini(self.controls_path_var, "controls.ini")
        _check_ini(self.mess_var, "mess.ini")
        _check_ini(self.working_arcade_var, "working_arcade.ini")
        _check_ini(self.not_working_arcade_var, "not_working_arcade.ini")
        
        self.out_var.set(str(root_path / "filtered_mame_set"))
            
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

        self.sidebar = tk.Frame(self.top_pane, bg="#2c3e50", width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        try:
            logo_path = get_asset_path("TNTLogo400by400.png")
            raw_img = tk.PhotoImage(file=str(logo_path))
            
            target_size = 135
            scale_factor = max(1, (raw_img.height() + target_size - 1) // target_size)
            self.logo_img = raw_img.subsample(scale_factor, scale_factor) 
            
            logo_lbl = tk.Label(self.sidebar, image=self.logo_img, bg="#2c3e50")
        except Exception:
            logo_lbl = tk.Label(self.sidebar, text="MAME\nSmart Sorter", font=('Segoe UI', 16, 'bold'), bg="#2c3e50", fg="white")
            
        logo_lbl.pack(pady=(20, 15), padx=10)

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
            ("Regions & Languages", self._build_locales_tab), 
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

    def browse_ini(self, title_name, string_var, post_action=None):
        f = filedialog.askopenfilename(initialdir=self.script_dir, title=f"Select {title_name} INI", filetypes=(("INI files", "*.ini"), ("All files", "*.*")))
        if f:
            string_var.set(f)
            if post_action:
                post_action()

    def _build_paths_tab(self, parent):
        ttk.Label(parent, text="Paths & Configuration", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        ttk.Button(parent, text="✨ Auto-Select MAME Root Folder", command=self.auto_detect_paths).pack(fill=tk.X, pady=(0, 20))
        
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.BOTH, expand=True)
        
        fields = [
            ("ROMs path:", self.roms_var, self.browse_roms), 
            ("Samples path:", self.samples_var, self.browse_samples), 
            ("XML path:", self.xml_var, self.browse_xml), 
            ("Output Dir:", self.out_var, self.browse_output),
            ("CatVer path:", self.catver_var, lambda: self.browse_ini("CatVer", self.catver_var, self.start_catver_scan)), 
            ("Languages path:", self.languages_var, lambda: self.browse_ini("Languages", self.languages_var)), 
            ("Mature path:", self.mature_var, lambda: self.browse_ini("Mature", self.mature_var)), 
            ("Players path:", self.players_var, lambda: self.browse_ini("Players", self.players_var)), 
            ("Bootlegs path:", self.bootlegs_var, lambda: self.browse_ini("Bootlegs", self.bootlegs_var)), 
            ("Prototype path:", self.prototype_var, lambda: self.browse_ini("Prototype", self.prototype_var)), 
            ("BestGames path:", self.bestgames_var, lambda: self.browse_ini("BestGames", self.bestgames_var)), 
            ("Series path:", self.series_var, lambda: self.browse_ini("Series", self.series_var)), 
            ("Monochrome path:", self.monochrome_var, lambda: self.browse_ini("Monochrome", self.monochrome_var)),
            ("Controls.ini:", self.controls_path_var, lambda: self.browse_ini("Controls", self.controls_path_var)),
            ("MESS.ini:", self.mess_var, lambda: self.browse_ini("MESS", self.mess_var, self.start_catver_scan)),
            ("Work Arcade.ini:", self.working_arcade_var, lambda: self.browse_ini("Working Arcade", self.working_arcade_var, self.start_catver_scan)),
            ("Not Work Arc.ini:", self.not_working_arcade_var, lambda: self.browse_ini("Not Working Arcade", self.not_working_arcade_var, self.start_catver_scan))
        ]
        
        for i, (txt, var, cmd) in enumerate(fields):
            row = i // 2
            col_base = (i % 2) * 3
            ttk.Label(grid, text=txt, font=('Segoe UI', 10)).grid(row=row, column=col_base, sticky='e', pady=6, padx=5)
            ttk.Entry(grid, textvariable=var, font=('Segoe UI', 10)).grid(row=row, column=col_base+1, sticky='we', pady=6, padx=5)
            ttk.Button(grid, text="Browse", command=cmd).grid(row=row, column=col_base+2, padx=5)
            
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(4, weight=1)

    def _build_controls_tab(self, parent):
        ttk.Label(parent, text="Controls & Inputs", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        
        p_frame = ttk.Frame(parent)
        p_frame.pack(fill=tk.X, pady=10)
        ttk.Label(p_frame, text="Players:").pack(side=tk.LEFT)
        ttk.Combobox(p_frame, textvariable=self.players_var_dropdown, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=(5,20))
        ttk.Label(p_frame, text="Buttons:").pack(side=tk.LEFT)
        ttk.Combobox(p_frame, textvariable=self.buttons_var_dropdown, values=self.player_values, width=5, state="readonly").pack(side=tk.LEFT, padx=5)
        
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
        ttk.Label(f, text="Min Emulation Status:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(f, textvariable=self.status_tier_var, values=["Working", "Working & Imperfect", "All (Incl. Preliminary)"], state="readonly", width=25).pack(side=tk.LEFT)
        
        ttk.Label(f, text="Min Game Quality:").pack(side=tk.LEFT, padx=(15, 5))
        ttk.Combobox(f, textvariable=self.min_score_var, values=["0 (All Games)", "40 (Good+)", "70 (Excellent+)", "90 (Masterpieces)"], state="readonly", width=16).pack(side=tk.LEFT)
        
        ori_f = ttk.Frame(parent)
        ori_f.pack(fill=tk.X, pady=10)
        ttk.Label(ori_f, text="Screen Orientation:").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(ori_f, text="Both", variable=self.orientation_var, value="both").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ori_f, text="Horizontal", variable=self.orientation_var, value="horizontal").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ori_f, text="Vertical", variable=self.orientation_var, value="vertical").pack(side=tk.LEFT, padx=5)

        disp_f = ttk.Frame(parent)
        disp_f.pack(fill=tk.X, pady=10)
        ttk.Label(disp_f, text="Display Type:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(disp_f, textvariable=self.display_type_var, values=["All", "Color Only", "Black & White Only"], state="readonly", width=20).pack(side=tk.LEFT)

        lf = ttk.LabelFrame(parent, text="Inclusions", padding=10)
        lf.pack(fill=tk.X, pady=15)
        ttk.Checkbutton(lf, text="Include Clones", variable=self.clones_var).grid(row=0, column=0, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Include Bootlegs", variable=self.bootlegs_filter_var).grid(row=0, column=1, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Include Prototypes", variable=self.prototypes_filter_var).grid(row=0, column=2, sticky='w', padx=20, pady=10)
        ttk.Checkbutton(lf, text="Mature Content", variable=self.mature_filter_var).grid(row=1, column=0, sticky='w', padx=20, pady=10)
        
        ttk.Checkbutton(parent, text="Enable 1G1R (One Game, One ROM) - Highly Recommended", variable=self.one_game_one_rom_var).pack(anchor="w", pady=15)
        ttk.Checkbutton(parent, text="Consolidate Series (Keep only the best game per franchise)", variable=self.consolidate_series_var).pack(anchor="w", pady=5)
        ttk.Checkbutton(parent, text="Require Simultaneous Co-op (Ignore turn-taking multiplayer)", variable=self.require_coop_var).pack(anchor="w", pady=5)
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
        
        # --- THE V4.70 WIDESCREEN GEOMETRY FIX ---
        self.genre_inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.genre_window_id = canvas.create_window((0, 0), window=self.genre_inner_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.genre_window_id, width=e.width))
        # -----------------------------------------
        
        # --- THE V4.74 MOUSE WHEEL SCROLL FIX ---
        def _on_mousewheel(event):
            # event.delta is typically multiples of 120 on Windows
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind mouse wheel only when hovering over the canvas area
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        # ----------------------------------------
        
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
        ttk.Label(parent, text="Region & Language Priority (Used for 1G1R Optimization)", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(parent, text="Move items to the right box and order them from top (Highest Priority) to bottom.", foreground="#7f8c8d").pack(anchor="w", pady=(0, 5))
        ttk.Label(parent, text="Note: Region priority is automatically evaluated before Language priority in 1G1R sorting.", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 10))

        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        reg_frame = ttk.LabelFrame(paned, text="Regions")
        lang_frame = ttk.LabelFrame(paned, text="Languages")
        paned.add(reg_frame, weight=1)
        paned.add(lang_frame, weight=1)

        self.region_list_avail, self.region_list_pref = self._create_dual_listbox(reg_frame, "Available Regions", height=8)
        self.language_list_avail, self.language_list_pref = self._create_dual_listbox(lang_frame, "Available Languages", height=8)

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
        
        # --- THE V4.71 UX FIX FOR MANUAL TRIGGERS ---
        ttk.Button(tl_lf, text="⚙️ Generate full.xml", command=self.manual_generate_xml).pack(fill=tk.X, pady=5)
        ttk.Button(tl_lf, text="🌐 Download God Mode INIs", command=self.manual_download_catver).pack(fill=tk.X, pady=5)
        
        run_f = tk.Frame(parent, bg="#d35400", pady=3, padx=3)
        run_f.pack(fill=tk.X, pady=20)
        self.run_button = tk.Button(run_f, text="🚀 RUN MAME SMART SORTER", font=('Segoe UI', 16, 'bold'), bg="#e67e22", fg="white", bd=0, pady=10, command=self.start_sort)
        self.run_button.pack(fill=tk.BOTH, expand=True)

        eco_lf = ttk.LabelFrame(parent, text="Guides-MAME-Shoutouts-Resources", padding=15)
        eco_lf.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # --- V4.73 FIX: Restored all 20 Links correctly in 5 rows ---
        ttk.Button(eco_lf, text="🌐 TNT Official Website", command=lambda: webbrowser.open(TNT_WEBSITE_URL)).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🎥 TNT YouTube Channel", command=lambda: webbrowser.open(YOUTUBE_URL)).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="💻 GitHub Repo", command=lambda: webbrowser.open(GITHUB_URL)).grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="☕ Buy Me a Coffee", command=lambda: webbrowser.open(COFFEE_URL)).grid(row=0, column=3, sticky="ew", padx=5, pady=5)

        ttk.Button(eco_lf, text="▶️ Smart ROM Sorter Guide", command=lambda: webbrowser.open(TNT_USER_GUIDE_URL)).grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="▶️ ROMLister Guide", command=lambda: webbrowser.open(TNT_FILTER_GUIDE_URL)).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="▶️ Arcade Database Hack!", command=lambda: webbrowser.open(TNT_ROM_EASY_URL)).grid(row=1, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="▶️ ClrMamePro Guide", command=lambda: webbrowser.open(CLRMAME_VID_URL)).grid(row=1, column=3, sticky="ew", padx=5, pady=5)

        ttk.Button(eco_lf, text="👾 MAMEdev Official", command=lambda: webbrowser.open(MAMEDEV_URL)).grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="📖 MAME Wiki", command=lambda: webbrowser.open(MAMEWIKI_URL)).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🗄️ ArcadeItalia (ADB)", command=lambda: webbrowser.open(ADB_URL)).grid(row=2, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🖼️ ProgettoSnaps", command=lambda: webbrowser.open(PROGETTO_URL)).grid(row=2, column=3, sticky="ew", padx=5, pady=5)

        ttk.Button(eco_lf, text="🔥 Team Encoder", command=lambda: webbrowser.open("https://www.team-encoder.com/")).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🚀 Rogue Synapse", command=lambda: webbrowser.open("http://www.roguesynapse.com/games/last_starfighter.php")).grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="👁️ Sinnesloschen (Polybius)", command=lambda: webbrowser.open("http://www.sinnesloschen.com/")).grid(row=3, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="🕹️ Houston Arcade Expo", command=lambda: webbrowser.open("https://www.houstonarcadeexpo.com/")).grid(row=3, column=3, sticky="ew", padx=5, pady=5)
        
        # New Row 4
        ttk.Button(eco_lf, text="🕹️ Controls.ini (AC)", command=lambda: webbrowser.open(ARCADE_CONTROLS_URL)).grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="👥 NPlayers (Belgium)", command=lambda: webbrowser.open(NPLAYERS_URL)).grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="📦 AntoPISA GitHub", command=lambda: webbrowser.open(ANTO_PISA_URL)).grid(row=4, column=2, sticky="ew", padx=5, pady=5)
        ttk.Button(eco_lf, text="👁️ Polybius Archive", command=lambda: webbrowser.open(POLYBIUS_ARCHIVE_URL)).grid(row=4, column=3, sticky="ew", padx=5, pady=5)

        for i in range(4):
            eco_lf.columnconfigure(i, weight=1)

    def _create_dual_listbox(self, parent, title, height=15):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=2, padx=2)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Label(frame, text=f"{title}:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text="Preferred:").grid(row=0, column=2, sticky=tk.W)

        list_avail = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=height)
        list_avail.grid(row=1, column=0, sticky=tk.NSEW, rowspan=2)

        list_pref = tk.Listbox(frame, selectmode=tk.EXTENDED, exportselection=False, height=height)
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

    # --- MANUAL WIZARD TRIGGERS (UX FIX) ---
    def manual_generate_xml(self):
        base_dir = Path(self.xml_var.get()).parent
        mame_exe = base_dir / "mame.exe"
        if not mame_exe.exists():
            messagebox.showerror("Error", f"mame.exe not found in:\n{base_dir}\n\nPlease set correct Paths.")
            return
            
        self.run_button.config(state=tk.DISABLED)
        for btn in self.nav_buttons.values(): btn.config(state=tk.DISABLED)
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(15)
        self.progress_label.config(text="Generating XML (May take 5+ mins)...")
        
        threading.Thread(target=self._wizard_worker, args=(base_dir, [], True), daemon=True).start()

    def manual_download_catver(self):
        base_dir = Path(self.catver_var.get()).parent
        if base_dir.name == "folders":
            base_dir = base_dir.parent
        all_inis = [
            "catver.ini", "languages.ini", "mature.ini", "players.ini", 
            "Bootlegs.ini", "Prototype.ini", "series.ini", "bestgames.ini", 
            "monochrome.ini", "controls.ini", "mess.ini", 
            "working_arcade.ini", "not_working_arcade.ini"
        ]
        
        self.run_button.config(state=tk.DISABLED)
        for btn in self.nav_buttons.values(): btn.config(state=tk.DISABLED)
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(15)
        self.progress_label.config(text="Downloading God Mode INIs...")
        
        threading.Thread(target=self._wizard_worker, args=(base_dir, all_inis, False), daemon=True).start()

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
            self.status_q.put(("apply_pending_regions_langs", None))
            return
        xml_path = Path(xml_path_str)
        if not xml_path.exists():
            self.log(f"⚠️ full.xml not found at: {xml_path}")
            return
        self._last_scanned_xml = xml_path_str
        self.log(f"🔄 Scanning {xml_path.name} for regions & languages...")
        def worker():
            regions, langs = scan_xml_for_regions_and_languages(xml_path)
            self.status_q.put(("regions_langs_done", (regions, langs)))
        threading.Thread(target=worker, daemon=True).start()

    def start_catver_scan(self):
        catver_path_str = self.catver_var.get().strip()
        mess_path_str = self.mess_var.get().strip()
        working_path_str = self.working_arcade_var.get().strip()
        not_working_path_str = self.not_working_arcade_var.get().strip()
        
        if not catver_path_str: return
        
        cache_key = f"{catver_path_str}|{mess_path_str}|{working_path_str}|{not_working_path_str}"
        if getattr(self, '_last_scanned_catver', None) == cache_key:
            self.status_q.put(("apply_pending_genres", None))
            return
            
        catver_path = Path(catver_path_str)
        if not catver_path.exists(): return
        
        self._last_scanned_catver = cache_key
        self.log(f"🔄 Scanning {catver_path.name} & validating against VIP Arcade/MESS definitions...")
        
        mess_path = Path(mess_path_str) if mess_path_str else None
        working_path = Path(working_path_str) if working_path_str else None
        not_working_path = Path(not_working_path_str) if not_working_path_str else None
        
        def worker():
            genres = scan_catver_for_genres(catver_path, mess_path, working_path, not_working_path)
            self.status_q.put(("genres_done", genres))
        threading.Thread(target=worker, daemon=True).start()

    def build_config(self) -> Dict[str, Any]:
        c = [val for val, var in self.control_vars.items() if var.get()]
        d = [val for val, var in self.dir_vars.items() if var.get()]
        p = self.players_var_dropdown.get()
        b = self.buttons_var_dropdown.get()
        selected_genres = [g for g, var in self.genre_vars.items() if var.get()]
        selected_decades = [val for val, var in self.decade_vars.items() if var.get()] 
        
        region_order = list(self.region_list_pref.get(0, tk.END))
        language_order = list(self.language_list_pref.get(0, tk.END))
        
        # Keep locale_order populated for backwards compatibility with older preset loaders
        locale_order = region_order + language_order
        
        score_str = self.min_score_var.get()
        min_score = int(score_str.split()[0]) if score_str and score_str[0].isdigit() else 0
        
        cfg = {
            "schema_version": 1.5,
            "rom_dir": self.roms_var.get().strip(),
            "sample_dir": self.samples_var.get().strip(),
            "full_xml": self.xml_var.get().strip(),
            "output_path": (self.out_var.get() or "filtered_mame_set").strip(),
            "players": 99 if str(p).lower() == "all" else int(p),
            "max_buttons": 99 if str(b).lower() == "all" else int(b),
            "controls": [] if any(str(x).lower() == "all" for x in c) else c,
            "directions": [] if any(str(x).lower() == "all" for x in d) else d,
            "strict_controls": self.strict_var.get(),
            "require_coop": self.require_coop_var.get(),
            "orientation": self.orientation_var.get(),
            "display_type": self.display_type_var.get(),
            "emulation_status": self.status_tier_var.get(),
            "min_score": min_score,
            "consolidate_series": self.consolidate_series_var.get(),
            "mature": self.mature_filter_var.get(),
            "include_clones": self.clones_var.get(),
            "include_bootlegs": self.bootlegs_filter_var.get(),
            "include_prototypes": self.prototypes_filter_var.get(),
            "one_game_one_rom": self.one_game_one_rom_var.get(),
            "locale_order": locale_order,
            "region_order": region_order,
            "language_order": language_order,
            "catver_path": self.catver_var.get().strip(),
            "languages_path": self.languages_var.get().strip(),
            "mature_path": self.mature_var.get().strip(),
            "players_path": self.players_var.get().strip(),
            "bootlegs_path": self.bootlegs_var.get().strip(),
            "prototype_path": self.prototype_var.get().strip(),
            "bestgames_path": self.bestgames_var.get().strip(),
            "series_path": self.series_var.get().strip(),
            "monochrome_path": self.monochrome_var.get().strip(),
            "controls_path": self.controls_path_var.get().strip(),
            "mess_path": self.mess_var.get().strip(),
            "working_arcade_path": self.working_arcade_var.get().strip(),
            "not_working_arcade_path": self.not_working_arcade_var.get().strip(),
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
                
                self.log(f"📂 Preset loaded: {Path(f).name} (Syncing UI with databases...)")
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
                
                self.catver_var.set(cfg.get("catver_path") or str(self.script_dir / "folders" / "catver.ini"))
                self.languages_var.set(cfg.get("languages_path") or str(self.script_dir / "folders" / "languages.ini"))
                self.mature_var.set(cfg.get("mature_path") or str(self.script_dir / "folders" / "mature.ini"))
                self.players_var.set(cfg.get("players_path") or str(self.script_dir / "folders" / "players.ini"))
                self.bootlegs_var.set(cfg.get("bootlegs_path") or str(self.script_dir / "folders" / "Bootlegs.ini"))
                self.prototype_var.set(cfg.get("prototype_path") or str(self.script_dir / "folders" / "Prototype.ini"))
                self.bestgames_var.set(cfg.get("bestgames_path") or str(self.script_dir / "folders" / "bestgames.ini"))
                self.series_var.set(cfg.get("series_path") or str(self.script_dir / "folders" / "series.ini"))
                self.monochrome_var.set(cfg.get("monochrome_path") or str(self.script_dir / "folders" / "monochrome.ini"))
                self.controls_path_var.set(cfg.get("controls_path") or str(self.script_dir / "folders" / "controls.ini"))
                self.mess_var.set(cfg.get("mess_path") or str(self.script_dir / "folders" / "mess.ini"))
                self.working_arcade_var.set(cfg.get("working_arcade_path") or str(self.script_dir / "folders" / "working_arcade.ini"))
                self.not_working_arcade_var.set(cfg.get("not_working_arcade_path") or str(self.script_dir / "folders" / "not_working_arcade.ini"))
                
                p_val = cfg.get("players", 4); self.players_var_dropdown.set("All" if p_val == 99 else str(p_val))
                b_val = cfg.get("max_buttons", 8); self.buttons_var_dropdown.set("All" if b_val == 99 else str(b_val))
                self.orientation_var.set(cfg.get("orientation", "both"))
                self.display_type_var.set(cfg.get("display_type", "All"))
                self.status_tier_var.set(cfg.get("emulation_status", "Working"))
                
                score_val = cfg.get("min_score", 0)
                if score_val == 0: self.min_score_var.set("0 (All Games)")
                elif score_val == 40: self.min_score_var.set("40 (Good+)")
                elif score_val == 70: self.min_score_var.set("70 (Excellent+)")
                elif score_val == 90: self.min_score_var.set("90 (Masterpieces)")
                else: self.min_score_var.set("0 (All Games)")
                
                self.consolidate_series_var.set(cfg.get("consolidate_series", False))
                
                self.strict_var.set(cfg.get("strict_controls", False))
                self.require_coop_var.set(cfg.get("require_coop", False))
                self.mature_filter_var.set(cfg.get("mature", False))
                self.clones_var.set(cfg.get("include_clones", True))
                self.bootlegs_filter_var.set(cfg.get("include_bootlegs", True))
                self.prototypes_filter_var.set(cfg.get("include_prototypes", True))
                self.one_game_one_rom_var.set(cfg.get("one_game_one_rom", True))
                self.verbose_log_var.set(cfg.get("verbose_log", True))
                saved_controls = cfg.get("controls", [])
                for val, var in self.control_vars.items(): var.set(val in saved_controls if saved_controls else val.lower() == "all")
                saved_dirs = cfg.get("directions", [])
                for val, var in self.dir_vars.items(): var.set(val in saved_dirs if saved_dirs else val.lower() == "all")
                
                saved_decades = cfg.get("decades", self.decade_values)
                for val, var in self.decade_vars.items(): var.set(val in saved_decades)

                pref_regions = cfg.get("region_order")
                if not pref_regions:
                    legacy_locales = cfg.get("locale_order", [])
                    if legacy_locales: pref_regions = [x for x in legacy_locales if x in _REGION_OPTS]
                    else: pref_regions = _REGION_OPTS.copy()
                
                pref_langs = cfg.get("language_order")
                if not pref_langs:
                    legacy_locales = cfg.get("locale_order", [])
                    if legacy_locales: pref_langs = [x for x in legacy_locales if x in _LANG_OPTS]
                    else: pref_langs = _LANG_OPTS.copy()

                seen_reg = set(); self.pending_pref_regions = [x for x in pref_regions if not (x in seen_reg or seen_reg.add(x))]
                seen_lng = set(); self.pending_pref_languages = [x for x in pref_langs if not (x in seen_lng or seen_lng.add(x))]
                
                # --- v4.68 FIX: Sanitize legacy preset genres by scrubbing * Mature * ---
                raw_genres = cfg.get("genres", [])
                self.pending_pref_genres = [g.replace("* Mature *", "").strip().strip("/") for g in raw_genres]
                
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
                
                if kind == "progress":
                    curr, tot = data
                    if tot > 0:
                        pct = (curr / tot) * 100.0
                        self.progress_var.set(pct)
                        self.progress_label.config(text=f"Copying: {curr} / {tot}")
                        
                if kind in ("done", "error"):
                    self.run_button.config(state=tk.NORMAL)
                    if kind == "done":
                        self.progress_label.config(text="Complete!")
                        self.progress_var.set(100.0)
                        play_audio_cue("game_over.wav")
                    else:
                        self.progress_label.config(text="Error / Aborted")
                
                if kind == "set_catver_var":
                    self.catver_var.set(data)
                if kind == "set_xml_var":
                    self.xml_var.set(data)
                if kind == "set_ini_paths":
                    folders_dir = Path(data)
                    def _update_var(var, name):
                        if (folders_dir / name).exists(): var.set(str(folders_dir / name))
                    _update_var(self.catver_var, "catver.ini")
                    _update_var(self.languages_var, "languages.ini")
                    _update_var(self.mature_var, "mature.ini")
                    _update_var(self.players_var, "players.ini")
                    _update_var(self.bootlegs_var, "Bootlegs.ini")
                    _update_var(self.prototype_var, "Prototype.ini")
                    _update_var(self.bestgames_var, "bestgames.ini")
                    _update_var(self.series_var, "series.ini")
                    _update_var(self.monochrome_var, "monochrome.ini")
                    _update_var(self.controls_path_var, "controls.ini")
                    _update_var(self.mess_var, "mess.ini")
                    _update_var(self.working_arcade_var, "working_arcade.ini")
                    _update_var(self.not_working_arcade_var, "not_working_arcade.ini")
                
                if kind == "wizard_done":
                    if self.wizard:
                        self.wizard.destroy()
                        self.wizard = None
                    # --- V4.71 UX FIX: RESTORE BUTTONS AND PROGRESS BAR ---
                    self.progress_bar.stop()
                    self.progress_bar.config(mode='determinate')
                    self.run_button.config(state=tk.NORMAL)
                    for btn in self.nav_buttons.values(): btn.config(state=tk.NORMAL)
                    self.start_xml_scan()
                    self.start_catver_scan()
                    self.progress_label.config(text="Ready")
                    self.progress_var.set(0)
                
                if kind == "show_set_warning":
                    self.show_set_warning_popup(data)
                    
                if kind == "regions_langs_done":
                    regions, languages = data
                    self.region_list_avail.delete(0, tk.END)
                    self.region_list_pref.delete(0, tk.END)
                    self.language_list_avail.delete(0, tk.END)
                    self.language_list_pref.delete(0, tk.END)
                    
                    for x in regions: self.region_list_avail.insert(tk.END, x)
                    for x in languages: self.language_list_avail.insert(tk.END, x)
                    
                    self.log(f"✅ XML Scan complete. Found {len(regions)} regions and {len(languages)} languages.")
                    self.status_q.put(("apply_pending_regions_langs", None))

                if kind == "apply_pending_regions_langs":
                    if getattr(self, "pending_pref_regions", None) is not None:
                        avail = list(self.region_list_avail.get(0, tk.END))
                        for item in self.pending_pref_regions:
                            if item in avail:
                                idx = avail.index(item)
                                self.region_list_pref.insert(tk.END, self.region_list_avail.get(idx))
                                self.region_list_avail.delete(idx)
                                avail.pop(idx)
                        self.pending_pref_regions = None
                        
                    if getattr(self, "pending_pref_languages", None) is not None:
                        avail = list(self.language_list_avail.get(0, tk.END))
                        for item in self.pending_pref_languages:
                            if item in avail:
                                idx = avail.index(item)
                                self.language_list_pref.insert(tk.END, self.language_list_avail.get(idx))
                                self.language_list_avail.delete(idx)
                                avail.pop(idx)
                        self.pending_pref_languages = None
                    self.log("✅ Region & Language UI synchronized with preset.")
                
                # --- HIERARCHICAL GENRE UI (v4.72 Popularity Priority) ---
                if kind == "genres_done":
                    genres = data
                    [w.destroy() for w in self.genre_inner_frame.winfo_children()]
                    self.genre_vars.clear()
                    
                    # 1. Define our Popularity Map & Examples
                    POPULAR_MAP = {
                        "Fighter": "Fighter (Street Fighter II, Mortal Kombat)",
                        "Shooter": "Shooter (1942, Galaga)",
                        "Platform": "Platform (Donkey Kong, Bubble Bobble)",
                        "Maze": "Maze (Pac-Man, Dig Dug)",
                        "Puzzle": "Puzzle (Tetris, Bust-A-Move)",
                        "Driving": "Driving (OutRun, Pole Position)",
                        "Sports": "Sports (NBA Jam, NFL Blitz)"
                    }
                    priority_list = list(POPULAR_MAP.keys())

                    genre_hierarchy = defaultdict(list)
                    for g in sorted(genres):
                        if " / " in g:
                            main_cat, sub_cat = g.split(" / ", 1)
                            genre_hierarchy[main_cat].append((sub_cat, g))
                        else:
                            genre_hierarchy[g].append(("General", g))

                    # 2. Sort keys: Popular ones first (by priority_list order), then alphabetical
                    def get_sort_key(main_cat):
                        if main_cat in priority_list:
                            return (0, priority_list.index(main_cat))
                        return (1, main_cat)

                    sorted_main_genres = sorted(genre_hierarchy.keys(), key=get_sort_key)

                    current_row = 0
                    for main_genre in sorted_main_genres:
                        sub_list = genre_hierarchy[main_genre]
                        
                        # Use the "Example" name if it's a popular category
                        display_name = POPULAR_MAP.get(main_genre, main_genre)
                        
                        group_frame = ttk.LabelFrame(self.genre_inner_frame, text=display_name)
                        group_frame.grid(row=current_row, column=0, sticky="ew", padx=10, pady=5)
                        self.genre_inner_frame.columnconfigure(0, weight=1)
                        current_row += 1
                        
                        btn_frame = ttk.Frame(group_frame)
                        btn_frame.grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=2)
                        
                        def make_toggler(vars_to_toggle):
                            def toggle():
                                if vars_to_toggle:
                                    new_state = not vars_to_toggle[0].get()
                                    for v in vars_to_toggle:
                                        v.set(new_state)
                            return toggle

                        sub_row = 1
                        sub_col = 0
                        max_cols = 4
                        
                        group_vars = []
                        for sub_name, full_genre_string in sub_list:
                            var = tk.BooleanVar(value=True)
                            self.genre_vars[full_genre_string] = var
                            group_vars.append(var)
                            
                            display_text = GENRE_DISPLAY_MAP.get(full_genre_string, sub_name)
                            
                            chk = ttk.Checkbutton(group_frame, text=display_text, variable=var)
                            chk.grid(row=sub_row, column=sub_col, sticky='w', padx=5, pady=2)
                            
                            sub_col += 1
                            if sub_col >= max_cols: 
                                sub_col = 0
                                sub_row += 1

                        ttk.Button(btn_frame, text="Toggle All", command=make_toggler(group_vars)).pack(side=tk.LEFT)

                    self.log(f"✅ God Mode INI Scan complete. Found {len(genres)} pure arcade categories.")
                    self.status_q.put(("apply_pending_genres", None))
                # --- END HIERARCHICAL GENRE UI ---

                if kind == "apply_pending_genres":
                    if getattr(self, "pending_pref_genres", None) is not None:
                        want_all = len(self.pending_pref_genres) == 0
                        for g, var in self.genre_vars.items():
                            if want_all or g in self.pending_pref_genres:
                                var.set(True)
                            else:
                                var.set(False)
                        self.pending_pref_genres = None
                        self.log("✅ Genre UI synchronized with preset.")
                        
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