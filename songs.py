# region Imports
if __name__ == "__main__":
    print("Loading...")
else:
    print("Loading songs...")
import math
import webbrowser
import requests
import hashlib
import subprocess
import difflib
import yt_dlp
import json
import mutagen
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, parse_qs
import keyboard
import time
import os
import random
import re
from colorama import init, Fore, Back, Style
import ctypes
import shutil
import vlc
import dotenv
import sys
# endregion

# region Helper Functions
def read(fp):
    while True:
        try:
            return json.load(fp)
        except json.decoder.JSONDecodeError:
            fp.seek(0)
            time.sleep(0.01)
def authenticate():
    clearline("Starting authorization process")
    dotenv.load_dotenv("secrets.env")
    api = os.getenv("LASTFM_API")
    secret = os.getenv("LASTFM_SECRET")
    sig_string = f"api_key{api}methodauth.getToken{secret}"
    api_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
    clearline("Performing pre-auth...")
    token = session.get(
        f"https://ws.audioscrobbler.com/2.0/?method=auth.getToken&api_key={api}&api_sig={api_sig}&format=json"
    ).json()['token']
    webbrowser.open(f"https://www.last.fm/api/auth/?api_key={api}&token={token}")
    clearline("Press Enter when authorized...", end="")
    input()
    clearline("Authenticating...")
    try:
        sig_string = f"api_key{api}methodauth.getSessiontoken{token}{secret}"
        api_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        sessionk = session.get(
            f"https://ws.audioscrobbler.com/2.0/?method=auth.getSession&token={token}&api_key={api}&api_sig={api_sig}&format=json"
        ).json()["session"]
        old = read(open("config.json"))
        old["username"] = sessionk["name"]
        old["session"] = sessionk["key"]
        old["authenticated"] = True
        json.dump(old, open("config.json", "w"), indent=4)
        clearline("Authentication completed!")
        time.sleep(2)
        threading.Thread(target=scrobble_plays()).start()
    except:
        clearline("Authentication failed. Please try again.")
        return False
    return True
def scrobble_plays():
    f = open("config.json")
    config = read(f)
    for track in config["plays"]:
        track: str
        data = track.split("!>|<!")
        scrobble(data[0], data[1])
def scrobble(name, artist, chosen_by_user=False):
    session = read(open("config.json"))['session']
    name, artist = correction(name, artist)
    if session:
        timestamp = int(time.time())
        sig_string = f"artist{artist}chosenByUser{int(chosen_by_user)}method{'track.scrobble'}sk{session}timestamp{timestamp}track{name}"
        sign = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        response = requests.post(
            "https://ws.audioscrobbler.com/2.0/",
            data={
                "method": "track.scrobble",
                "artist": artist,
                "track": name,
                "sk": session,
                "timestamp": timestamp,
                "chosenByUser": int(chosen_by_user),
                "format": "json"
            }
        )
        return response
    else:
        return False
def signed_request(method: str, params=None):
    if params is None:
        params = {}
    dotenv.load_dotenv("secrets.env")
    secret = os.getenv("LASTFM_SECRET")
    sig = ""
    for key, value in sorted(params.items()):
        sig += f"{key}{value}"
    sig += secret
    sign = hashlib.md5(sig.encode("utf-8")).hexdigest()
    url = f"https://ws.audioscrobbler.com/2.0/?method={method}&{'&'.join(f'{quote(p)}={quote(v)}' for p, v in params.items())}&format=json&api_sig={sign}"
    return session.get(url).json()
def reget(url):
    while True:
        try:
            return session.get(url, timeout=3)
        except requests.exceptions.ReadTimeout:
            pass
def autochoose(nowplaying, played:list, ms=False):
    """
    Choose a song for autoplay.
    :return:
    """
    dotenv.load_dotenv("secrets.env")
    username = read(open("config.json"))["username"]
    api = os.getenv("LASTFM_API")
    start = int(time.perf_counter() * 1000)
    toptracks = reget(
        f"https://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&period=overall&user={username}&format=json&api_key={api}"
    ).json()["toptracks"]["track"]
    topartists = reget(
        f"https://ws.audioscrobbler.com/2.0/?method=user.gettopartists&period=overall&user={username}&format=json&api_key={api}"
    ).json()["topartists"]["artist"]
    lovetracks = reget(
        f"https://ws.audioscrobbler.com/2.0/?method=user.getlovedtracks&user={username}&limit=100&api_key={api}&format=json"
    ).json()["lovedtracks"]["track"]
    listed = {
        "toptracks": [track["name"] for track in toptracks],
        "topartists": [artist["name"] for artist in topartists],
        "lovetracks": [track["name"] for track in lovetracks]
    }
    cf = suggestions(nowplaying["name"], nowplaying["artist"], 100)
    playcount = [e["name"] for e in sorted(cf, key=lambda k: k["playcount"])]
    scores = []
    if cf:
        # Scoring - out of 15
        # 3 points max for top artist
        # 4 points max for top track
        # 3 points max for highest playcount
        # 5 points for loved track
        # 1 point for matching tag
        for num, track in enumerate(cf):
            score = ((len(cf) - playcount.index(track["name"])) / len(cf)) * 3
            if track["name"] in listed["lovetracks"]:
                score += 5
            if track["name"] in listed["toptracks"]:
                rank = int(toptracks[listed["toptracks"].index(track["name"])]["@attr"]["rank"])
                score += (rank / len(toptracks)) * 4
            if track["artist"]["name"] in listed["topartists"]:
                rank = int(topartists[listed["topartists"].index(track["artist"]["name"])]["@attr"]["rank"])
                score += (rank / len(topartists)) * 3
            scores.append(score)
        copy = cf.copy()
        cf = sorted(cf, key=lambda e: scores[copy.index(e)])
        scores = sorted(scores, reverse=True)
        cf = [t for t in cf if t not in played]
        return cf[random.randint(0, 2)], ((int(time.perf_counter() * 1000) - start) if ms else None), cf, scores
    return False
def is_active():
    kernel32 = ctypes.windll.kernel32
    _u = ctypes.windll.user32
    hwnd = kernel32.GetConsoleWindow()
    pid1 = ctypes.c_ulong()
    pid2 = ctypes.c_ulong()
    _u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid1))
    _u.GetWindowThreadProcessId(_u.GetForegroundWindow(), ctypes.byref(pid2))
    return pid1.value == pid2.value
def erase():
    os.system('cls')
    clear()
def clamp(num, minimum, maximum):
    return max(minimum, (min(num, maximum)))
def keying(e):
    global pressed, held, events
    pressed = e.name
    held.add(e.name)
def unkeying(e):
    global held
    held.discard(e.name)
def is_pressed(name):
    global held
    return name in held
def uat(text, index):
    return text[:index] + u(text[index]) + text[(index + 1):]
def get_millis(starting):
    return (time.perf_counter() - starting) * 1000
def intro(color, long=True):
    clearline(style(f"█▀▀▀ █▀▀█ █▀▀▄ █▀▀▄ ▀▀▀█ {'█▀▀▄ █   █▀▀▄ █  █ █▀▀▀ █▀▀▄' if long else ''}", color, "BRIGHT"))
    clearline(style(f"▀▀▀▄ █  █ █  █ ▀▀▀█  ▄▀  {'█▀▀  █   █▀▀█ ▀▀▀█ █▀▀  █▀█ ' if long else ''}", color, "BRIGHT"))
    clearline(style(f"▀▀▀▀ ▀▀▀▀ ▀  ▀ ▀▀▀▀ ▀▀▀▀ {'▀    ▀▀▀ ▀  ▀ ▀▀▀▀ ▀▀▀▀ ▀  ▀' if long else ''}", color, "BRIGHT"))
    clearline(style(f"{'             ' if long else ''}♪ Your CLI Music Player ♪", "LIGHTBLUE_EX", "BRIGHT"))
    clearline()
def u(text):
    return f"\033[4m{text}\033[0m"
def i(text):
    return f"\033[3m{text}\033[0m"
def s(text):
    return f"\033[9m{text}\033[0m"
def clear():
    print("\033[H\033[2K\r")
def startstyle(foreground=None, styling=None):
    if foreground:
        print(getattr(Fore, foreground.upper()), end='')
    if styling:
        print(getattr(Style, styling.upper()), end='')
def resstyle():
    print(Style.RESET_ALL, end='')
def add_recent(sal: str, name: str, artist: str = None):
    text = ""
    if sal == "s":
        text = f"S:>{name}<!>{artist}"
    elif sal == "a":
        text = f"A:>{name}"
    elif sal == "l":
        text = f"L:>{name}<!>{artist}"
    data = read(open("config.json"))
    data["recents"].append(text)
    json.dump(data, open("config.json", "w"), indent=4)
def style(text: str, foreground=None, styling=None, background=None):
    parts = []
    if foreground:
        parts.append(getattr(Fore, foreground.upper()))
    if styling:
        parts.append(getattr(Style, styling.upper()))
    if background:
        parts.append(getattr(Back, background.upper()))
    return ''.join(parts) + text + Style.RESET_ALL
def get_times(milliseconds: int):
    minutes = math.floor(milliseconds / 60000)
    seconds = math.floor((milliseconds - (minutes * 60000)) / 1000)
    return [minutes, seconds, milliseconds]
def clearline(text="", end="\n"):
    print(f"\033[2K\r{text}", end=end)
def suggestions(name, artist, limit):
    """
    Get suggestions for a track.

    :returns: Name as ['name'], artist as ['artist']['name'] and playcount as ['playcount'].
    """
    name, artist = correction(name, artist)
    similar = session.get(f"https://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={quote(artist)}&track={quote(name)}&api_key=dabde6a332fadc456b8882d0d6fb0529&format=json&limit={limit + 1}").json()['similartracks']['track']
    return similar
def results(name, mode="songs", limit=5):
    if mode == "songs":
        _ = session.get(f"https://ws.audioscrobbler.com/2.0/?method=track.search&track={quote(name)}&api_key=dabde6a332fadc456b8882d0d6fb0529&limit={limit + 1}&format=json").json()
        response_ = _['results']['trackmatches']['track']
        if response_:
            return response_
        else:
            return False
    elif mode == "albums":
        _ = session.get(f"https://ws.audioscrobbler.com/2.0/?method=album.search&album={quote(name)}&api_key=dabde6a332fadc456b8882d0d6fb0529&limit={limit + 1}&format=json").json()
        response_ = _['results']['albummatches']['album']
        if response_:
            return response_
        else:
            return False
    elif mode == "artists":
        _ = session.get(f"https://ws.audioscrobbler.com/2.0/?method=artist.search&artist={quote(name)}&api_key=dabde6a332fadc456b8882d0d6fb0529&limit={limit + 1}&format=json").json()
        response_ = _['results']['artistmatches']['artist']
        if response_:
            return response_
        else:
            return False
    return None
def load_song(name, artist=None):
    global current
    tru, val = check(camelcase(name), True)
    if not tru:
        response_ = ydl.extract_info(f"ytsearch:{name} {artist if artist else ''} topic lyrics", download=False)['entries'][0]
        url = response_['original_url']
        download(url, camelcase(name), artist)
        tru, val = check(camelcase(name), True)
    val = val[0]
    current["name"] = val
    current["artist"] = get_saved_artist(val)
    return {"name": val, "artist": get_saved_artist(val)}
def play_song(title_, player_):
    global current_length, current
    titl = camelcase(title_)
    artist = get_saved_artist(titl)
    current_length = mutagen.File(f"SONGS/{titl}---{artist}.mp3").info.length * 1000
    current['length'] = current_length
    player_.stop()
    player_.set_media(vlc.Media(f"SONGS/{titl}---{artist}.mp3"))
    player_.play()
    threading.Thread(target=scrobble, args=(title_, get_saved_artist(camelcase(titl)))).start()
    old = read(open("config.json"))
    old["plays"].append(f"{titl}!>|<!{get_saved_artist(titl)}")
    json.dump(old, open("config.json", "w"), indent=4)
    add_recent("s", titl, get_saved_artist(titl))
def download(urls, name, artist):
    #    "progress_hooks": [download_progress],
    #    "progress_delta": 0.01,
    _ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": f"SONGS/{camelcase(name)}---{artist}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": 192
        }]
    }
    with yt_dlp.YoutubeDL(_ydl_opts) as ytdl:
        ytdl.download([urls])
    add_song(camelcase(name), artist)
def add_song(name, artist):
    try:
        file = open("config.json", 'r')
        data_ = read(file)
    except:
        open("config.json", 'x').close()
        data_ = {'songs': [], 'artists': []}
    data_["songs"].append(name)
    data_["artists"].append(artist)
    data_["IDs"].append(f"{name}<!>{artist}")
    with open("config.json", "w") as dumpee:
        json.dump(data_, dumpee, indent=4)
def save_config(key, value):
    file = open("config.json", "r")
    data_ = read(file)
    data_[key] = value
    with open("config.json", "w") as dumpee:
        json.dump(data_, dumpee, indent=4)
def camelcase(text):
    return normalize(" ".join(w.capitalize() for w in text.split()))
def normalize(text):
    text = re.sub(r"\(.*?\)|\(.*$", "", text)
    text = re.sub(r"\b(Feat\.|Ft\.|Video|Official|Live|Radio)\b", "", text)
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"[\\/:*?\"<>|]", "#", text)
    return text.strip()
def correction(name, artist):
    data = read(open("config.json"))
    response = session.get(
        f"https://ws.audioscrobbler.com/2.0/?method=track.getcorrection&artist={quote(artist)}&track={quote(name)}&api_key={os.getenv('LASTFM_API')}&format=json"
    ).json()["corrections"]["correction"]["track"]
    return response["name"], response["artist"]["name"]
def check(name, verbose=False):
    try:
        file = open("config.json")
    except:
        return False
    data_ = read(file)
    matched = difflib.get_close_matches(name, data_['songs'], 1, 0.85)
    if matched:
        if verbose:
            return True, matched
        else:
            return True
    else:
        if verbose:
            return False, None
        else:
            return False
def quit_(restart=False, volume=None):
    old = read(open("config.json"))
    old["volume"] = volume
    json.dump(old, open("config.json", "w"), indent=4)
    os.system("cls")
    if not restart:
        print("\033[?25h", end='')
    else:
        os.system(
            f'start wt cmd /k "title Command Prompt && echo {subprocess.check_output("ver", shell=True).decode().strip()} && echo ^(c^) Microsoft Corporation. All rights reserved. && cd /d \"{sys.argv[1]}\""'
        )
    exit(0)
def get_saved_artist(song):
    try:
        file = open("config.json")
    except:
        return None
    data_ = read(file)
    if song in data_["songs"]:
        return data_["artists"][data_["songs"].index(song)]
    else:
        return False
def download_progress(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        cur = d.get('downloaded_bytes', 0)
        if total:
            curpos = int(min(cur / total, 1) * 35)
            clearline(f"[{style('■' * curpos, 'LIGHTMAGENTA_EX', 'BRIGHT')}{'･' * (35 - curpos)}] {style('', styling='RESET_ALL')} {(cur / total) * 100:.1f}%")
def get_config(key):
    try:
        file = open("config.json")
    except:
        return None
    data_ = read(file)
    file.close()
    return data_[key]
# endregion

# region Classes
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
class Session:
    def get(self, url: str, secure: bool = False) -> dict:
        """
        Sends a POST request to the GET endpoint of the backend
        :param url: The url that would have been sent to last.fm's API minus the api_key and/or api_sig
        :param secure: Whether to include the api_sig or not; False by default
        :return: The exact response from last.fm OR the error code plsu the error message
        """
        q = url.replace("https://ws.audioscrobbler.com/2.0/?", "")
        queries_ = parse_qs(q)
        queries = {}
        for key, value in queries_.items():
            queries[key] = value[0]
        queries.pop("format")
        queries["session_key"] = get_config("ssk")
        queries["secure"] = secure
        response = requests.post(
            "https://songz.ashmit.hackclub.app/get",
            json=queries
        ).json()["response"]
        return response
    def post(self, url: str, data: dict, secure: bool = False):
        """
        Sends a POST request to the POST endpoint of the backend
        :param url: The url that would have been sent to last.fm's API minus the api_key and/or api_sig
        :param data: The POST data sent along with the POST request to last.fm
        :param secure: Whether to include the api_sig or not; False by default
        :return:
        """
        q = url.replace("https://ws.audioscrobbler.com/2.0/?", "")
        queries_ = parse_qs(q)
        queries = {}
        for key, value in queries_.items():
            queries[key] = value[0]

# endregion

# region Main Functions
def UI():
    global current, events, user32, active_window, last_active, pressed, main, queued, lefts, rhide
    # region Initialization
    intext = ""
    future = None
    laststate = "home"
    start = time.perf_counter()
    player = vlc.MediaPlayer()
    cursor = 0
    volume = 50
    pheld = False
    paused = False
    os.system("cls")
    ctrl = False
    chosen = None
    page = 1
    results_run = None
    recommendation = False
    show = 0
    showing = None
    temphome = False
    ql = False
    autoplay = False
    autochose = False
    played = []
    sartist = {
        "name": None,
        "tops": []
    }
    salbum = {
        "name": None,
        "artist": None
    }
    current = {
        "name": None,
        "artist": None,
        "length": 0
    }
    state = "home"  # home, search, album, artist, playing, results-album, results-artist, results-song
    nowplaying = {
        "name": None,
        "artist": None
    }
    executor = ThreadPoolExecutor()
    rhide = False
    esced = False
    nums = ['1', '2', '3', '4', '5', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5']
    exnums = [
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
        'num 1', 'num 2', 'num 3', 'num 4', 'num 5', 'num 6',
        'num 7', 'num 8', 'num 9', 'num 0'
    ]
    # endregion
    while True:
        with open("config.json") as f:
            config = read(f)
        active = user32.GetForegroundWindow() == active_window
        if not active:
            pressed = None
        _, height = shutil.get_terminal_size()
        clear()
        intro("LIGHTGREEN_EX")
        if state == 'home':
            clearline(f"Search: {uat(intext + ' ', (cursor + (0 if cursor == len(intext) else -1)))}")
            clearline()
            if pressed and active:
                st = "abcdefghijklmnopqrstuvwxyz1234567890"
                if pressed in list(st + st.upper()) + ['space']:
                    mod = pressed
                    if pressed == "space":
                        mod = " "
                    intext += mod
                    if cursor == len(intext) - 1:
                        cursor += 1
                if pressed == "backspace":
                    intext = intext[:-1]
                    if cursor == len(intext) + 1:
                        cursor -= 1
                if pressed == "enter":
                    laststate = state
                    state = "search"
                    erase()
                if pressed == "left":
                    cursor -= 1
                    cursor = clamp(cursor, 0, len(intext))
                if pressed == "right":
                    cursor += 1
                    cursor = clamp(cursor, 0, len(intext))
                if pressed in ['q', 'Q'] and ctrl:
                    quit_(volume=volume)
                if pressed in ['n', 'N'] and ctrl:
                    quit_(volume=volume, restart=True)
                if pressed in ['b', 'B'] and ctrl and nowplaying['name']:
                    erase()
                    temphome = False
                    laststate = state
                    state = "playing"
                if pressed in nums and ctrl:
                    recent = list(dict.fromkeys(config["recents"]))
                    recent.reverse()
                    sel = recent[int("".join(c for c in pressed if c.isdigit())) - 1]
                    if sel[0] == "S":
                        data = sel[3:].split("<!>")
                        try:
                            name, artist = data[0], data[1]
                        except IndexError:
                            name, artist = data[0], None
                        threading.Thread(target=load_song, args=(name, artist)).start()
                        erase()
                        laststate = state
                        state = "songstate"
                    elif sel[0] == "L":
                        data = sel[3:].split("<!>")
                        try:
                            name, artist = data[0], data[1]
                        except IndexError:
                            name, artist = data[0], None
                        erase()
                        salbum = session.get(
                            f"https://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={os.getenv('LASTFM_API')}&artist={quote(artist)}&album={quote(name)}&format=json"
                        ).json()['album']
                        laststate = state
                        state = "album"
                        add_recent("l", salbum["name"], salbum["artist"])
                        page = 1
                    elif sel[0] == "A":
                        stop = session.get(
                            f"https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&api_key=dabde6a332fadc456b8882d0d6fb0529&artist={quote(sel[3:])}&format=json&limit=10"
                        ).json()['toptracks']
                        sartist = {
                            "name": sel[3:],
                            "tops": stop['track'],
                            "total": int(stop['@attr']['total'])
                        }
                        add_recent("a", sartist['name'])
                        laststate = state
                        state = "artist"
                        page = 1
                pressed = None
            ctrl = keyboard.is_pressed("ctrl")
            if esced:
                clearline("[esc] Focus window")
            clearline("[Enter] Search           [Ctrl+Q] Exit")
            clearline("[Ctrl+(1-5)] Open recent [Ctrl+N] Exit & Relaunch")
            if nowplaying['name']:
                clearline("[Ctrl+B] Back")
            clearline()
            _i = 1
            try:
                recents = list(dict.fromkeys(config["recents"]))
                recents.reverse()
                clearline("Recents:")
                for recent in recents:
                    if _i < 6:
                        if recent[0] == "S":
                            metadata = recent.split("<!>")
                            name, a = metadata[0][3:], metadata[1]
                            clearline(f"{_i}. {name} by {a}")
                        elif recent[0] == "A":
                            clearline(f"{_i}. {recent[3:]} (Artist)")
                        elif recent[0] == "L":
                            metadata = recent.split("<!>")
                            name, a = metadata[0][3:], metadata[1]
                            clearline(f"{_i}. {name} by {a}")
                    _i += 1
            except Exception as e:
                if e == KeyboardInterrupt:
                    exit(1)
                else:
                    pass
            clearline()
        if state == 'playing' or temphome:
            if state == "playing":
                temphome = False
            try:
                if nowplaying['length'] and not temphome:
                    songs = get_times(nowplaying['length'])
                    curs = get_times(player.get_time())
                    lefts = get_times(songs[2] - curs[2])
                    curpos = round(curs[2] / songs[2] * 25)
                    clearline(f"{curs[0]}:{curs[1]:02} {'─' * curpos}●{'─' * (25 - curpos)} {songs[0]}:{songs[1]:02} (-{lefts[0]}:{lefts[1]:02})")
            except:
                clearline("Loading...")
            if not temphome:
                clearline(f"Playing: {nowplaying['name']} {'by' if nowplaying['artist'] else ''} {nowplaying['artist'] if nowplaying['artist'] else ''}")
            if pressed and active and state == "playing" and not temphome:
                if pressed.lower() == "space":
                    if not pheld:
                        paused = not paused
                        player.pause()
                    pheld = True
                elif pressed in ['q', 'Q']:
                    quit_(volume=volume)
                elif pressed in ['n', 'N']:
                    quit_(volume=volume, restart=True)
                elif pressed in ['a', 'A']:
                    if not paused:
                        player.play()
                        show = get_millis(start)
                        showing = "◁◁ 10 seconds"
                        player.set_time(max(0, player.get_time() - 10000))
                elif pressed in ['d', 'D']:
                    if not paused:
                        show = get_millis(start)
                        showing = "▷▷ 10 seconds"
                        player.set_time(min(player.get_time() + 10000, current['length']))
                elif pressed in ['r', 'R']:
                    if not recommendation and not chosen and nowplaying['artist'] and not rhide and not autoplay:
                        recommendation = suggestions(nowplaying['name'], nowplaying['artist'], 5)
                elif pressed in ['z', 'Z']:
                    if recommendation and not chosen and not rhide:
                        page = max(1, page - 1)
                elif pressed in ['x', 'X']:
                    if recommendation and not rhide and not chosen and not len(recommendation) > ((page + 1) * 5):
                        page += 1
                        erase()
                        recommendation = suggestions(nowplaying['name'], nowplaying['artist'], page * 5)
                elif pressed in ['h', 'H']:
                    erase()
                    intext = ""
                    cursor = 0
                    laststate = state
                    state = "home"
                elif pressed in ['o', 'O']:
                    if not autoplay:
                        _ = suggestions(nowplaying['name'], nowplaying['artist'], 5)
                        if _:
                            autoplay = True
                elif pressed in ['c', 'C']:
                    if recommendation and not chosen and not rhide:
                        erase()
                        recommendation = False
                elif pressed in nums:
                    if recommendation and not chosen and not rhide:
                        erase()
                        queued = [{}] + queued
                        ql = False
                        chosen = True
                        index = ((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)
                        queued[0]['name'] = recommendation[index]['name']
                        queued[0]['artist'] = recommendation[index]['artist']['name']
                pressed = None
            else:
                pheld = False
            try:
                if len(queued) > 0:
                    if not temphome:
                        clearline(f"Next in queue: {queued[0]['name']} by {queued[0]['artist']}")
                    if lefts[2] < 40000 and not ql:
                        ql = True
                        threading.Thread(target=load_song, args=(queued[0]['name'], queued[0]['artist'])).start()
                    if lefts[2] < 1000:
                        erase()
                        play_song(queued[0]['name'], player)
                        nowplaying = current.copy()
                        recommendation = False
                        chosen = False
                        rhide = False
                        ql = False
                        autochose = False
                        future = None
                        queued.pop(0)
            except Exception as e:
                clearline(f"ERROR: {e}")
            if recommendation and not chosen and not rhide:
                startstyle("LIGHTMAGENTA_EX", "BRIGHT")
                clearline("RECOMMENDATIONS:")
                ind = 0
                for recom in recommendation:
                    ind += 1
                    if ind > ((page - 1) * 5) and ind < ((page * 5) + 1):
                        clearline(f"{ind - ((page - 1) * 5)}. {recom['name']} by {recom['artist']['name']} (Playcount: {recom['playcount']})")
                resstyle()
            if showing:
                if (show + 1000) < get_millis(start):
                    clearline(showing)
                else:
                    showing = None
            if autoplay:
                if nowplaying['name'] not in played:
                    played.append(nowplaying['name'])
                clearline(style("Autoplay is on", "LIGHTMAGENTA_EX", "BRIGHT"))
                if lefts[2] < 60000 and len(queued) == 0:
                    if not config["authenticated"]:
                        queued = [{}] + queued
                        ch = sorted(
                            [l for l in suggestions(nowplaying['name'], nowplaying['artist'], 5) if l['name'] not in played],
                            key=lambda e: e['playcount']
                        )[-1]
                        queued[0]['name'] = ch['name']
                        queued[0]['artist'] = ch['artist']['name']
                    else:
                        if not autochose:
                            autochose = True
                            future = executor.submit(autochoose, nowplaying, played)
                        elif future.done():
                            queued = [{}] + queued
                            queued[0]['name'] = future.result()[0]['name']
                            queued[0]['artist'] = future.result()[0]['artist']['name']
            if keyboard.is_pressed("w") and active and not temphome:
                volume = min(100, volume + 1)
                clearline(f"Volume: {volume}%")
                time.sleep(0.05)
            elif keyboard.is_pressed("s") and active and not temphome:
                volume = max(0, volume - 1)
                clearline(f"Volume: {volume}%")
                time.sleep(0.05)
            if paused and not temphome:
                clearline(style("PAUSED", "LIGHTRED_EX", "BRIGHT"))
            if recommendation is not False and not recommendation and not temphome:
                rhide = True
                clearline(style("This track doesn't have similar tracks.", "LIGHTMAGENTA_EX", "BRIGHT"))
            if recommendation and not chosen and not rhide and not temphome:
                clearline(style("[1-5] Add to Queue", "LIGHTMAGENTA_EX", "BRIGHT"))
                clearline(f"{style('[Z] Previous [X] Next    [C] Close', 'LIGHTMAGENTA_EX', 'BRIGHT')}")
            else:
                clearline(("[H] Home     " if not chosen else '') + ("     [O] Autoplay" if not autoplay else ''))
            if not temphome:
                clearline("[Space] Pause [A] Rewind  [D] Fast-Forward")
                clearline("[W] +Volume   [S] -Volume [Q] Exit")
                clearline(f"[N] Exit & Relaunch       {'[R] Recommendations' if nowplaying['artist'] and not recommendation and not rhide and not autoplay else ('[H] Home' if autoplay else '')}")
                player.audio_set_volume(volume)
                clearline()
                clearline()
                clearline()
        elif state == 'search':
            clearline(f"Search: {intext}")
            clearline("[A] Artists [S] Songs [L] Albums")
            clearline("[B] Back    [Q] Exit  [N] Exit & Relaunch")
            if pressed and active:
                if pressed in ["q", "Q"]:
                    quit_(volume=volume)
                elif pressed in ["n", "N"]:
                    quit_(volume=volume, restart=True)
                elif pressed in ['b', 'B']:
                    erase()
                    laststate = state
                    state = "home"
                elif pressed in ['s', 'S']:
                    erase()
                    t, res = check(camelcase(intext), verbose=True)
                    if t:
                        if len(res) < 2:
                            laststate = state
                            state = "songstate"
                            erase()
                            threading.Thread(target=load_song, args=(intext, get_saved_artist(camelcase(intext)))).start()
                        else:
                            laststate = state
                            state = "results-song"
                            results_run = []
                            for trac in res:
                                results_run.append({
                                    "name": trac,
                                    "artist": get_saved_artist(trac)
                                })
                            erase()
                            page = 1
                    else:
                        laststate = state
                        state = "results-song"
                        results_run = results(intext)
                        erase()
                        page = 1
                elif pressed in ['l', 'L']:
                    erase()
                    results_run = results(intext, mode="albums")
                    laststate = state
                    state = "results-album"
                    page = 1
                elif pressed in ['a', 'A']:
                    erase()
                    intro("LIGHTGREEN_EX")
                    clearline("Loading...")
                    results_run = results(intext, "artists", 5)
                    laststate = state
                    state = "results-artist"
                    page = 1
                pressed = None
        elif state == 'results-song':
            if results_run:
                clearline(f"PAGE {page}")
                _j = 0
                availables = {"d": False, "a": False}
                for track in results_run:
                    if _j > (((page - 1) * 5) - 1) and _j < (page * 5):
                        clearline(f"{(_j + 1) - ((page - 1) * 5)}. {track['name']} by {track['artist']}")
                    _j += 1
                if page > 1:
                    availables['a'] = True
                if len(results_run) > 5:
                    availables['d'] = True
                if pressed and active:
                    if pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    elif pressed in ['d', 'D'] and availables['d']:
                        page += 1
                        erase()
                        results_run = results(intext, limit=(page * 5))
                    elif pressed in ['a', 'A'] and availables['a']:
                        page -= 1
                        erase()
                    elif pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = 'home'
                        intext = ''
                        cursor = 0
                    elif pressed in nums:
                        index = ((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)
                        erase()
                        threading.Thread(target=load_song, args=(results_run[index]['name'], results_run[index]['artist'])).start()
                        laststate = state
                        state = "songstate"
                    pressed = None
                if availables['a'] or availables['d']:
                    clearline(f"{'[A] Previous ' if availables['a'] else '             '}{'[D] Next' if availables['d'] else ''}")
                clearline("[1-5] Select [Q] Exit")
                clearline("[B] Back     [N] Exit & Relaunch")
            else:
                clearline("Autoplay is not available for this song.")
                clearline("[P] Play [B] Back")
                clearline("[Q] Exit [N] Exit & Relaunch")
                if pressed and active:
                    if pressed in ['p', 'P']:
                        erase()
                        threading.Thread(target=load_song, args=(intext, None)).start()
                        laststate = state
                        state = "songstate"
                    elif pressed in ['b', 'B']:
                        clear()
                        intext = ""
                        cursor = 0
                        laststate = state
                        state = "home"
                    elif pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    pressed = None
        elif state == 'songstate':
            if current['name'] and not (nowplaying['name'] and nowplaying['name'] == current['name']):
                if check(camelcase(current['name'])):
                    clearline(f"Selected song: {current['name']} by {current['artist']}")
                    clearline(f"[P] Play [B] Back {'[U] Add to queue' if nowplaying['name'] else ''}")
                    clearline("[Q] Exit [N] Exit & Relaunch")
                    if pressed and active:
                        if pressed in ['p', 'P']:
                            erase()
                            play_song(current['name'], player)
                            nowplaying = current.copy()
                            paused = False
                            laststate = state
                            state = "playing"
                            page = 1
                        elif pressed in ['b', 'B']:
                            erase()
                            state = laststate
                        elif pressed in ['u', 'U'] and nowplaying['name']:
                            erase()
                            queued.append({})
                            queued[len(queued) - 1]['name'] = current['name']
                            queued[len(queued) - 1]['artist'] = current['artist']
                            laststate = state
                            state = "playing"
                        elif pressed in ['q', 'Q']:
                            quit_(volume=volume)
                        elif pressed in ['n', 'N']:
                            quit_(volume=volume, restart=True)
                        pressed = None
                else:
                    clearline("Loading...")
                    clearline()
                    clearline()
            else:
                clearline("Loading...")
                clearline()
                clearline()
        elif state == "results-album":
            if results_run:
                clearline(f"PAGE {page}")
                _i = 1
                for album in results_run:
                    if _i > ((page - 1) * 5) and _i < ((page * 5) + 1):
                        clearline(f"{_i - ((page - 1) * 5)}. {album['name']} (Artist: {album['artist']})")
                    _i += 1
                availables = {
                    "a": page > 1,
                    "d": len(results_run) > (page * 5)
                }
                if pressed and active:
                    if pressed in ['a', 'A']:
                        page = max(1, page - 1)
                    elif pressed in ['d', 'D']:
                        if availables['d']:
                            page += 1
                            erase()
                            results_run = results(intext, "albums", page * 5)
                    elif pressed in nums:
                        erase()
                        index = ((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)
                        salbum = session.get(f"https://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={os.getenv('LASTFM_API')}&artist={quote(results_run[index]['artist'])}&album={quote(results_run[index]['name'])}&format=json").json()['album']
                        laststate = state
                        state = "album"
                        add_recent("l", salbum["name"], salbum["artist"])
                        page = 1
                    elif pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
                        page = 1
                    elif pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    pressed = None
                clearline()
                if availables['a'] or availables['d']:
                    clearline(f"{'[A] Previous ' if availables['a'] else ''}{'[D] Next' if availables['d'] else ''}")
                clearline("[1-5] Select [Q] Exit")
                clearline("[B] Back     [N] Exit & Restart")
            else:
                clearline("Album not found.")
                clearline("[B] Back")
                if pressed and active:
                    if pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
        elif state == "album":
            try:
                tracks = salbum['tracks']['track']
                clearline(f"ALBUM: {salbum['name']} by {salbum['artist']}")
                clearline(f"PAGE {page}")
                j = 1
                for track in tracks:
                    if j > ((page - 1) * 5) and j < ((page * 5) + 1):
                        clearline(f"{j - ((page - 1) * 5)}. {track['name']} by {track['artist']['name']}")
                    j += 1
                availables = {
                    "d": len(tracks) > (page * 5),
                    "a": page > 1
                }
                if pressed and active:
                    if pressed in ['d', 'D']:
                        if availables['d']:
                            page += 1
                    elif pressed in ['a', 'A']:
                        if availables['a']:
                            page -= 1
                    elif pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    elif pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
                        intext = ""
                        cursor = 0
                    elif pressed in ['p', 'P']:
                        clearline("Loading...")
                        nowplaying['name'] = tracks[0]['name']
                        nowplaying['artist'] = tracks[0]['artist']['name']
                        load_song(tracks[0]['name'], tracks[0]['artist']['name'])
                        play_song(tracks[0]['name'], player)
                        nowplaying['length'] = current['length']
                        erase()
                        laststate = state
                        state = "playing"
                        page = 1
                        for j, track in enumerate(tracks):
                            if j > 0:
                                queued.append({
                                    "name": track['name'],
                                    "artist": track['artist']['name']
                                })
                    elif pressed in ['s', 'S']:
                        clearline("Loading...")
                        popped = tracks.pop(random.randint(0, len(tracks) - 1))
                        nowplaying['name'] = popped['name']
                        nowplaying['artist'] = popped['artist']['name']
                        load_song(nowplaying['name'], nowplaying['artist'])
                        play_song(nowplaying['name'], player)
                        nowplaying['length'] = current['length']
                        erase()
                        laststate = state
                        state = "playing"
                        page = 1
                        for j in range(len(tracks)):
                            popped = tracks.pop(random.randint(0, len(tracks) - 1))
                            queued.append({
                                "name": popped['name'],
                                "artist": popped['artist']['name']
                            })
                    elif pressed in nums:
                        cho = tracks[((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)]
                        threading.Thread(target=load_song, args=(cho['name'], cho['artist']['name']))
                        erase()
                        laststate = state
                        state = "songstate"
                clearline("[1-5] Select song    [S] Play shuffled")
                clearline("[P] Play full album  [B] Back")
                clearline("[Q] Exit             [N] Exit & Relaunch")
            except:
                clearline("This album is empty.")
                clearline("[Q] Exit [N] Exit & Relaunch")
                clearline("[B] Back")
                if pressed and active:
                    if pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    elif pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
        elif state == "results-artist":
            if results_run:
                clearline(f"PAGE {page}")
                _i = 1
                for artist in results_run:
                    if _i > ((page - 1) * 5) and _i < ((page * 5) + 1):
                        clearline(f"{_i - ((page - 1) * 5)}. {artist['name']}")
                    _i += 1
                availables = {
                    "a": page > 1,
                    "d": len(results_run) > (page * 5)
                }
                if pressed and active:
                    if pressed in ['a', 'A']:
                        page = max(1, page - 1)
                    elif pressed in ['d', 'D']:
                        if availables['d']:
                            page += 1
                            erase()
                            if len(results_run) < (page + 1) * 5:
                                results_run = results(intext, "artists", page * 5)
                    elif pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
                        page = 1
                    elif pressed in ['q', 'Q']:
                        quit_(volume=volume)
                    elif pressed in ['n', 'N']:
                        quit_(volume=volume, restart=True)
                    elif pressed in nums:
                        erase()
                        index = ((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)
                        stop = session.get(
                            f"https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&api_key=dabde6a332fadc456b8882d0d6fb0529&artist={quote(results_run[index]['name'])}&format=json&limit=10"
                        ).json()['toptracks']
                        sartist = {
                            "name": results_run[index]['name'],
                            "tops": stop['track'],
                            "total": int(stop['@attr']['total'])
                        }
                        add_recent("a", sartist['name'])
                        laststate = state
                        state = "artist"
                        page = 1
                    pressed = None
                clearline()
                if availables['a'] or availables['d']:
                    clearline(f"{'[A] Previous ' if availables['a'] else ''}{'[D] Next' if availables['d'] else ''}")
                clearline("[1-5] Select [Q] Exit")
                clearline("[B] Back     [N] Exit & Restart")
            else:
                clearline("Artist not found.")
                clearline("[B] Back")
                if pressed and active:
                    if pressed in ['b', 'B']:
                        erase()
                        laststate = state
                        state = "home"
        elif state == "artist":
            clearline(f"Top tracks of {sartist['name']}:")
            clearline(f"PAGE {page} (out of {math.ceil(sartist['total'] / 10)} pages total)")
            _i = 1
            availables = {
                "a": page > 1,
                "d": sartist['total'] > (page * 5)
            }
            for track in sartist['tops']:
                if _i > ((page - 1) * 10) and _i < (page * 10) + 1:
                    clearline(f"{(_i - ((page - 1) * 10)) - 1}. {track['name']} (Playcount: {track['playcount']})")
                _i += 1
            if pressed and active:
                if pressed in ['n', 'N']:
                    quit_(volume=volume, restart=True)
                elif pressed in ['q', 'Q']:
                    quit_(volume=volume)
                elif pressed in ['d', 'D']:
                    if availables['d']:
                        if not len(sartist['tops']) > (page * 10) + 1:
                            stop = session.get(
                                f"https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&api_key=dabde6a332fadc456b8882d0d6fb0529&artist={quote(sartist['name'])}&format=json&limit={(page + 1) * 10}"
                            ).json()['toptracks']
                            sartist = {
                                "name": sartist['name'],
                                "tops": stop['track'],
                                "total": int(stop['@attr']['total'])
                            }
                        page += 1
                elif pressed in ['a', 'A']:
                    if availables['a']:
                        page -= 1
                elif pressed in ['b', 'B']:
                    erase()
                    laststate = state
                    state = "home"
                elif pressed in ['p', 'P', 's', 'S']:
                    clearline("Loading...")
                    stop = session.get(
                        f"https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&api_key=dabde6a332fadc456b8882d0d6fb0529&artist={quote(sartist['name'])}&format=json&limit=35"
                    ).json()['toptracks']['track']
                    if pressed in ['s', 'S']:
                        random.shuffle(stop)
                    plad = False
                    for track in stop:
                        if not plad:
                            load_song(track['name'], track['artist']['name'])
                            plad = True
                        else:
                            queued.append({})
                            queued[-1]['name'] = track['name']
                            queued[-1]['artist'] = track['artist']['name']
                    erase()
                    play_song(stop[0]['name'], player)
                    nowplaying = current.copy()
                    laststate = state
                    state = "playing"
                elif pressed in exnums:
                    clearline("Loading...")
                    index = ((page - 1) * 5) + int("".join(c for c in pressed if c.isdigit()))
                    load_song(sartist['tops'][index]['name'], sartist['tops'][index]['artist']['name'])
                    erase()
                    laststate = state
                    state = "songstate"
                pressed = None
            if availables['d'] or availables['a']:
                clearline(f"{'[A] Previous ' if availables['a'] else ''}{'[D] Next' if availables ['d'] else ''}")
            clearline("[Q] Exit    [N] Exit & Relaunch")
            clearline("[B] Back    [P] Play (In order of playcount)")
            clearline("[S] Play (Shuffled)")

def setup():
    global events, user32, active_window, ydl, last_active, pressed, held
    pressed = None
    held = set()
    events = []
    print("\033[?25l", end="")
    ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "windowsfilenames": True,
    }
    user32 = ctypes.windll.user32
    user32.SetForegroundWindow(user32.FindWindowW(None, "songzplayer"))
    active_window = user32.GetForegroundWindow()
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    last_active = False
    keyboard.on_press(keying)
    keyboard.on_release(unkeying)
    UI()
# endregion

# region Start
dotenv.load_dotenv("secrets.env")
if __name__ == "__main__":
    init()
    session = Session()
    st = requests.post(
        "https://songz.ashmit.hackclub.app/admin/stats",
        json={"token": get_config("ssk")}
    ).json()["Status"]
    if st == "Expired" or st == "Nonexistent":
        print("Please log in")
        for i in range(3):
            print("Username: ", end="")
            us = input()
            print("Password: ", end="")
            pw = input()
            ssk = requests.post(
                "https://songz.ashmit.hackclub.app/login",
                json={"username": us, "password": pw}
            )
            if ssk.status_code == 401:
                if i != 3:
                    print("Password and/or username incorrect. Please try again.")
                else:
                    print("Too many incorrect attempts. Exiting...")
                    os.system(f'cd /d "{sys.argv[1]}"')
                    exit(0)
            else:
                ssk = ssk.json()
                save_config("ssk", ssk["session_key"])
                break
    queued: list[dict] = []
    setup()
    held = set()
# endregion
