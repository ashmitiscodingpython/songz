import math
import requests
import argparse
import yt_dlp
import json
import mutagen
import threading
from urllib.parse import quote
import keyboard
import time
import os
import re
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import ctypes

def get_times(milliseconds: int):
    minutes = math.floor(milliseconds / 60000)
    seconds = math.floor((milliseconds - (minutes * 60000)) / 1000)
    return [minutes, seconds, milliseconds]

def clearline(text="", end=""):
    print(f"\r{text:80}\r{end}", end="")

def suggestions(data_):
    similar = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={quote(data_['artist'])}&track={quote(data_['name'])}&api_key=483f6442563f932e2b116e1c83d316af&format=json&limit=5").json()['similartracks']['track']
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
            print(f"Preparing to play '{data_['name']}' by {data_['artist']}.")
            response_ = ydl.extract_info(f"ytsearch:{data_['name']} {data_['artist']}", download=False)['entries'][0]
            url = response_['original_url']
            if not check(camelcase(data_['name'])):
                print(f"Downloading {data_['name']}...")
                download(url, camelcase(data_['name']), data_['artist'])
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

def mainloop(infinity: bool):
    global playing, current_artist, paused, held, volume, current_length, last_active, active_window, user32
    data_ = load_song(playing, False, details=True)
    similar = None
    if infinity and current_artist:
        similar = suggestions(data_)
    nextchoose = None
    while playing is not None:
        active = user32.GetForegroundWindow() == active_window
        songs = get_times(current_length)
        currents = get_times(pygame.mixer.music.get_pos())
        lefts = get_times(songs[2] - currents[2])
        if last_active != active:
            if active:
                keyboard.block_key('w')
                keyboard.block_key('s')
                keyboard.block_key('a')
                keyboard.block_key('d')
                keyboard.block_key('e')
                keyboard.block_key('q')
                for i in range(5):
                    keyboard.block_key(f"{i + 1}")
                    keyboard.block_key(f"num {i + 1}")
            else:
                keyboard.unhook_all()
            last_active = active
        if active:
            if keyboard.is_pressed("w"):
                clearline(f"Volume: {round(volume * 100)}%")
                volume = min(1.0, volume + 0.01)
                time.sleep(0.05)
            elif keyboard.is_pressed("s"):
                clearline(f"Volume: {round(volume * 100)}%")
                volume = max(0.0, volume - 0.01)
                time.sleep(0.05)
            else:
                if not paused:
                    curpos = round((currents[2] / songs[2]) * 25)
                    clearline(f"{currents[0]}:{currents[1]:0>2} {'─' * curpos}●{'─' * (25 - curpos)} {songs[0]}:{songs[1]:0>2} (-{lefts[0]}:{lefts[1]:0>2})")
                else:
                    clearline("Paused")
            if keyboard.is_pressed("q"):
                clearline("Exiting...")
                pygame.mixer.music.stop()
                break
            pause_held = keyboard.is_pressed("e")
            numkeys = [keyboard.is_pressed(key) for key in ([f"{i+1}" for i in range(5)] + [f"num {j + 1}" for j in range(5)])]
            if any(numkeys) and infinity and not nextchoose:
                nextchoose = similar[(numkeys.index(True) % 5)]
                clearline(f"Next playing: {nextchoose['name']} by {nextchoose['artist']['name']}", end='\n')
                threading.Thread(target=load_song, args=(nextchoose['name'], False, True, False)).start()
            if (lefts[2] / 1000) < 21 and not nextchoose and infinity:
                nextchoose = sorted(similar, key=lambda k: k['playcount'])[-1]
                clearline(f"Next playing: {nextchoose['name']} by {nextchoose['artist']['name']} (chosen by highest playcount)", end="\n")
                threading.Thread(target=load_song, args=(nextchoose['name'], False, True, False)).start()
            if lefts[2] < 500 and infinity:
                os.system("cls")
                current_artist = nextchoose['artist']['name']
                playing = nextchoose['name']
                print(f"Now playing: {playing} by {current_artist}")
                suggestions({'name': playing, 'artist': current_artist})
                nextchoose = None
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                play_song(playing)
            if lefts[2] < 100 and not infinity:
                pygame.mixer.music.stop()
                break
            if pause_held and not held:
                paused = not paused
                held = True
                if paused:
                    clearline("Paused")
                    pygame.mixer.music.pause()
                else:
                    clearline()
                    pygame.mixer.music.unpause()
            elif not pause_held:
                held = False
        pygame.mixer.music.set_volume(volume)

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

pygame.mixer.init()
last_active = False
user32 = ctypes.windll.user32
active_window = user32.GetForegroundWindow()
ydl_opts = {
    "logger": SilentLogger(),
    "quiet": True,
    "no_warnings": True,
    "format": "bestaudio/best",
    "windowsfilenames": True,
}
ydl = yt_dlp.YoutubeDL(ydl_opts)
parser = argparse.ArgumentParser()
subparser = parser.add_subparsers(dest="command")
player = subparser.add_parser("play", help="Play a song.")
player.add_argument("song", help="The song to play.", type=str)
player.add_argument("-i", "--infinite", help="Autoplay similar songs.", action="store_true")
player.add_argument("-t", "--top", help="Select the top match without displaying options", action="store_true")
player.add_argument("-s", "--search")
current_artist = None
args = parser.parse_args()
queue = []
playing = None
paused = False
held = False
volume = 0.5
current_length = 0
if args.command == "play":
    os.system("cls")
    data = load_song(args.song, True, args.top)
    play_song(data['name'])
    print(f"Now playing: {data['name']} by {data['artist']}")
    playing = data['name']
    current_artist = data['artist']
    mainloop(args.infinite)
