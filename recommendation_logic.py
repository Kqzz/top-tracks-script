from collections import Counter, deque

import spotipy

from logging_config import LogLevel, log
from spotify_utils import get_spotify_client


def split_into_groups(tracks, group_size=5):
    return [tracks[i : i + group_size] for i in range(0, len(tracks), group_size)]


def aggregate_recommendations(group_recs, final_limit=30, exclude_ids=None):
    # group_recs: List[List[str]]
    # exclude_ids: set of track IDs to exclude from recommendations
    if exclude_ids is None:
        exclude_ids = set()

    all_recs = [track for group in group_recs for track in group]
    rec_counts = Counter(all_recs)
    final_list = []

    # 1. Add all tracks that appear in 2 or more groups (overlaps)
    overlapping = [
        (track, count)
        for track, count in rec_counts.items()
        if count >= 2 and track not in exclude_ids
    ]
    for track, count in overlapping:
        if track not in final_list:
            final_list.append(track)

    log(f"Added {len(final_list)} overlapping recommendations.", LogLevel.INFO)
    if overlapping:
        log("Overlapping tracks (track_id, name, artists, count):", LogLevel.INFO)
        try:
            sp = get_spotify_client()
            for track, count in overlapping:
                try:
                    t = sp.track(track)
                    name = t.get("name", "Unknown")
                    artists = ", ".join([a["name"] for a in t.get("artists", [])])
                    log(
                        f"  {track}: '{name}' by {artists} ({count} groups)",
                        LogLevel.INFO,
                    )
                except Exception as e:
                    log(
                        f"  {track}: [lookup failed: {e}] ({count} groups)",
                        LogLevel.INFO,
                    )
        except Exception as e:
            log(
                f"[WARN] Could not fetch track details for overlaps: {e}", LogLevel.INFO
            )

    # 2. Fill remaining slots round-robin
    group_queues = [deque(group) for group in group_recs]
    round_num = 1
    while len(final_list) < final_limit:
        for q in group_queues:
            while q:
                candidate = q.popleft()
                if candidate not in final_list and candidate not in exclude_ids:
                    final_list.append(candidate)
                    log(
                        f"Added track {candidate} from group in round {round_num}.",
                        LogLevel.DEBUG,
                    )
                    break
            if len(final_list) >= final_limit:
                break
        round_num += 1
        if all(not q for q in group_queues):
            break  # All queues empty

    log(f"Final recommendation list has {len(final_list)} tracks.", LogLevel.INFO)
    return final_list[:final_limit]
