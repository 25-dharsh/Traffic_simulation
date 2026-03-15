"""
Phase 2 — Download Chennai OSM map from Overpass API.
Retry logic, fallback endpoint, and minimum file size validation.
"""

import os
import sys
import time
import requests

# ── Config ──────────────────────────────────────────────────────────────────
BBOX = (80.209, 13.035, 80.235, 13.062)   # (min_lon, min_lat, max_lon, max_lat)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "osm", "chennai.osm")
MIN_FILE_SIZE_MB = 5

ENDPOINTS = [
    "https://overpass-api.de/api/map",
    "https://overpass.kumi.systems/api/map",
]

MAX_RETRIES = 3
RETRY_DELAY = 10   # seconds


def build_url(endpoint: str) -> str:
    min_lon, min_lat, max_lon, max_lat = BBOX
    return f"{endpoint}?bbox={min_lon},{min_lat},{max_lon},{max_lat}"


def download_osm():
    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    for endpoint in ENDPOINTS:
        url = build_url(endpoint)
        print(f"[download_osm] Trying endpoint: {endpoint}")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"  Attempt {attempt}/{MAX_RETRIES} → GET {url}")
                response = requests.get(url, timeout=120, stream=True)
                response.raise_for_status()

                # Stream-write to file
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        f.write(chunk)

                # ── Validate size ──────────────────────────────────────────
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                if size_mb < MIN_FILE_SIZE_MB:
                    print(f"  [WARN] File too small: {size_mb:.2f} MB (minimum {MIN_FILE_SIZE_MB} MB). Retrying…")
                    os.remove(output_path)
                else:
                    print(f"  [OK] Downloaded {size_mb:.2f} MB → {output_path}")
                    return output_path

            except requests.RequestException as e:
                print(f"  [ERROR] Attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    print(f"  Waiting {RETRY_DELAY}s before retry…")
                    time.sleep(RETRY_DELAY)

        print(f"[download_osm] All retries exhausted for {endpoint}. Trying next endpoint…")

    sys.exit("[download_osm] FATAL: Could not download a valid OSM file from any endpoint. Aborting.")


if __name__ == "__main__":
    download_osm()
    print("[download_osm] Phase 2 complete.")
