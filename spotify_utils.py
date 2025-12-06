import spotipy
from spotipy.oauth2 import SpotifyOAuth

from logging_config import LogLevel, log

SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"

# Singleton Spotipy client
_sp = None


def get_spotify_client():
    global _sp
    if _sp is None:
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
    return _sp


def get_top_n_tracks(playlist_id, n):
    sp = get_spotify_client()
    tracks = []
    offset = 0
    limit = 100

    while len(tracks) < n:
        resp = sp.playlist_items(
            playlist_id, offset=offset, limit=min(limit, n - len(tracks))
        )
        items = resp.get("items", [])
        for item in items:
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(track["id"])
                if len(tracks) >= n:
                    break
        if len(items) < limit:
            break
        offset += limit

    log(f"Fetched {len(tracks)} tracks from playlist {playlist_id}", LogLevel.DEBUG)
    return tracks


def move_tracks_to_top_of_playlist(playlist_id, track_ids):
    """
    Moves the given track_ids to the top of the playlist, preserving order.
    Removes all occurrences of each track in track_ids from the playlist first.
    """
    sp = get_spotify_client()
    # Fetch all tracks in the playlist
    all_tracks = []
    offset = 0
    limit = 100
    while True:
        resp = sp.playlist_items(playlist_id, offset=offset, limit=limit)
        items = resp.get("items", [])
        if not items:
            break
        for item in items:
            track = item.get("track")
            if track and track.get("id"):
                all_tracks.append(track["id"])
        if len(items) < limit:
            break
        offset += limit

    # Remove all occurrences of each track_id from the playlist
    # (Spotify API: remove by snapshot, so do in one call per 100 tracks)
    to_remove = []
    for tid in track_ids:
        idxs = [i for i, t in enumerate(all_tracks) if t == tid]
        for idx in idxs:
            to_remove.append({"uri": f"spotify:track:{tid}"})
    if to_remove:
        # Remove all occurrences in one call (max 100 per call)
        for i in range(0, len(to_remove), 100):
            sp.playlist_remove_all_occurrences_of_items(
                playlist_id, [item["uri"] for item in to_remove[i : i + 100]]
            )

    # Add the tracks at the top (position=0), in order
    # Spotify API: playlist_add_items with position=0
    if track_ids:
        sp.playlist_add_items(
            playlist_id, [f"spotify:track:{tid}" for tid in track_ids], position=0
        )
    log(
        f"Moved {len(track_ids)} tracks to top of playlist {playlist_id}", LogLevel.INFO
    )


def replace_playlist(playlist_id, track_ids):
    sp = get_spotify_client()
    # Replace up to 100 tracks, then add in batches
    sp.playlist_replace_items(playlist_id, track_ids[:100])
    for i in range(100, len(track_ids), 100):
        sp.playlist_add_items(playlist_id, track_ids[i : i + 100])
    log(f"Replaced playlist {playlist_id} with {len(track_ids)} tracks", LogLevel.INFO)
