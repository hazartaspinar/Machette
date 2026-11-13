#!/usr/bin/env python3
"""
Machette — Subdomain Discovery Tool
Extracted from the ASM YUK-1 module into a single, plug-and-play Python file.
Includes: subfinder + OneForAll (passive, DNS brute force, altdns permutations) + dnsx.
Auto-installs all dependencies on Linux/macOS/Windows without requiring external scripts.
"""

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import textwrap
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
#  COLORS
# ══════════════════════════════════════════════════════════════════

# Same palette Lucille uses: basic 16-colour ANSI, not 256-colour, so the two
# tools read identically in any terminal.
C = {
    "R": "\033[31m",    # red
    "G": "\033[32m",    # green
    "Y": "\033[33m",    # yellow
    "B": "\033[36m",    # cyan
    "M": "\033[35m",    # magenta
    "W": "\033[1m",     # bold
    "D": "\033[90m",    # grey
    "0": "\033[0m",     # reset
}

# ------------------------------------------------------------- banner
# Machette: the name in the Bloody figlet font, and a machete lying under
# it, blood smeared down the blade and dripping off the edge. Plain data
# so the tool keeps zero dependencies; 24-bit colour where the terminal
# says it can (COLORTERM / known terminals), 256-colour otherwise.

# key -> (r, g, b, 256-colour fallback)
_ART_PAL = {
    '1': (255, 31, 31, 196),
    '2': (224, 0, 0, 160),
    '3': (179, 0, 0, 124),
    '4': (133, 0, 0, 88),
    '5': (86, 0, 0, 52),
    'S': (216, 221, 227, 253),
    's': (154, 160, 168, 247),
    'x': (91, 97, 107, 240),
    'h': (138, 90, 52, 130),
    'H': (92, 58, 32, 94),
    'K': (46, 29, 16, 236),
    'b': (209, 162, 74, 179),
    'B': (156, 112, 32, 136),
    'R': (224, 0, 0, 160),
    'r': (156, 0, 0, 124),
    'q': (100, 0, 0, 88),
    't': (138, 138, 138, 245),
}

_ART_TEXT = [
    '   ███▄ ▄███▓ ▄▄▄       ▄████▄   ██░ ██ ▓█████▄▄▄█████▓▄▄▄█████▓▓█████ ',
    '  ▓██▒▀█▀ ██▒▒████▄    ▒██▀ ▀█  ▓██░ ██▒▓█   ▀▓  ██▒ ▓▒▓  ██▒ ▓▒▓█   ▀ ',
    '  ▓██    ▓██░▒██  ▀█▄  ▒▓█    ▄ ▒██▀▀██░▒███  ▒ ▓██░ ▒░▒ ▓██░ ▒░▒███   ',
    '  ▒██    ▒██ ░██▄▄▄▄██ ▒▓▓▄ ▄██▒░▓█ ░██ ▒▓█  ▄░ ▓██▓ ░ ░ ▓██▓ ░ ▒▓█  ▄ ',
    '  ▒██▒   ░██▒ ▓█   ▓██▒▒ ▓███▀ ░░▓█▒░██▓░▒████▒ ▒██▒ ░   ▒██▒ ░ ░▒████▒',
    '  ░ ▒░   ░  ░ ▒▒   ▓▒█░░ ░▒ ▒  ░ ▒ ░░▒░▒░░ ▒░ ░ ▒ ░░     ▒ ░░   ░░ ▒░ ░',
    '  ░  ░      ░  ▒   ▒▒ ░  ░  ▒    ▒ ░▒░ ░ ░ ░  ░   ░        ░     ░ ░  ░',
    '  ░      ░     ░   ▒   ░         ░  ░░ ░   ░    ░        ░         ░   ',
    '         ░         ░  ░░ ░       ░  ░  ░   ░  ░                    ░  ░',
    '                       ░                                               ',
]
# one shade per text row: bright blood on top, darker toward the drip
_ART_TEXT_SHADE = '1122344555'

# the machete: glyph rows + a foreground and background key per cell
_ART_ART = [
    '',
    '           ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▖',
    ' ▄███o██o███████▁██▁██▁██▁██▁██▁██▓██▁██▓██▁█▓▁██▓██▁▓██▓█▜▘',
    ' ▀████████████████████████████▓██████▓████▓████▓███▓███▓█▜',
    '           ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀',
    '                                        ▌    ▌   ▌   ▌  ▌',
    '                                        ▘        ▌   ▘',
    '                                                 ▘',
]
_ART_ART_FG = [
    '',
    '           bbxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    ' HhhhKhhKhhbbSSSxSSxSSxSSxSSxSSxSSRSSxSSRSSxSRxSSRSSxRSSRSSS',
    ' KHHHHHHHHHBBsssssssssssssssssrssssssrssssrssssrsssrsssrss',
    '           BBSSSSSSSSSSSSSSSSSSSSSSSSSSSRSSSSRSSSRSSSRSSRS',
    '                                        r    r   r   r  r',
    '                                        q        r   q',
    '                                                 q',
]
_ART_ART_BG = [
    '',
    '',
    '     h  h       S  S  S  S  S  S  S  S  S  S SS  S  SS  S',
    '                              s      s    s    s   s   s',
    '',
    '',
    '',
    '',
]
_ART_TAG = '          subdomain discovery tool'

# for terminals that cannot draw block characters
_ART_ASCII = str.maketrans({
    "█": "#", "▓": "#", "▒": "+", "░": ".", "▄": "_", "▀": "'",
    "▖": ".", "▗": ".", "▘": "'", "▝": "'", "▌": "|", "▜": "\\",
    "▁": "_", "o": "o",
})



def _bannerable(text, stream):
    """True if this stream can render these characters."""
    try:
        text.encode(getattr(stream, "encoding", None) or "ascii")
        return True
    except (UnicodeEncodeError, LookupError, AttributeError):
        return False


def _truecolor():
    """True when the terminal can show 24-bit colour."""
    env = os.environ
    if env.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    if any(env.get(v) for v in ("WT_SESSION", "VTE_VERSION", "KONSOLE_VERSION",
                                "KITTY_WINDOW_ID", "ALACRITTY_SOCKET")):
        return True
    return env.get("TERM_PROGRAM", "") in ("iTerm.app", "WezTerm", "vscode")


def _paint(key, ground, true):
    r, g, b, idx = _ART_PAL[key]
    if true:
        return "\033[%d;2;%d;%d;%dm" % (ground, r, g, b)
    return "\033[%d;5;%dm" % (ground, idx)


def _art_row(glyphs, fg, bg, color, true):
    if not color:
        return glyphs
    fg, bg = fg.ljust(len(glyphs)), bg.ljust(len(glyphs))
    out, cur = [], None
    for ch, f, b in zip(glyphs, fg, bg):
        if ch == " " and b == " ":
            if cur is not None:
                out.append("\033[0m")
                cur = None
            out.append(" ")
            continue
        if (f, b) != cur:
            out.append("\033[0m" + _paint(f, 38, true))
            if b != " ":
                out.append(_paint(b, 48, true))
            cur = (f, b)
        out.append(ch)
    if cur is not None:
        out.append("\033[0m")
    return "".join(out)


def banner(color=True, stream=None):
    """The startup banner: the name, the machete, and the blood off it."""
    stream = stream or sys.stderr
    true = color and _truecolor()
    rows = [""]
    for i, line in enumerate(_ART_TEXT):
        shade = _ART_TEXT_SHADE[min(i, len(_ART_TEXT_SHADE) - 1)]
        rows.append(_art_row(line, shade * len(line), "", color, true))
    rows.append("")
    for glyphs, fg, bg in zip(_ART_ART, _ART_ART_FG, _ART_ART_BG):
        rows.append(_art_row(glyphs, fg, bg, color, true))
    rows.append(_art_row(_ART_TAG, "t" * len(_ART_TAG), "", color, true))
    rows.append("")
    text = "\n".join(rows)
    if not _bannerable("█▓░▄▀█", stream):
        text = text.translate(_ART_ASCII)
    return text


def p_info(msg):  print(f"{C['B']}[*]{C['0']} {msg}")
def p_ok(msg):    print(f"{C['G']}[+]{C['0']} {msg}")
def p_warn(msg):  print(f"{C['Y']}[!]{C['0']} {msg}")
def p_fail(msg):  print(f"{C['R']}[-]{C['0']} {msg}")
def p_found(msg): print(f"{C['D']}  -{C['0']} {msg}")


# ══════════════════════════════════════════════════════════════════
#  PATHS & TOOL METADATA
# ══════════════════════════════════════════════════════════════════

DATA_DIR = Path.home() / ".local" / "share" / "machette"
LOCAL_BIN_DIR = DATA_DIR / "bin"
VENDOR_DIR = DATA_DIR / "vendor"
OFA_DIR = VENDOR_DIR / "OneForAll"
OFA_VENV = VENDOR_DIR / "oneforall-venv"
OFA_RUNNER = DATA_DIR / "oneforall_runner.py"
EXE = ".exe" if os.name == "nt" else ""

TOOLS_META = {
    "subfinder": {
        "repo": "projectdiscovery/subfinder",
        "go_pkg": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    },
    "dnsx": {
        "repo": "projectdiscovery/dnsx",
        "go_pkg": "github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    },
}

ONEFORALL_ZIP = "https://github.com/shmilylty/OneForAll/archive/refs/heads/master.zip"

# Embedded OneForAll runner (from ASM common/oneforall_runner.py)
EMBEDDED_OFA_RUNNER = '''"""Run OneForAll for one domain with ASM settings and write the discovered subdomains as JSON lines."""
import json
import os
import sys
import time
from pathlib import Path

OFA_DIR = Path(os.environ["ASM_OFA_DIR"])
MAX_PERMUTATIONS = 500_000


def clean(name):
    return (name or "").strip().lower().rstrip(".")


def run_permutations(domain, live_names, log):
    """altdns-style permutations of live names, resolved via DNS only."""
    from common import resolve
    from modules import wildcard
    from modules.altdns import Altdns

    alt = Altdns(domain)
    alt.now_subdomains = set(live_names)
    alt.get_words()
    alt.extract_words()
    alt.gen_new_subdomains()
    alt.subdomains = alt.new_subdomains - alt.now_subdomains
    if not alt.subdomains:
        return []
    if len(alt.subdomains) > MAX_PERMUTATIONS:
        log(f"permutations skipped: {len(alt.subdomains)} candidates exceed the {MAX_PERMUTATIONS} limit")
        return []
    alt.gen_result()
    resolved = wildcard.deal_wildcard(resolve.run_resolve(domain, alt.results))
    return [clean(r.get("subdomain")) for r in resolved if r.get("resolve") == 1]


def main():
    domain, out_path = sys.argv[1], Path(sys.argv[2]).resolve()
    active = "--no-brute" not in sys.argv

    os.chdir(OFA_DIR)
    sys.path.insert(0, str(OFA_DIR))
    from config import settings
    from config.log import logger
    from common import utils

    settings.enable_check_network = False
    settings.enable_check_version = False
    settings.use_china_nameservers = False
    settings.enable_http_request = False
    settings.enable_banner_identify = False
    settings.enable_takeover_check = False
    settings.enable_cdn_check = False
    settings.brute_concurrent_num = 500
    settings.result_export_alive = False

    for attr, value in json.loads(os.environ.get("ASM_ONEFORALL_KEYS", "{}")).items():
        setattr(settings, attr, value)

    utils.get_net_env = lambda: True

    from oneforall import OneForAll

    started = time.time()
    ofa = OneForAll(target=domain, brute=active, dns=True, req=False, alive=False, takeover=False,
                    fmt="json", path=str(out_path.with_suffix(".ofa.json")))
    ofa.run()

    found = {}
    for path in (OFA_DIR / "results" / "temp").glob(f"collected_subdomains_{domain}_*.txt"):
        if path.stat().st_mtime >= started:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                found.setdefault(clean(line), "oneforall")
    live = set()
    for row in ofa.datas or []:
        name = clean(row.get("subdomain"))
        found[name] = f"oneforall:{row.get('source') or ''}"
        live.add(name)

    if active and live:
        for name in run_permutations(domain, live, lambda msg: logger.log("ALERT", msg)):
            found.setdefault(name, "oneforall:Altdns")

    with open(out_path, "w", encoding="utf-8") as f:
        for host, source in sorted(found.items()):
            if host:
                f.write(json.dumps({"host": host, "source": source}) + "\\n")


if __name__ == "__main__":
    main()
'''


# ══════════════════════════════════════════════════════════════════
#  AUTO-INSTALL & UPDATE MECHANISM
# ══════════════════════════════════════════════════════════════════

def find_tool(name):
    """Locate binary in local tool dir or system PATH."""
    local_bin = LOCAL_BIN_DIR / f"{name}{EXE}"
    if local_bin.exists() and os.access(local_bin, os.X_OK):
        return str(local_bin)
    return shutil.which(name)


def oneforall_python():
    """Return OneForAll's isolated venv python path, or None if not installed."""
    python = OFA_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.exists() and (OFA_DIR / "oneforall.py").exists():
        return str(python)
    return None


def get_platform_arch():
    """Return OS and architecture names matching ProjectDiscovery GitHub releases."""
    sys_name = platform.system().lower()
    os_tag = {"windows": "windows", "linux": "linux", "darwin": "macos"}.get(sys_name)
    if not os_tag:
        return None, None
    mach = platform.machine().lower()
    arch = {
        "amd64": "amd64", "x86_64": "amd64",
        "arm64": "arm64", "aarch64": "arm64",
        "i386": "386", "i686": "386", "x86": "386",
    }.get(mach)
    return os_tag, arch


def http_get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "ASM-Subdomains/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_tool_version(tool):
    """Return the installed version string of a tool."""
    bin_path = find_tool(tool)
    if not bin_path:
        return "not installed"
    try:
        proc = subprocess.run(
            [bin_path, "-version"], capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=10
        )
        out = (proc.stdout + proc.stderr).strip()
        for line in out.splitlines():
            line = line.strip()
            if line:
                return line
        return "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "not installed"


def install_or_update_go_tool(tool):
    """Download and verify SHA256 checksum for subfinder/dnsx from GitHub releases."""
    meta = TOOLS_META[tool]
    os_tag, arch = get_platform_arch()

    if not os_tag or not arch:
        p_fail(f"Unsupported OS/architecture: {platform.system()} {platform.machine()}")
        return False

    LOCAL_BIN_DIR.mkdir(parents=True, exist_ok=True)
    api_url = f"https://api.github.com/repos/{meta['repo']}/releases/latest"

    try:
        release = json.loads(http_get(api_url, timeout=20).decode("utf-8"))
    except Exception as e:
        p_warn(f"Failed to fetch {tool} release info from GitHub ({e})")
        if shutil.which("go"):
            p_info(f"Fallback: installing {tool} via Go...")
            proc = subprocess.run(["go", "install", meta["go_pkg"]], capture_output=True, text=True, timeout=300)
            return proc.returncode == 0
        return False

    suffix = f"_{os_tag}_{arch}.zip"
    assets = release.get("assets", [])
    asset = next((a for a in assets if a.get("name", "").lower().endswith(suffix)), None)
    if not asset:
        p_fail(f"No {os_tag}_{arch} release package found for {tool}.")
        return False

    checksums = next((a for a in assets if a.get("name", "").endswith("checksums.txt")), None)

    p_info(f"Downloading {tool} ({release.get('tag_name', 'latest')})...")
    try:
        data = http_get(asset["browser_download_url"], timeout=120)
    except Exception as e:
        p_fail(f"Failed to download {tool}: {e}")
        return False

    if checksums:
        try:
            expected = None
            for line in http_get(checksums["browser_download_url"], timeout=30).decode().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == asset["name"]:
                    expected = parts[0]
            actual = hashlib.sha256(data).hexdigest()
            if expected and expected != actual:
                p_fail(f"{tool}: checksum mismatch! expected={expected} got={actual}")
                return False
        except Exception:
            pass

    binary_name = f"{tool}{EXE}"
    dest_path = LOCAL_BIN_DIR / binary_name
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            member = next((m for m in zf.namelist() if Path(m).name == binary_name), None)
            if not member:
                p_fail(f"Binary '{binary_name}' not found inside archive.")
                return False
            dest_path.write_bytes(zf.read(member))
        if os.name != "nt":
            dest_path.chmod(dest_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except Exception as e:
        p_fail(f"Failed to extract {tool}: {e}")
        return False


def install_or_update_oneforall(force=False):
    """Download OneForAll and set up its isolated venv (ASM install_tools.py logic)."""
    if (OFA_DIR / "oneforall.py").exists() and OFA_VENV.exists() and not force:
        return True

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    if force or not (OFA_DIR / "oneforall.py").exists():
        p_info("Downloading OneForAll (master)...")
        try:
            data = http_get(ONEFORALL_ZIP, timeout=180)
            if OFA_DIR.exists():
                shutil.rmtree(OFA_DIR)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                prefix = zf.namelist()[0]
                for member in zf.namelist():
                    rel = member[len(prefix):]
                    if not rel or member.endswith("/"):
                        continue
                    dest = OFA_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(member))
            if os.name != "nt":
                for exe in (OFA_DIR / "thirdparty" / "massdns").glob("massdns_*"):
                    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception as e:
            p_fail(f"Failed to download OneForAll: {e}")
            return False

    p_info("Creating OneForAll virtual environment and installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(OFA_VENV)], check=True)
        py = OFA_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        pip = [str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check"]
        subprocess.run([*pip, "-r", str(OFA_DIR / "requirements.txt")], check=True)
        subprocess.run([*pip, "--upgrade", "fire"], check=True)
        return True
    except Exception as e:
        p_fail(f"Failed to set up OneForAll venv: {e}")
        return False


def ensure_tools(use_oneforall=True):
    """Automatically download and install any missing tools."""
    for tool in TOOLS_META:
        if not find_tool(tool):
            p_warn(f"{tool} not found, installing automatically...")
            if install_or_update_go_tool(tool):
                p_ok(f"{tool} installed successfully!")
            else:
                if tool == "subfinder":
                    p_fail("Failed to install subfinder. Please check your internet connection.")
                    sys.exit(1)
                else:
                    p_warn("Failed to install dnsx, DNS resolution will be skipped.")

    if use_oneforall and not oneforall_python():
        p_warn("OneForAll not found, installing automatically (first-time setup)...")
        if install_or_update_oneforall():
            p_ok("OneForAll installed successfully!")
        else:
            p_warn("OneForAll installation failed, continuing with subfinder only.")


def run_update():
    """Update subfinder, dnsx, and OneForAll to the latest versions."""
    print(banner())
    p_info("Tool Updater")
    print()

    for tool in TOOLS_META:
        old_ver = get_tool_version(tool)
        status = "updating" if old_ver != "not installed" else "installing"
        p_info(f"{status.capitalize()} {tool}...")
        if old_ver != "not installed":
            print(f"    {C['D']}Current: {old_ver}{C['0']}")
        if install_or_update_go_tool(tool):
            new_ver = get_tool_version(tool)
            if old_ver == new_ver:
                p_ok(f"{tool} is already up to date: {C['W']}{new_ver}{C['0']}")
            else:
                p_ok(f"{tool} updated: {C['R']}{old_ver}{C['0']} → {C['G']}{new_ver}{C['0']}")
        print()

    p_info("Updating OneForAll...")
    if install_or_update_oneforall(force=True):
        p_ok("OneForAll updated!")
    print()

    p_ok(f"{C['G']}Update completed!{C['0']}")
    print()


# ══════════════════════════════════════════════════════════════════
#  API KEY CONFIGURATION (ZERO-DEPENDENCY YAML PARSER)
# ══════════════════════════════════════════════════════════════════

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "machette"
DEFAULT_PROVIDER_CONFIG = DEFAULT_CONFIG_DIR / "provider-config.yaml"

EXAMPLE_PROVIDER_CONFIG = """\
# -------------------------------------------------------------
# Machette - subfinder & OneForAll API Key Configuration
# -------------------------------------------------------------
# Add your API keys below. Keys are automatically shared with both
# subfinder and OneForAll.
# -------------------------------------------------------------

shodan:
  - YOUR_SHODAN_API_KEY

securitytrails:
  - YOUR_SECURITYTRAILS_API_KEY

virustotal:
  - YOUR_VIRUSTOTAL_API_KEY

censys:
  - YOUR_CENSYS_API_ID:YOUR_CENSYS_API_SECRET

chaos:
  - YOUR_CHAOS_API_KEY

github:
  - YOUR_GITHUB_TOKEN

fofa:
  - YOUR_FOFA_EMAIL:YOUR_FOFA_KEY

hunter:
  - YOUR_HUNTER_API_KEY

zoomeyeapi:
  - YOUR_ZOOMEYE_API_KEY

fullhunt:
  - YOUR_FULLHUNT_API_KEY

quake:
  - YOUR_QUAKE_API_KEY

bevigil:
  - YOUR_BEVIGIL_API_KEY

binaryedge:
  - YOUR_BINARYEDGE_API_KEY

whoisxmlapi:
  - YOUR_WHOISXML_API_KEY

urlscan:
  - YOUR_URLSCAN_API_KEY
"""

# subfinder provider name -> OneForAll api setting(s) (from ASM yuk1.py)
ONEFORALL_KEY_MAP = {
    "securitytrails": ["securitytrails_api"],
    "shodan": ["shodan_api_key"],
    "virustotal": ["virustotal_api_key"],
    "censys": ["censys_api_id", "censys_api_secret"],
    "fofa": ["fofa_api_email", "fofa_api_key"],
    "github": ["github_api_token"],
    "threatbook": ["threatbook_api_key"],
    "zoomeyeapi": ["zoomeye_api_key"],
    "dnsdb": ["dnsdb_api_key"],
    "hunter": ["hunter_api_key"],
    "fullhunt": ["fullhunt_api_key"],
    "quake": ["quake_api_key"],
    "bevigil": ["bevigil_api"],
    "chinaz": ["chinaz_api"],
    "windvane": ["windvane_api_token"],
}


def parse_provider_yaml(config_path):
    """Lightweight parser for provider-config.yaml without requiring PyYAML."""
    if not config_path or not config_path.exists():
        return {}
    providers = {}
    current_key = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw[0].isspace() and stripped.endswith(":"):
            current_key = stripped[:-1].strip()
            providers.setdefault(current_key, [])
        elif current_key and stripped.startswith("-"):
            val = stripped[1:].strip().strip('"').strip("'")
            if val and not val.startswith("YOUR_"):
                providers[current_key].append(val)
    return {k: v for k, v in providers.items() if v}


def oneforall_keys(config_path):
    """Reuse subfinder API keys for OneForAll."""
    providers = parse_provider_yaml(config_path)
    keys = {}
    for provider, attrs in ONEFORALL_KEY_MAP.items():
        values = providers.get(provider) or []
        if not values:
            continue
        parts = str(values[0]).split(":", 1) if len(attrs) == 2 else [str(values[0])]
        if len(parts) == len(attrs):
            keys.update(zip(attrs, parts))
    return keys


def setup_config():
    """Create the config directory and example provider-config.yaml on first run."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not DEFAULT_PROVIDER_CONFIG.exists():
        DEFAULT_PROVIDER_CONFIG.write_text(EXAMPLE_PROVIDER_CONFIG, encoding="utf-8")
        p_warn(f"Created example API key config: {DEFAULT_PROVIDER_CONFIG}")
        p_warn("Add your API keys to this file to discover more subdomains!")
    return DEFAULT_PROVIDER_CONFIG


# ══════════════════════════════════════════════════════════════════
#  SUBPROCESS HELPERS
# ══════════════════════════════════════════════════════════════════

def run_jsonl(tool, args, stdin_lines=None):
    """Execute an external tool and parse its JSONL stdout lines."""
    bin_path = find_tool(tool)
    if not bin_path:
        p_fail(f"'{tool}' not found!")
        return []
    cmd = [bin_path] + args
    stdin_data = "\n".join(stdin_lines) + "\n" if stdin_lines else None
    try:
        proc = subprocess.run(
            cmd, input=stdin_data, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=3600
        )
    except FileNotFoundError:
        p_fail(f"'{tool}' not found!")
        return []
    except subprocess.TimeoutExpired:
        p_warn(f"{tool} timed out")
        return []

    rows = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


# ══════════════════════════════════════════════════════════════════
#  DISCOVERY & RESOLUTION (FULL ASM YUK-1 PIPELINE)
# ══════════════════════════════════════════════════════════════════

def in_scope(host, domains):
    """Check whether a host belongs to any of the target root domains."""
    return any(host == d or host.endswith("." + d) for d in domains)


def cdn_label(name, type_):
    """Format cdncheck result: 'cloudflare (WAF)', 'akamai (CDN)', 'aws (Cloud)'."""
    if not name:
        return ""
    return f"{name} ({'Cloud' if type_ == 'cloud' else (type_ or 'cdn').upper()})"


def enumerate_subfinder(domains, config_path=None, use_all_sources=False, timeout_min=30):
    """Discover subdomains using subfinder (passive sources)."""
    args = ["-silent", "-oJ", "-cs", "-max-time", str(timeout_min)]
    for d in domains:
        args += ["-d", d]

    if config_path and Path(config_path).exists():
        args += ["-pc", str(config_path)]

    if use_all_sources:
        args.append("-all")

    p_info("Running subfinder...")
    rows = run_jsonl("subfinder", args)

    found, skipped = {}, 0
    for r in rows:
        host = r.get("host", "").strip().lower().rstrip(".")
        if host.startswith("*."):
            host = host[2:]
        if not host:
            continue
        if not in_scope(host, domains):
            skipped += 1
            continue
        sources = r.get("sources") or ([r["source"]] if r.get("source") else [])
        found.setdefault(host, set()).update(sources)

    for d in domains:
        found.setdefault(d, set()).add("root-domain")

    p_ok(f"subfinder: {len(found)} subdomains found ({skipped} out-of-scope dropped)")
    return found


def enumerate_oneforall(domains, found, work_dir, config_path=None, brute=True, timeout_min=30):
    """Add OneForAll results (passive modules + DNS brute force + altdns permutations) to `found`."""
    python = oneforall_python()
    if not python:
        p_warn("OneForAll not installed, skipped.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OFA_RUNNER.write_text(EMBEDDED_OFA_RUNNER, encoding="utf-8")

    keys = oneforall_keys(config_path)
    env = {
        **os.environ,
        "ASM_OFA_DIR": str(OFA_DIR),
        "ASM_ONEFORALL_KEYS": json.dumps(keys),
        "PYTHONIOENCODING": "utf-8",
    }
    p_info(f"Running OneForAll ({len(keys)} API key settings reused, brute={'on' if brute else 'off'})...")
    before = len(found)

    for domain in domains:
        out = work_dir / f"oneforall_{domain}.jsonl"
        args = [python, str(OFA_RUNNER), domain, str(out)]
        if not brute:
            args.append("--no-brute")
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env=env, timeout=timeout_min * 60
            )
            if proc.returncode != 0:
                p_warn(f"OneForAll exit code {proc.returncode} for {domain}: {proc.stderr.strip()[-300:]}")
        except subprocess.TimeoutExpired:
            p_warn(f"OneForAll timed out for {domain}; keeping partial results")

        if out.exists():
            for line in out.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                host = row["host"]
                if in_scope(host, domains):
                    found.setdefault(host, set()).add(row["source"])

    p_ok(f"OneForAll: {len(found) - before} new subdomains added (total {len(found)})")


def resolve_subdomains(subdomains, threads=25):
    """Resolve discovered hosts with dnsx (A/AAAA/CNAME/CDN)."""
    if not find_tool("dnsx"):
        p_warn("dnsx not found, skipping DNS resolution.")
        return {s: {"a": [], "aaaa": [], "cname": [], "cdn": "", "status": "?"} for s in subdomains}

    p_info(f"Resolving {len(subdomains)} hosts with dnsx...")
    rows = run_jsonl(
        "dnsx",
        ["-a", "-aaaa", "-cname", "-resp", "-json", "-or", "-cdn",
         "-silent", "-t", str(threads), "-retry", "2"],
        stdin_lines=subdomains
    )

    result = {}
    for r in rows:
        host = r.get("host", "").lower()
        a = sorted(set(r.get("a") or []))
        aaaa = sorted(set(r.get("aaaa") or []))
        cname = r.get("cname") or []
        cdn = cdn_label(r.get("cdn-name"), r.get("cdn-type")) if r.get("cdn") else ""
        status = "LIVE" if (a or aaaa) else "DEAD"
        result[host] = {"a": a, "aaaa": aaaa, "cname": cname, "cdn": cdn, "status": status}

    for s in subdomains:
        if s not in result:
            result[s] = {"a": [], "aaaa": [], "cname": [], "cdn": "", "status": "DEAD"}

    live = sum(1 for v in result.values() if v["status"] == "LIVE")
    p_ok(f"{live}/{len(subdomains)} hosts resolved to an IP")
    return result


# ══════════════════════════════════════════════════════════════════
#  REPORTING
# ══════════════════════════════════════════════════════════════════

def save_txt(items, filepath):
    """Write items one per line to a plain text file."""
    filepath.write_text("\n".join(items) + "\n", encoding="utf-8")


def save_html(domains, found_map, dns_data, filepath):
    """Generate a single-file interactive HTML report."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subdomains = sorted(found_map.keys())
    total = len(subdomains)
    live = sum(1 for s in subdomains if dns_data.get(s, {}).get("status") == "LIVE")
    dead = total - live

    rows_html = ""
    for i, sub in enumerate(subdomains, 1):
        d = dns_data.get(sub, {})
        ips = ", ".join(d.get("a", []) + d.get("aaaa", []))
        cnames = ", ".join(d.get("cname", []))
        cdn = d.get("cdn", "")
        sources = ", ".join(sorted(found_map.get(sub, [])))
        status = d.get("status", "?")

        if status == "LIVE":
            status_badge = '<span class="badge live">LIVE</span>'
        elif status == "DEAD":
            status_badge = '<span class="badge dead">DEAD</span>'
        else:
            status_badge = '<span class="badge unknown">?</span>'

        rows_html += f"""<tr>
            <td class="num">{i}</td>
            <td class="host">{sub}</td>
            <td>{status_badge}</td>
            <td><code>{ips}</code></td>
            <td>{cnames}</td>
            <td>{cdn}</td>
            <td><small>{sources}</small></td>
        </tr>\n"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Machette - {', '.join(domains)}</title>
<style>
:root {{
    --bg: #0b0d17; --surface: #111827; --border: #1e293b;
    --red: #ef4444; --green: #22c55e; --cyan: #06b6d4;
    --amber: #f59e0b; --gray: #94a3b8; --text: #e2e8f0;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace; background: var(--bg); color: var(--text); }}

.header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    padding: 2.5rem 2rem; text-align: center;
    border-bottom: 2px solid var(--cyan);
}}
.header h1 {{ font-size: 2.4rem; color: var(--cyan); letter-spacing: 4px; }}
.header .meta {{ color: var(--gray); margin-top: 0.6rem; font-size: 0.85rem; }}

.cards {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1rem; padding: 1.5rem 2rem; max-width: 800px; margin: 0 auto;
}}
.card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.2rem; text-align: center;
}}
.card .val {{ font-size: 2.2rem; font-weight: bold; }}
.card .val.total {{ color: var(--cyan); }}
.card .val.live {{ color: var(--green); }}
.card .val.dead {{ color: var(--red); }}
.card .lbl {{ color: var(--gray); font-size: 0.8rem; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }}

.content {{ max-width: 1400px; margin: 0 auto; padding: 1rem 2rem 3rem; }}
.section-title {{
    color: var(--cyan); font-size: 1.1rem; margin: 1.5rem 0 0.8rem;
    padding-bottom: 6px; border-bottom: 1px solid var(--border);
    letter-spacing: 1px;
}}

table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
thead th {{
    background: var(--surface); color: var(--amber); padding: 10px 12px;
    text-align: left; position: sticky; top: 0; z-index: 1;
    border-bottom: 2px solid var(--border); text-transform: uppercase;
    font-size: 0.75rem; letter-spacing: 1px;
}}
tbody td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
tbody tr:hover {{ background: rgba(6,182,212,0.04); }}
.num {{ color: var(--gray); width: 40px; text-align: center; }}
.host {{ color: #f1f5f9; font-weight: 600; }}
code {{ background: #1e293b; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; color: var(--green); }}

.badge {{
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.7rem; font-weight: bold; letter-spacing: 1px;
}}
.badge.live {{ background: rgba(34,197,94,0.15); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }}
.badge.dead {{ background: rgba(239,68,68,0.12); color: var(--red); border: 1px solid rgba(239,68,68,0.25); }}
.badge.unknown {{ background: rgba(148,163,184,0.1); color: var(--gray); border: 1px solid rgba(148,163,184,0.2); }}

.search-box {{
    width: 100%; padding: 10px 14px; background: var(--surface); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px; font-family: inherit;
    font-size: 0.9rem; margin-bottom: 1rem; outline: none;
}}
.search-box:focus {{ border-color: var(--cyan); }}

.footer {{
    text-align: center; padding: 2rem; color: #475569; font-size: 0.75rem;
    border-top: 1px solid var(--border);
}}
</style>
</head>
<body>

<div class="header">
    <h1>MACHETTE</h1>
    <div class="meta">{stamp} - {', '.join(domains)}</div>
</div>

<div class="cards">
    <div class="card"><div class="val total">{total}</div><div class="lbl">Total</div></div>
    <div class="card"><div class="val live">{live}</div><div class="lbl">Live</div></div>
    <div class="card"><div class="val dead">{dead}</div><div class="lbl">Dead</div></div>
</div>

<div class="content">
    <div class="section-title">SUBDOMAIN LIST</div>
    <input type="text" class="search-box" id="search" placeholder="Filter... (subdomain, IP, CDN, source)">
    <table>
        <thead><tr>
            <th>#</th><th>Subdomain</th><th>Status</th><th>IP Addresses</th><th>CNAME</th><th>CDN / WAF</th><th>Sources</th>
        </tr></thead>
        <tbody id="tbody">{rows_html}</tbody>
    </table>
</div>

<div class="footer">Machette v1.0</div>

<script>
document.getElementById('search').addEventListener('input', function() {{
    const q = this.value.toLowerCase();
    document.querySelectorAll('#tbody tr').forEach(tr => {{
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}});
</script>
</body>
</html>"""

    filepath.write_text(html, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════
#  MAIN ENTRYPOINT
# ══════════════════════════════════════════════════════════════════

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--update" in sys.argv:
        run_update()
        sys.exit(0)

    print(banner())

    ap = argparse.ArgumentParser(
        description="Machette - Subdomain Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python3 machette.py -d target.com
          python3 machette.py -d target.com target2.com
          python3 machette.py -l domains.txt
          python3 machette.py -d target.com --no-brute
          python3 machette.py -d target.com --no-oneforall
          python3 machette.py -d target.com -pc /path/to/provider-config.yaml
          python3 machette.py --setup-keys
          python3 machette.py --update
        """)
    )
    ap.add_argument("-d", "--domain", nargs="+",
                    help="Target root domain(s) to scan")
    ap.add_argument("-l", "--list", dest="domain_list", default=None,
                    help="File containing target domains (one per line)")
    ap.add_argument("-o", "--output", default=None,
                    help="Output directory (default: ./machette_<domain>_<timestamp>/)")
    ap.add_argument("-pc", "--provider-config", default=None,
                    help="Path to provider-config.yaml (API keys)")
    ap.add_argument("--all-sources", action="store_true",
                    help="Use all subfinder sources (slower, more thorough)")
    ap.add_argument("--no-oneforall", action="store_true",
                    help="Skip OneForAll discovery (subfinder only)")
    ap.add_argument("--no-brute", action="store_true",
                    help="Skip OneForAll DNS brute force and permutations (passive only)")
    ap.add_argument("-t", "--threads", type=int, default=25,
                    help="DNS resolution thread count (default: 25)")
    ap.add_argument("--timeout", type=int, default=30,
                    help="Per-tool timeout in minutes (default: 30)")
    ap.add_argument("--no-resolve", action="store_true",
                    help="Skip DNS resolution, only list discovered subdomains")
    ap.add_argument("--setup-keys", action="store_true",
                    help="Create the API key configuration file")
    ap.add_argument("--update", action="store_true",
                    help="Update subfinder, dnsx, and OneForAll")
    args = ap.parse_args()

    # -- API key setup mode --
    if args.setup_keys:
        cfg = setup_config()
        print()
        p_ok(f"Config file: {cfg}")
        p_info("Edit this file to add your API keys:")
        print(f"\n    {C['G']}nano {cfg}{C['0']}\n")
        p_info("Then start a scan:")
        print(f"\n    {C['G']}python3 machette.py -d target.com{C['0']}\n")
        sys.exit(0)

    domains = []
    if args.domain:
        domains.extend(d.lower().strip() for d in args.domain if d.strip())
    if args.domain_list:
        list_path = Path(args.domain_list)
        if not list_path.exists():
            p_fail(f"Domain list file not found: {list_path}")
            sys.exit(1)
        for line in list_path.read_text(encoding="utf-8").splitlines():
            line = line.strip().lower()
            if line and not line.startswith("#"):
                domains.append(line)

    domains = sorted(set(domains))
    if not domains:
        ap.print_help()
        print(f"\n  {C['R']}Error: -d/--domain or -l/--list is required!{C['0']}\n")
        sys.exit(1)

    # -- API key config (check -pc, then local ./provider-config.yaml, then default) --
    config_path = None
    local_cfg = Path(__file__).resolve().parent / "provider-config.yaml"
    if args.provider_config:
        config_path = Path(args.provider_config)
        if not config_path.exists():
            p_fail(f"Config file not found: {config_path}")
            sys.exit(1)
    elif local_cfg.exists():
        config_path = local_cfg
    else:
        config_path = setup_config()

    loaded_keys = sum(len(v) for v in parse_provider_yaml(config_path).values())
    if loaded_keys > 0:
        p_ok(f"Loaded {loaded_keys} API key(s) ({config_path})")
    else:
        p_warn("No API keys configured. Run: python3 machette.py --setup-keys")

    # -- Output directory --
    if args.output:
        outdir = Path(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = Path.cwd() / f"machette_{domains[0].replace('.', '_')}_{stamp}"
    raw_dir = outdir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # -- Tool check (auto-install if missing) --
    print()
    p_info("Checking dependencies:")
    use_ofa = not args.no_oneforall
    ensure_tools(use_oneforall=use_ofa)
    p_ok("subfinder OK")
    if use_ofa and oneforall_python():
        p_ok("OneForAll OK")
    has_dnsx = find_tool("dnsx") is not None
    if has_dnsx:
        p_ok("dnsx OK")
    else:
        p_warn("dnsx missing (DNS resolution will be skipped)")

    # ==============================================================
    #  START SCAN
    # ==============================================================
    started = datetime.now()
    print()
    p_info(f"Target: {C['W']}{', '.join(domains)}{C['0']}")
    print()

    # 1. Subdomain discovery (subfinder + OneForAll)
    p_info(f"{C['W']}[1/3]{C['0']} Passive discovery (subfinder)...")
    found_map = enumerate_subfinder(
        domains,
        config_path=config_path,
        use_all_sources=args.all_sources,
        timeout_min=args.timeout
    )

    if use_ofa:
        print()
        p_info(f"{C['W']}[2/3]{C['0']} Deep discovery (OneForAll)...")
        enumerate_oneforall(
            domains,
            found_map,
            raw_dir,
            config_path=config_path,
            brute=not args.no_brute,
            timeout_min=args.timeout
        )

    subdomains = sorted(found_map.keys())
    print()
    p_ok(f"Total unique subdomains: {C['G']}{len(subdomains)}{C['0']}")
    print()

    for s in subdomains:
        p_found(s)
    print()

    # 2. DNS resolution
    dns_data = {}
    if not args.no_resolve and has_dnsx and subdomains:
        p_info(f"{C['W']}[3/3]{C['0']} Resolving DNS records (dnsx)...")
        dns_data = resolve_subdomains(subdomains, threads=args.threads)
        print()
    elif args.no_resolve:
        p_info("DNS resolution skipped (--no-resolve)")
        dns_data = {s: {"a": [], "aaaa": [], "cname": [], "cdn": "", "status": "?"} for s in subdomains}
    else:
        dns_data = {s: {"a": [], "aaaa": [], "cname": [], "cdn": "", "status": "?"} for s in subdomains}

    # ==============================================================
    #  EXPORT RESULTS
    # ==============================================================

    txt_file = outdir / "subdomains.txt"
    save_txt(subdomains, txt_file)

    live_subs = [s for s in subdomains if dns_data.get(s, {}).get("status") == "LIVE"]
    if live_subs:
        save_txt(live_subs, outdir / "live_subdomains.txt")

    all_ips = set()
    for d in dns_data.values():
        all_ips.update(d.get("a", []))
        all_ips.update(d.get("aaaa", []))
    if all_ips:
        save_txt(sorted(all_ips), outdir / "ips.txt")

    html_file = outdir / "report.html"
    save_html(domains, found_map, dns_data, html_file)

    # ==============================================================
    #  SUMMARY
    # ==============================================================
    elapsed = int((datetime.now() - started).total_seconds())
    live_count = len(live_subs)
    dead_count = len(subdomains) - live_count

    print(f"{C['G']}SCAN COMPLETED{C['0']} ({elapsed}s)")
    print()
    print(f"{C['B']}Total{C['0']}    {C['W']}{len(subdomains)}{C['0']} subdomains")
    print(f"{C['G']}Live{C['0']}     {C['W']}{live_count}{C['0']}")
    print(f"{C['R']}Dead{C['0']}     {C['W']}{dead_count}{C['0']}")
    print(f"{C['M']}IPs{C['0']}      {C['W']}{len(all_ips)}{C['0']} unique")
    print()
    print(f"{C['D']}Outputs:{C['0']}")
    print(f"{C['G']}  ->{C['0']} {txt_file}")
    if live_subs:
        print(f"{C['G']}  ->{C['0']} {outdir / 'live_subdomains.txt'}")
    if all_ips:
        print(f"{C['G']}  ->{C['0']} {outdir / 'ips.txt'}")
    print(f"{C['G']}  ->{C['0']} {html_file}")
    print()


if __name__ == "__main__":
    main()
