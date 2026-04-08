import requests
import argparse
import yt_dlp

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

ydl_opts = {
    "logger": SilentLogger(),
    "quiet": True,
    "no_warnings": True,
}
ydl = yt_dlp.YoutubeDL(ydl_opts)
parser = argparse.ArgumentParser()
subparser = parser.add_subparsers(dest="command")
play = subparser.add_parser("play", help="Play a song.")
play.add_argument("song", help="The song to play.", type=str)
play.add_argument("-i", "--infinite", help="Autoplay similar songs.", action="store_true")
play.add_argument("-t", "--top", help="Select the top match without displaying options", action="store_true")
args = parser.parse_args()
if args.command == "play":
    print("Loading...")
    response = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={args.song}&api_key=483f6442563f932e2b116e1c83d316af&limit=5&format=json").json()['results']['trackmatches']['track']
    if not args.top:
        i = 1
        for track in response:
            print(f"{i}. '{track['name']}' by {track['artist']}")
            i += 1
        num = int(input("Play which track?: ")) - 1
    else:
        num = 0
    data = response[num]
    print(f"Playing '{data['name']}' by {data['artist']}.")
    url = ydl.extract_info(f"ytsearch:{data['name']} {data['artist']}", download=False)['entries'][0]['original_url']
    
