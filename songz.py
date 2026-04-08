import requests
import argparse
import yt_dlp
import json
import subprocess
from pydub import AudioSegment
import pygame
import keyboard
import time

def load_song(name, starting: bool, top):
    if starting:
        print("Loading...")
        response = requests.get(
            f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={name}&api_key=483f6442563f932e2b116e1c83d316af&limit=5&format=json").json()[
            'results']['trackmatches']['track']
        if not top:
            i = 1
            for track in response:
                print(f"{i}. '{track['name']}' by {track['artist']}")
                i += 1
            num = int(input("Play which track?: ")) - 1
        else:
            num = 0
        data = response[num]
        print(f"Preparing to play '{data['name']}' by {data['artist']}.")
        response = ydl.extract_info(f"ytsearch:{data['name']} {data['artist']}", download=False)['entries'][0]
        url = response['original_url']
        title = response['title']
        if not check(title):
            print("Downloading song...")
            download(url, title)
        return data, response
    else:
        return None

def mainloop(infinity):
    global paused, held, volume
    while playing is not None:
        if keyboard.is_pressed("w"):
            print(f"\rVolume: {round(volume * 100)}%", end='')
            volume = min(1.0, volume + 0.01)
            time.sleep(0.05)
        elif keyboard.is_pressed("s"):
            print(f"\rVolume: {round(volume * 100)}%", end='')
            volume = max(0.0, volume - 0.01)
            time.sleep(0.05)
        else:
            if not paused:
                print("\r                      ", end='')
            else:
                print("\rPaused", end='')
        if keyboard.is_pressed("q"):
            print("\rExiting...")
            pygame.mixer.music.stop()
            break
        if keyboard.is_pressed("e"):
            paused = not paused
            if paused:
                print("\rPaused", end='')
                pygame.mixer.music.pause()
            else:
                print("\r                      ", end="")
                pygame.mixer.music.unpause()
        pygame.mixer.music.set_volume(volume)

def download(urls, name):
    ydl.download([urls])
    add_song(name)
    subprocess.run(["cmd", "/c", "rename", f"{name} [{response['id']}].webm", f"{name}.webm"])
    subprocess.run(["cmd", "/c", "move", f'{name}.webm', "SONGS\\", ">nul"])

def add_song(name):
    try:
        file = open("config.json", 'r')
        data_ = json.load(file)
    except:
        file = open("config.json", 'x')
        data_ = {'songs': []}
    data_["songs"].append(name)
    with open("config.json", "w") as dumpee:
        json.dump(data_, dumpee)

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
ydl_opts = {
    "logger": SilentLogger(),
    "quiet": True,
    "no_warnings": True,
    "format": "bestaudio/best",
}
ydl = yt_dlp.YoutubeDL(ydl_opts)
parser = argparse.ArgumentParser()
subparser = parser.add_subparsers(dest="command")
player = subparser.add_parser("play", help="Play a song.")
player.add_argument("song", help="The song to play.", type=str)
player.add_argument("-i", "--infinite", help="Autoplay similar songs.", action="store_true")
player.add_argument("-t", "--top", help="Select the top match without displaying options", action="store_true")
args = parser.parse_args()
queue = []
playing = None
paused = False
held = False
volume = 0.5
if args.command == "play":
    data, response = load_song(args.song, True, args.top)
    title = response['title']
    song = AudioSegment.from_file(f"SONGS/{title}.webm")
    song.export("song.mp3", format="mp3")
    pygame.mixer.music.load("song.mp3")
    pygame.mixer.music.play()
    print(f"Playing '{data['name']}' by {data['artist']} now.")
    playing = title
    mainloop(args.infinite)
