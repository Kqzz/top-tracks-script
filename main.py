import json
import os
import requests
import spotipy
import argparse
import time
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# ANSI color codes for logging
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"

def log_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {message}")

def log_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")

def log_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def log_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")

# Load environment variables
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_KEY")
LASTFM_USER = os.getenv("LASTFM_USER")
WEEKLY_ID = os.getenv("WEEKLY_ID")
MONTHLY_ID = os.getenv("MONTHLY_ID")

# Spotify authentication
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
    log_info("Successfully authenticated with Spotify")
except Exception as e:
    log_error(f"Failed to authenticate with Spotify: {str(e)}")
    exit(1)

def get_top_songs(api_key, user, timeframe="7day", page=1, limit=100):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={user}&api_key={api_key}&period={timeframe}&page={page}&limit={limit}&format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log_error(f"Failed to fetch top songs: {str(e)}")
        return None

def put_top_songs_into_playlist(playlist_id, last_fm_user, timeframe):
    log_info(f"Updating playlist {playlist_id} with top songs for {timeframe}")
    try:
        sp.playlist_replace_items(playlist_id, [])
        log_info("Playlist cleared successfully")
    except spotipy.SpotifyException as e:
        log_error(f"Failed to clear playlist: {str(e)}")
        return

    songs = get_top_songs(LASTFM_API_KEY, last_fm_user, timeframe=timeframe, page=1, limit=50)
    if not songs:
        log_error("Failed to fetch top songs")
        return

    added_count = 0
    for song in songs["toptracks"]["track"]:
        try:
            results = sp.search(
                q=f"track:{song.get('name')} artist:{song.get('artist').get('name')}",
                type="track",
                limit=1,
            )
            if results["tracks"]["items"]:
                track_uri = results["tracks"]["items"][0]["uri"]
                sp.playlist_add_items(playlist_id, [track_uri])
                added_count += 1
            else:
                log_warning(f"Song not found: {song.get('name')} by {song.get('artist').get('name')}")
        except spotipy.SpotifyException as e:
            log_error(f"Error adding song to playlist: {str(e)}")

    log_success(f"Added {added_count} songs to playlist {playlist_id}")

def update_playlists():
    if not all([LASTFM_API_KEY, LASTFM_USER, WEEKLY_ID, MONTHLY_ID]):
        log_error("Missing required environment variables")
        return

    put_top_songs_into_playlist(WEEKLY_ID, LASTFM_USER, "7day")
    put_top_songs_into_playlist(MONTHLY_ID, LASTFM_USER, "1month")

def main():
    parser = argparse.ArgumentParser(description="Update Spotify playlists with Last.fm top tracks")
    parser.add_argument("--loop", type=int, help="Run the script in a loop with specified minutes between iterations")
    args = parser.parse_args()

    if args.loop:
        log_info(f"Running in loop mode with {args.loop} minutes interval")
        while True:
            update_playlists()
            log_info(f"Sleeping for {args.loop} minutes")
            time.sleep(args.loop * 60)
    else:
        update_playlists()

if __name__ == "__main__":
    main()
