import json
import os
from http.cookies import SimpleCookie
from typing import Dict, List, Optional

import requests

# Toggle logging here
ENABLE_LOGS = True
SESSION_FILE = ".chosic_session.json"


class ChosicClient:
    HANDSHAKE_URL = "https://www.chosic.com/api/tools/handshake/"
    RECOMMEND_URL = "https://www.chosic.com/api/tools/recommendations"
    INIT_COOKIE = {"pll_language": "en"}
    HEADERS = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.5",
        "app": "playlist_generator",
        "priority": "u=1, i",
        "referer": "https://www.chosic.com/playlist-generator/",
        "sec-ch-ua": '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, session_file: str = SESSION_FILE):
        self.session_file = session_file
        self.cookies = None
        self._load_session()

    def log(self, msg: str):
        if ENABLE_LOGS:
            print(f"[ChosicClient] {msg}")

    def _load_session(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    self.cookies = data.get("cookies", None)
                self.log(f"Loaded session from {self.session_file}")
            except Exception as e:
                self.log(f"Failed to load session: {e}")
                self.cookies = None
        else:
            self.cookies = None

    def _save_session(self):
        try:
            with open(self.session_file, "w") as f:
                json.dump({"cookies": self.cookies}, f)
            self.log(f"Saved session to {self.session_file}")
        except Exception as e:
            self.log(f"Failed to save session: {e}")

    def initialize(self, force: bool = False):
        if self.cookies and not force:
            self.log("Session already initialized.")
            return
        self.log("Performing handshake with Chosic...")
        resp = requests.post(
            self.HANDSHAKE_URL,
            headers={**self.HEADERS, "accept": "*/*"},
            cookies=self.INIT_COOKIE,
        )
        if resp.status_code != 200:
            self.log(f"Handshake failed: {resp.status_code} {resp.text}")
            raise Exception(f"Handshake failed: {resp.status_code}")
        # Extract cookies from response
        cookie_jar = resp.cookies
        self.cookies = requests.utils.dict_from_cookiejar(cookie_jar)
        self.log(f"Handshake successful. Cookies: {self.cookies}")
        self._save_session()

    def get_recommendations(
        self, seed_tracks: List[str], limit: int = 10
    ) -> List[Dict]:
        if not self.cookies:
            self.log("No session found, initializing...")
            self.initialize()
        params = {"seed_tracks": ",".join(seed_tracks), "limit": limit}
        headers = self.HEADERS.copy()
        headers["accept"] = "application/json, text/javascript, */*; q=0.01"
        try:
            resp = requests.get(
                self.RECOMMEND_URL, params=params, headers=headers, cookies=self.cookies
            )
            if resp.status_code == 401 or resp.status_code == 403:
                self.log("Session expired or unauthorized, re-initializing...")
                self.initialize(force=True)
                resp = requests.get(
                    self.RECOMMEND_URL,
                    params=params,
                    headers=headers,
                    cookies=self.cookies,
                )
            resp.raise_for_status()
            data = resp.json()
            self.log(f"Fetched {len(data.get('tracks', []))} recommendations.")
            return data.get("tracks", [])
        except Exception as e:
            self.log(f"Failed to fetch recommendations: {e}")
            raise
