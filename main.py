import json
import os

import requests
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_KEY")

scope = "playlist-read-private playlist-modify-private playlist-modify-public"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


def get_top_songs(api_key, user, timeframe="7day", page=1, limit=100):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={user}&api_key={api_key}&period={timeframe}&page={page}&limit={limit}&format=json"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    else:
        print("failed: ", r.status_code, r.text)
        return None


def put_top_songs_into_playlist(playlist_id, last_fm_user, timeframe):
    sp.playlist_replace_items(playlist_id, [])

    songs = get_top_songs(
        LASTFM_API_KEY, last_fm_user, timeframe=timeframe, page=1, limit=50
    )

    for song in songs["toptracks"]["track"]:
        results = sp.search(
            q=f"track:{song.get('name')} artist:{song.get('artist').get('name')}",
            type="track",
            limit=1,
        )

        # Check if the song was found
        if results["tracks"]["items"]:
            # Get the URI of the first track
            track_uri = results["tracks"]["items"][0]["uri"]

            # Add the song to the playlist
            sp.playlist_add_items(playlist_id, [track_uri])


weekly = os.getenv("WEEKLY_ID")
monthly = os.getenv("MONTHLY_ID")
put_top_songs_into_playlist(weekly, "kqzz", "7day")
put_top_songs_into_playlist(monthly, "kqzz", "1month")
