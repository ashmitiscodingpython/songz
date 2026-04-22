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

init(autoreset=True)

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
def get_millis():
    return (time.perf_counter() - start) * 1000
def u(text):
    return f"\033[4m{text}\033[0m"
def i(text):
    return f"\033[3m{text}\033[0m"
def s(text):
    return f"\033[9m{text}\033[0m"
def clear():
    print("\033[H")
def style(text: str, foreground=None, styling=None, background=None):
    parts = []
    if foreground:
        parts.append(getattr(Fore, foreground.upper()))
    if styling:
        parts.append(getattr(Style, styling.upper()))
    if background:
        parts.append(getattr(Back, background.upper()))
    return ''.join(parts) + text
def get_times(milliseconds: int):
    minutes = math.floor(milliseconds / 60000)
    seconds = math.floor((milliseconds - (minutes * 60000)) / 1000)
    return [minutes, seconds, milliseconds]
def clearline(text="", end="\n"):
    print(f"\033[2K\r{text}", end=end)
def suggestions(name, artist):
    """
    Get suggestions for a track.

    :returns: Name as ['name'], artist as ['artist']['name'] and playcount as ['playcount'].
    """
    similar = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={quote(artist)}&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&format=json&limit=5").json()['similartracks']['track']
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
def load_song(name, artist=None, play=False):
    global current
    current = {
        "name": name,
        "artist": artist
    }
    response_ = ydl.extract_info(f"ytsearch:{name} {artist if artist else ''} topic lyrics", download=False)['entries'][0]
    url = response_['original_url']
    if not check(camelcase(name)):
        download(url, camelcase(name), artist)
    if play:
        play_song(camelcase(name))
    return {"name": name, "artist": artist}
def play_song(title_):
    global current_length, current, player
    titl = camelcase(title_)
    current_length = mutagen.File(f"SONGS/{titl}.ogg").info.length * 1000
    current['length'] = current_length
    player.set_media(vlc.Media(f"SONGS/{titl}.ogg"))
    player.play()
def download(urls, name, artist):
    _ydl_opts = {
        "logger": SilentLogger(),
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": f"SONGS/{camelcase(name)}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "ogg",
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
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def UI():
    global pheld, volume, events, user32, active_window, last_active, pressed, main, state, queued
    intext = ""
    cursor = 0
    pheld = False
    paused = False
    os.system("cls")
    ctrl = False
    page = 1
    results_run = None
    nums = ['1', '2', '3', '4', '5', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5']
    while True:
        active = user32.GetForegroundWindow() == active_window
        if not active:
            pressed = None
        _, height = shutil.get_terminal_size()
        clear()
        if state == 'home':
            clearline(f"Search: {uat(intext + ' ', (cursor + (0 if cursor == len(intext) else -1)))}", end=f'\n\n')
            if pressed and active:
                st = "abcdefghijklmnopqrstuvwxyz"
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
                if pressed == "ctrl":
                    ctrl = True
                pressed = None
            clearline("[Enter] Search    [Ctrl+Q] Exit")
            clearline("[1-5] Open recent [Ctrl+N] Exit & Relaunch", end='')
        elif state == 'search':
            clearline(f"Search: {intext}")
            clearline("[A] Artists [S] Songs [L] Albums")
            clearline("[B] Back    [Q] Exit  [Y] Search YouTube")
            clearline("[N] Exit & Relaunch")
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
                        threading.Thread(target=load_song, args=(intext, get_saved_artist(camelcase(intext)), False)).start()
                    else:
                        state = "results-song"
                        results_run = results(intext)
                    page = 1
                if pressed in ['l', 'L']:
                    erase()
                    state = "results-album"
                    page = 1
                if pressed in ['y', 'Y']:
                    erase()
                    state = "youtube-results"
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
                        threading.Thread(target=load_song, args=(results_run[index]['name'], results_run[index]['artist'], False)).start()
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
                        threading.Thread(target=load_song, args=(intext, None, False)).start()
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
            clearline(f"Selected song: {current['name']} by {current['artist']}")
            clearline("[P] Play [B] Back [U] Add to queue")
            clearline("[Q] Exit [N] Exit & Restart")
            if pressed and active:
                if pressed in ['p', 'P']:
                    erase()
                    play_song(current['name'])
                    state = "playing"
                    page = 1
                elif pressed in ['b', 'B']:
                    erase()
                    state = 'results-song'
                elif pressed in ['u', 'U']:
                    queued.append({})
                    queued[len(queued) - 1]['name'] = current['name']
                    queued[len(queued) - 1]['artist'] = current['artist']
                elif pressed in ['q', 'Q']:
                    quit_()
                elif pressed in ['n', 'N']:
                    quit_(True)
                pressed = None
        elif state == 'playing':
            songs = get_times(current['length'])
            curs = get_times(player.get_time())
            lefts = get_times(songs[2] - curs[2])
            curpos = round(curs[2] / songs[2] * 25)
            clearline(f"{curs[0]}:{curs[1]:02} {'─' * curpos}●{'─' * (25 - curpos)} {songs[0]}:{songs[1]:02} (-{lefts[0]}:{lefts[1]:02})")
            clearline(f"Playing: {current['name']} by {current['artist']}")
            if pressed and active:
                if pressed in ['e', 'E']:
                    if not pheld:
                        paused = not paused
                        player.pause()
                    pheld = True
                if pressed in ['q', 'Q']:
                    quit_()
                elif pressed in ['n', 'N']:
                    quit_(True)
                elif pressed in ['a', 'A'] and not paused:
                    clearline("◁◁ 10 seconds")
                    player.set_time(player.get_time() - 10000)
                elif pressed in ['d', 'D'] and not paused:
                    clearline("▷▷ 10 seconds")
                    player.set_time(player.get_time() + 10000)
                pressed = None
            else:
                pheld = False
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
            clearline("[E] Pause    [A] Rewind  [D] Fast-Forward")
            clearline("[W] +Volume  [S] -Volume [Q] Exit")
            clearline("[N] Exit & Restart       [R] Recommendations")
            clearline()
            clearline()
            clearline()
            player.audio_set_volume(volume)

def setup():
    global events, user32, active_window, ydl, last_active, current, volume, state, pressed, held
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
    current = {
        "name": None,
        "artist": None,
        "length": 0
    }
    volume = 50
    state = "home"  # home, search, album, artist, playing, results-album, results-artist, results-song, youtube-results
    keyboard.on_press(keying)
    keyboard.on_release(unkeying)
    UI()

if __name__ == "__main__":
    print("Loading...")
    current = {
        "name": None,
        "artist": None
    }
    queued: list[dict] = []
    setup()
    held = set()
    player = vlc.MediaPlayer()
    start = time.perf_counter()
