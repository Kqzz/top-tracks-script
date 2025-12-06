import argparse
import os

import requests
import spotipy
from dotenv import load_dotenv

from chosic_api import ChosicClient
from logging_config import LogLevel, log
from recommendation_logic import aggregate_recommendations, split_into_groups
from spotify_utils import (
    get_spotify_client,
    get_top_n_tracks,
    move_tracks_to_top_of_playlist,
    replace_playlist,
)

# Load environment variables
load_dotenv()
WEEKLY_ID = os.getenv("WEEKLY_ID")
MONTHLY_ID = os.getenv("MONTHLY_ID")
RECOMMENDED_ID = os.getenv("RECOMMENDED_ID")
ARCHIVE_ID = os.getenv("ARCHIVE_ID")
LASTFM_API_KEY = os.getenv("LASTFM_KEY")
LASTFM_USER = os.getenv("LASTFM_USER")

RECS_PER_GROUP = 30
GROUP_SIZE = 5
FINAL_LIMIT = 30


def generate_advanced_recommendations():
    if not all([WEEKLY_ID, MONTHLY_ID, RECOMMENDED_ID, ARCHIVE_ID]):
        log(
            "Missing WEEKLY_ID, MONTHLY_ID, RECOMMENDED_ID, or ARCHIVE_ID in environment variables.",
            LogLevel.INFO,
        )
        return

    log("Fetching top tracks from playlists...", LogLevel.INFO)
    weekly_tracks = get_top_n_tracks(WEEKLY_ID, 10)
    monthly_tracks = get_top_n_tracks(MONTHLY_ID, 10)

    groups = split_into_groups(weekly_tracks, GROUP_SIZE) + split_into_groups(
        monthly_tracks, GROUP_SIZE
    )
    log(f"Formed {len(groups)} groups of {GROUP_SIZE} tracks each.", LogLevel.INFO)

    chosic = ChosicClient()
    chosic.initialize()

    group_recs = []
    for idx, group in enumerate(groups):
        log(f"Getting recommendations for group {idx + 1}: {group}", LogLevel.DEBUG)
        recs = chosic.get_recommendations(group, limit=RECS_PER_GROUP)
        group_recs.append([track["id"] for track in recs])
        log(
            f"Group {idx + 1} recommendations: {[track['id'] for track in recs]}",
            LogLevel.DEBUG,
        )

    # Exclude any tracks that are in the original weekly or monthly playlists
    exclude_ids = set(weekly_tracks + monthly_tracks)

    final_recs = aggregate_recommendations(
        group_recs, final_limit=FINAL_LIMIT, exclude_ids=exclude_ids
    )
    log(f"Final recommendations: {final_recs}", LogLevel.INFO)

    # Archive old recommendations before replacing
    old_recs = get_top_n_tracks(RECOMMENDED_ID, 100)
    if old_recs:
        move_tracks_to_top_of_playlist(ARCHIVE_ID, old_recs)
        log(
            f"Archived {len(old_recs)} old recommendations to archive playlist.",
            LogLevel.INFO,
        )

    replace_playlist(RECOMMENDED_ID, final_recs)
    log(f"Updated recommended playlist with {len(final_recs)} tracks.", LogLevel.INFO)


def get_top_songs(api_key, user, timeframe="7day", page=1, limit=100):
    url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={user}&api_key={api_key}&period={timeframe}&page={page}&limit={limit}&format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log(f"Failed to fetch top songs: {str(e)}", LogLevel.INFO)
        return None


def put_top_songs_into_playlist(playlist_id, last_fm_user, timeframe):
    log(
        f"Updating playlist {playlist_id} with top songs for {timeframe}", LogLevel.INFO
    )
    sp = get_spotify_client()
    try:
        sp.playlist_replace_items(playlist_id, [])
        log("Playlist cleared successfully", LogLevel.INFO)
    except (spotipy.SpotifyException, Exception) as e:
        log(f"Failed to clear playlist: {str(e)}", LogLevel.INFO)
        return
    songs = get_top_songs(
        LASTFM_API_KEY, last_fm_user, timeframe=timeframe, page=1, limit=50
    )
    if not songs:
        log("Failed to fetch top songs", LogLevel.INFO)
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
                log(
                    f"Song not found: {song.get('name')} by {song.get('artist').get('name')}",
                    LogLevel.INFO,
                )
        except (spotipy.SpotifyException, Exception) as e:
            log(f"Error adding song to playlist: {str(e)}", LogLevel.INFO)
    log(f"Added {added_count} songs to playlist {playlist_id}", LogLevel.INFO)


def update_playlists():
    if not all([LASTFM_API_KEY, LASTFM_USER, WEEKLY_ID, MONTHLY_ID]):
        log(
            "Missing required environment variables for Last.fm playlist update.",
            LogLevel.INFO,
        )
        return
    put_top_songs_into_playlist(WEEKLY_ID, LASTFM_USER, "7day")
    put_top_songs_into_playlist(MONTHLY_ID, LASTFM_USER, "1month")


def main():
    parser = argparse.ArgumentParser(
        description="Update Spotify playlists or generate advanced recommendations."
    )
    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Generate a recommended playlist from weekly and monthly playlists (advanced mode)",
    )
    parser.add_argument(
        "--top-songs",
        action="store_true",
        help="Update weekly and monthly playlists with Last.fm top tracks",
    )
    args = parser.parse_args()

    if args.top_songs:
        update_playlists()
    if args.recommend:
        generate_advanced_recommendations()
    if not args.recommend and not args.top_songs:
        print("Please specify --recommend, --top-songs, or both.")


if __name__ == "__main__":
    main()
