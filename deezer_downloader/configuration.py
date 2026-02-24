import sys
import os
from pathlib import Path
from configparser import ConfigParser, ParsingError, MissingSectionHeaderError

config = None


def _load_config_with_flexible_encoding(config_abs: str) -> ConfigParser:
    encodings_to_try = [
        "utf-8",
        "utf-8-sig",  # handles UTF-8 with BOM
        "utf-16",
        "utf-16-le",
        "utf-16-be",
    ]
    last_error = None
    for enc in encodings_to_try:
        parser = ConfigParser()
        try:
            with open(config_abs, "r", encoding=enc) as f:
                parser.read_file(f)
            # basic sanity check: must have at least one non-DEFAULT section
            if any(k for k in parser.keys() if k != "DEFAULT"):
                return parser
        except (UnicodeDecodeError, ParsingError, MissingSectionHeaderError) as e:
            last_error = e
            continue
        except OSError as e:
            last_error = e
            break
    print(f"ERROR: Failed to read config file with supported encodings (utf-8, utf-8-sig, utf-16, utf-16-le, utf-16-be): {config_abs}\nReason: {last_error}")
    sys.exit(1)


def load_config(config_abs):
    global config

    if not os.path.exists(config_abs):
        print(f"Could not find config file: {config_abs}")
        sys.exit(1)

    # Try multiple encodings to support files saved as UTF-16 (e.g., by some Windows editors)
    config = _load_config_with_flexible_encoding(config_abs)

    required_sections = {'mpd', 'download_dirs', 'debug', 'http', 'proxy', 'threadpool', 'deezer', 'youtubedl'}
    present_sections = set(k for k in config.keys() if k != 'DEFAULT')
    assert required_sections.issubset(present_sections), f"Validating config file failed. Check {config_abs}"
    # Optional sections are allowed, e.g. 'spotify'

    if config['mpd'].getboolean('use_mpd'):
        if not config['mpd']['music_dir_root'].startswith(config['download_dirs']['base']):
            print("ERROR: base download dir must be a subdirectory of the mpd music_dir_root")
            sys.exit(1)

    if not Path(config['youtubedl']['command']).exists():
        print(f"ERROR: yt-dlp not found at {config['youtubedl']['command']}")
        sys.exit(1)

    proxy_server = config['proxy']['server']
    if len(proxy_server) > 0:
        if not proxy_server.startswith("https://") and \
           not proxy_server.startswith("socks5"): # there is also socks5h
            print(f"ERROR: invalid proxy server address: {config['proxy']['server']}")
            sys.exit(1)

    if "DEEZER_COOKIE_ARL" in os.environ.keys():
        config["deezer"]["cookie_arl"] = os.environ["DEEZER_COOKIE_ARL"]

    if len(config["deezer"]["cookie_arl"].strip()) == 0:
        print("ERROR: cookie_arl must not be empty")
        sys.exit(1)

    if "quality" in config['deezer']:
        if config['deezer']["quality"] not in ("mp3", "flac"):
            print("ERROR: quality must be mp3 or flac in config file")
            sys.exit(1)
    else:
        print("Warning: quality not set in config file. Using mp3")
        config["deezer"]["quality"] = "mp3"
