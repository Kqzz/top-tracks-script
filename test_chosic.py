from chosic_api import ChosicClient

if __name__ == "__main__":
    chosic = ChosicClient()
    chosic.initialize()  # Will load or perform handshake as needed
    seed_tracks = ["0MPhcfGfHPlHu2GNspRXdO"]  # Replace with your own if desired
    print(f"Testing Chosic API with seed tracks: {seed_tracks}")
    try:
        tracks = chosic.get_recommendations(seed_tracks, limit=10)
        print(f"Received {len(tracks)} recommendations:")
        for t in tracks:
            print(f"- {t.get('name', 'Unknown')} by {', '.join(a['name'] for a in t.get('artists', []))} (ID: {t.get('id')})")
    except Exception as e:
        print(f"Error: {e}")
