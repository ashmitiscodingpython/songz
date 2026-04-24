import math
import requests
import subprocess
import yt_dlp
import json
import mutagen
import threading
from urllib.parse import quote
import keyboard
import time
import os
import re
from colorama import init, Fore, Back, Style
import ctypes
import shutil
import vlc
import sys
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

init()


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
    return max(minimum, (max(num, maximum)))
def keying(e):
    global pressed, held, events
    pressed = e.name
    held.add(e.name)
def unkeying(e):
    global held
    e.suppress = True
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
    similar = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={quote(artist)}&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&format=json&limit={limit + 1}").json()['similartracks']['track']
    return similar
def camelcase(text):
    sofar = ""
    returning = ""
    for letter in text:
        if letter not in list("<>:\"/\\|?*' "):
            sofar += letter
        else:
            if len(sofar) > 1:
                returning += sofar[0].upper() + sofar[1:].lower() + " "
            sofar = ""
    if len(sofar) > 1:
        returning += sofar[0].upper() + sofar[1:].lower()
    else:
        returning = returning[:-1]
    return re.sub(r'[<>:"/\\|?*]', "", returning)
def results(name, mode="songs", limit=5):
    if mode == "songs":
        _ = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&limit={limit + 1}&format=json").json()
        response_ = _['results']['trackmatches']['track']
        if response_:
            return response_
        else:
            return False
    elif mode == "albums":
        _ = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=album.search&album={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&limit={limit + 1}&format=json").json()
        response_ = _['results']['albummatches']['album']
        if response_:
            return response_
        else:
            return False
    return None
def load_song(name, artist=None):
    global current
    if not check(camelcase(name)):
        response_ = \
            ydl.extract_info(f"ytsearch:{name} {artist if artist else ''} topic lyrics", download=False)['entries'][0]
        url = response_['original_url']
        download(url, camelcase(name), artist)
    current["name"] = name
    current["artist"] = artist
    return {"name": name, "artist": artist}
def play_song(title_, player_):
    global current_length, current
    titl = camelcase(title_)
    current_length = mutagen.File(f"SONGS/{titl}.mp3").info.length * 1000
    current['length'] = current_length
    player_.stop()
    player_.set_media(vlc.Media(f"SONGS/{titl}.mp3"))
    player_.play()
def download(urls, name, artist):
    #    "progress_hooks": [download_progress],
    #    "progress_delta": 0.01,
    _ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": f"SONGS/{camelcase(name)}.%(ext)s",
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
        data_ = json.load(file)
    except:
        open("config.json", 'x').close()
        data_ = {'songs': [], 'artists': []}
    data_["songs"].append(name)
    data_["artists"].append(artist)
    with open("config.json", "w") as dumpee:
        json.dump(data_, dumpee, indent=4)
def check(name):
    try:
        file = open("config.json")
    except:
        return False
    data_ = json.load(file)
    return name in data_["songs"]
def quit_(restart=False):
    os.system("cls")
    if not restart:
        print("\033[?25h", end='')
    else:
        os.system(
            f'start cmd /k "title Command Prompt && echo {subprocess.check_output("ver", shell=True).decode().strip()} && echo ^(c^) Microsoft Corporation. All rights reserved. && cd /d \"{sys.argv[1]}\""'
        )
    exit(0)
def get_saved_artist(song):
    try:
        file = open("config.json")
    except:
        return None
    data_ = json.load(file)
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
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def UI():
    global current, events, user32, active_window, last_active, pressed, main, queued, lefts
    intext = ""
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
    salbum = {
        "name": None,
        "artist": None
    }
    current = {
        "name": None,
        "artist": None,
        "length": 0
    }
    state = "home"
    nowplaying = {
        "name": None,
        "artist": None
    }
    nums = ['1', '2', '3', '4', '5', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5']
    while True:
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
                    state = "search"
                    erase()
                if pressed == "left":
                    cursor -= 1
                    cursor = clamp(cursor, 0, len(intext))
                if pressed == "right":
                    cursor += 1
                    cursor = clamp(cursor, 0, len(intext))
                if pressed in ['q', 'Q'] and ctrl:
                    quit_()
                if pressed in ['n', 'N'] and ctrl:
                    quit_(True)
                if pressed in ['b', 'B'] and ctrl and nowplaying['name']:
                    erase()
                    temphome = False
                    state = "playing"
                if pressed == "ctrl":
                    ctrl = True
                pressed = None
            clearline("[Enter] Search           [Ctrl+Q] Exit")
            clearline("[Ctrl+(1-5)] Open recent [Ctrl+N] Exit & Relaunch")
            if nowplaying['name']:
                clearline("[Ctrl+B] Back")
        elif state == 'search':
            clearline(f"Search: {intext}")
            clearline("[A] Artists [S] Songs [L] Albums")
            clearline("[B] Back    [Q] Exit  [N] Exit & Relaunch")
            if pressed and active:
                if pressed in ["q", "Q"]:
                    quit_()
                if pressed in ["n", "N"]:
                    quit_(True)
                if pressed in ['b', 'B']:
                    erase()
                    state = "home"
                if pressed in ['a', "A"]:
                    erase()
                    state = "results-artist"
                    page = 1
                if pressed in ['s', 'S']:
                    erase()
                    if check(camelcase(intext)):
                        state = "songstate"
                        erase()
                        threading.Thread(target=load_song, args=(intext, get_saved_artist(camelcase(intext)))).start()
                    else:
                        state = "results-song"
                        results_run = results(intext)
                    page = 1
                if pressed in ['l', 'L']:
                    erase()
                    results_run = results(intext, mode="albums")
                    state = "results-album"
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
                        quit_()
                    elif pressed in ['n', 'N']:
                        quit_(True)
                    elif pressed in ['d', 'D'] and availables['d']:
                        page += 1
                        erase()
                        results_run = results(intext, limit=(page * 5))
                    elif pressed in ['a', 'A'] and availables['a']:
                        page -= 1
                        erase()
                        results_run = results(intext, limit=(page * 5))
                    elif pressed in ['b', 'B']:
                        erase()
                        state = 'home'
                        intext = ''
                        cursor = 0
                    elif pressed in nums:
                        index = ((page - 1) * 5) + (int("".join(c for c in pressed if c.isdigit())) - 1)
                        erase()
                        threading.Thread(target=load_song, args=(results_run[index]['name'], results_run[index]['artist'])).start()
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
                        state = "songstate"
                    elif pressed in ['b', 'B']:
                        clear()
                        intext = ""
                        cursor = 0
                        state = "home"
                    elif pressed in ['q', 'Q']:
                        quit_()
                    elif pressed in ['n', 'N']:
                        quit_(True)
                    pressed = None
        elif state == 'songstate':
            if current['name']:
                if check(camelcase(current['name'])):
                    clearline(f"Selected song: {current['name']} by {current['artist']}")
                    clearline(f"[P] Play [B] Back {'[U] Add to queue' if nowplaying['name'] else ''}")
                    clearline("[Q] Exit [N] Exit & Relaunch")
                    if pressed and active:
                        if pressed in ['p', 'P']:
                            erase()
                            play_song(current['name'], player)
                            nowplaying = current.copy()
                            state = "playing"
                            page = 1
                        elif pressed in ['b', 'B']:
                            erase()
                            state = 'results-song'
                        elif pressed in ['u', 'U'] and nowplaying['name']:
                            erase()
                            queued.append({})
                            queued[len(queued) - 1]['name'] = current['name']
                            queued[len(queued) - 1]['artist'] = current['artist']
                            state = "playing"
                        elif pressed in ['q', 'Q']:
                            quit_()
                        elif pressed in ['n', 'N']:
                            quit_(True)
                        pressed = None
                else:
                    clearline("Loading...")
                    clearline()
                    clearline()
            else:
                clearline("Loading...")
                clearline()
                clearline()
        elif state == 'playing' or temphome:
            try:
                if nowplaying['length']:
                    songs = get_times(nowplaying['length'])
                    curs = get_times(player.get_time())
                    lefts = get_times(songs[2] - curs[2])
                    curpos = round(curs[2] / songs[2] * 25)
                    clearline(f"{curs[0]}:{curs[1]:02} {'─' * curpos}●{'─' * (25 - curpos)} {songs[0]}:{songs[1]:02} (-{lefts[0]}:{lefts[1]:02})")
            except:
                clearline("Loading...")
            clearline(f"Playing: {nowplaying['name']} {'by' if nowplaying['artist'] else ''} {nowplaying['artist'] if nowplaying['artist'] else ''}")
            if pressed and active and state == "playing":
                if pressed in ['e', 'E']:
                    if not pheld:
                        paused = not paused
                        player.pause()
                    pheld = True
                elif pressed in ['q', 'Q']:
                    quit_()
                elif pressed in ['n', 'N']:
                    quit_(True)
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
                    if not recommendation and not chosen and nowplaying['artist']:
                        recommendation = suggestions(nowplaying['name'], nowplaying['artist'], 5)
                elif pressed in ['z', 'Z']:
                    if recommendation and not chosen:
                        page = max(1, page - 1)
                elif pressed in ['x', 'X']:
                    if recommendation and not chosen and len(recommendation) > (page * 5):
                        page += 1
                        erase()
                        recommendation = suggestions(nowplaying['name'], nowplaying['artist'], page * 5)
                elif pressed in ['h', 'H']:
                    erase()
                    intext = ""
                    cursor = 0
                    state = "home"
                elif pressed in nums:
                    if recommendation and not chosen:
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
            if len(queued) > 0:
                clearline(f"Next in queue: {queued[0]['name']} by {queued[0]['artist']}")
                if lefts[2] < 20000 and not ql:
                    ql = True
                    load_song(queued[0]['name'], queued[0]['artist'])
                if lefts[2] < 1000:
                    play_song(queued[0]['name'], player)
                    recommendation = False
                    chosen = False
                    ql = False
                    nowplaying = current.copy()
                    queued.pop(0)
            if recommendation and not chosen:
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
            if keyboard.is_pressed("w") and active:
                volume = min(100, volume + 1)
                clearline(f"Volume: {volume}%")
                time.sleep(0.05)
            elif keyboard.is_pressed("s") and active:
                volume = max(0, volume - 1)
                clearline(f"Volume: {volume}%")
                time.sleep(0.05)
            if paused:
                clearline("PAUSED")
            if recommendation is not False and not recommendation:
                rhide = True
                clearline(style("This track doesn't have similar tracks.", "LIGHTMAGENTA_EX", "BRIGHT"))
            if recommendation and not chosen:
                clearline(style("[1-5] Add to Queue", "LIGHTMAGENTA_EX", "BRIGHT"))
                clearline(f"{style('[Z] Previous [X] Next    [C] Close', 'LIGHTMAGENTA_EX', 'BRIGHT')}")
            else:
                clearline("[H] Home")
            clearline("[E] Pause    [A] Rewind  [D] Fast-Forward")
            clearline("[W] +Volume  [S] -Volume [Q] Exit")
            clearline(f"[N] Exit & Relaunch      {'[R] Recommendations' if nowplaying['artist'] and not recommendation else '[H] Home'}")
            clearline()
            clearline()
            clearline()
            player.audio_set_volume(volume)
        elif state == "results-album":
            if results_run:
                clearline(f"PAGE {page}")
                _i = 1
                for album in results_run:
                    if _i > ((page - 1) * 5) and _i < ((page * 5) + 1):
                        clearline(f"{_i}. {album['name']} (Artist: {album['artist']})")
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
                        salbum['name'] = results_run[index]['name']
                        salbum['artist'] = results_run[index]['artist']
                        state = "album"
                        page = 1
                    elif pressed in ['b', 'B']:
                        erase()
                        state = "home"
                        page = 1
                    elif pressed in ['q', 'Q']:
                        quit_()
                    elif pressed in ['n', 'N']:
                        quit_(True)
                    pressed = None
                clearline()
                if availables['a'] or availables['d']:
                    clearline(f"{'[A] Previous ' if availables['a'] else ''}{'[D] Next' if availables['d'] else ''}")
                clearline("[1-5] Select [Q] Exit")
                clearline("[B] Back     [N] Exit & Restart")
            else:
                clearline("Album not found.")

def setup():
    global events, user32, active_window, ydl, last_active, pressed, held
    pressed = None
    held = set()
    events = []
    print("\033[?25l", end="")
    pygame.mixer.init()
    ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "windowsfilenames": True,
    }
    user32 = ctypes.windll.user32
    active_window = user32.GetForegroundWindow()
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    last_active = False
    # home, search, album, artist, playing, results-album, results-artist, results-song
    keyboard.on_press(keying)
    keyboard.on_release(unkeying)
    UI()

if __name__ == "__main__":
    print("Loading...")
    queued: list[dict] = []
    setup()
    held = set()
