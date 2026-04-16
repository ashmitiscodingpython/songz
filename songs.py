import math
import requests
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
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import ctypes
import shutil

init(autoreset=True)

def erase():
    clear()
    printable = ""
    for j in range(15):
        printable += (" " * 70) + "\n"
    print(printable)
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
    print(f"\r{text:80}\r{end}", end="")
def suggestions(name, artist):
    similar = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={quote(artist)}&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&format=json&limit=5").json()['similartracks']['track']
    print("Suggested tracks: (Press the number key to select a song)")
    i = 0
    for track in similar:
        i += 1
        print(f"{i}. {track['name']} by {track['artist']['name']} [Playcount: {track['playcount']}]")
    return similar
def camelcase(text):
    sofar = ""
    returning = ""
    for letter in text:
        if not letter == " ":
            sofar += letter
        else:
            returning += sofar[0].upper() + sofar[1:].lower() + " "
            sofar = ""
    returning += sofar[0].upper() + sofar[1:].lower()
    return re.sub(r'[<>:"/\\|?*]', "", returning)
def load_song(name, starting: bool, top=False, details=False):
    if starting:
        print("Loading...")
        response_ = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&limit=5&format=json").json()['results']['trackmatches']['track']
        if response_:
            if not top:
                i = 1
                for track in response_:
                    print(f"{i}. '{track['name']}' by {track['artist']}")
                    i += 1
                num = int(input("Play which track?: ")) - 1
            else:
                num = 0
            data_ = response_[num]
            name = data_['name']
            artist = data_['artist']
            print(f"Preparing to play '{name}' by {artist}.")
            response_ = ydl.extract_info(f"ytsearch:{name} {artist}", download=False)['entries'][0]
            url = response_['original_url']
            if not check(camelcase(name)):
                print(f"Downloading {name}...")
                download(url, camelcase(name), artist)
            return data_
        else:
            print("This song is not available in the database, therefore autoplay is not available")
            print(f"Preparing to play {name}")
            response_ = ydl.extract_info(f"ytsearch:{name}", download=False)['entries'][0]
            url = response_['original_url']
            if not check(camelcase(name)):
                print(f"Downloading {name}...")
                download(url, name, None)
            return {'name': name, 'artist': None}
    else:
        data_ = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={quote(name)}&api_key=483f6442563f932e2b116e1c83d316af&limit=5&format=json").json()['results']['trackmatches']['track'][0]
        if not details:
            response_ = ydl.extract_info(f"ytsearch:{data_['name']} {data_['artist']}", download=False)['entries'][0]
            url = response_['original_url']
            if not check(camelcase(data_['name'])):
                download(url, camelcase(data_['name']), data_['artist'])
        return data_
def play_song(title_):
    global current_length
    title_ = camelcase(title_)
    current_length = mutagen.File(f"SONGS/{title_}.mp3").info.length * 1000
    pygame.mixer.music.load(f"SONGS/{title_}.mp3")
    pygame.mixer.music.play()
def download(urls, name, artist):
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
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def mainloop():
    global events, user32, active_window, last_active, pressed, main, state, caps
    intext = ""
    cursor = 0
    navcool = 50
    os.system("cls")
    running = True
    caps = False
    ctrl = False
    toggled = False
    caps = False
    while running:
        active = user32.GetForegroundWindow() == active_window
        # if last_active != active:
        #     if active:
        #         hooks = list("abdefghijklmnopqrstuvwxyz123456789") + ["space", "enter"]
        #         for key in hooks:
        #             keyboard.hook()
        #     else:
        #         keyboard.unhook_all()
        #     last_active = active
        _, height = shutil.get_terminal_size()
        clear()
        if state == 'home':
            clearline(f"Search: {uat(intext + ' ', (cursor + (0 if cursor == len(intext) else -1)))}", end=f'\n{"[CAPS LOCK ON]" if caps else ""}\n')
            if pressed and active:
                st = "abcdefghijklmnopqrstuvwxyz"
                if pressed in list(st + st.upper()) + ['space']:
                    mod = pressed
                    if caps:
                        mod = mod.upper()
                    if pressed == "space":
                        mod = " "
                    intext += mod
                    if cursor == len(intext) - 1:
                        cursor += 1
                if pressed == "caps lock" and not toggled:
                    caps = not caps
                    toggled = True
                else:
                    toggled = False
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
                if pressed == "q" and ctrl:
                    os.system("cls")
                    keyboard.unhook_all()
                    keyboard.clear_all_hotkeys()
                    print(f"\033[?25h", end='')
                    exit(0)
                if pressed == "ctrl":
                    ctrl = True
                pressed = None
            clearline("[Enter] Search    [Ctrl+Q] Exit")
            clearline("[1-5] Open Recent", end='')
        elif state == 'search':
            clearline(f"Search: {intext}")
            clearline("[A] Artists [S] Songs [L] Albums")
            clearline("[B] Back    [Q] Exit")
            if pressed == "q":
                os.system("cls")
                keyboard.unhook_all()
                keyboard.clear_all_hotkeys()
                print("\033[?25h", end='')
                exit(0)


def setup():
    global events, user32, active_window, ydl, last_active, current, volume, state, pressed, held
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
    active_window = user32.GetForegroundWindow()
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    last_active = False
    current = {
        "name": None,
        "artist": None
    }
    volume = 0.5
    state = "home"  # home, results, album, artist, playing, search
    keyboard.on_press(keying, True)
    keyboard.on_release(unkeying, True)
    mainloop()

if __name__ == "__main__":
    print("Loading...")
    setup()
    held = set()
    start = time.perf_counter()
