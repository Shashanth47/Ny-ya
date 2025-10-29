import csv
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

DEFAULT_CSV = Path("data/additional_sources.csv")
DEFAULT_OUT_DIR = Path("data/indian_acts")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"
}


def ensure_dir(d: Path):
    d.mkdir(parents=True, exist_ok=True)


def derive_filename(url: str) -> str:
    path = urlparse(url).path
    name = os.path.basename(path)
    return name or "download.pdf"


def download(url: str, out_path: Path) -> bool:
    try:
        with requests.get(url, stream=True, headers=HEADERS, timeout=60) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
        print(f"Downloaded: {out_path.name}")
        return True
    except Exception as e:
        print(f"Failed: {url} -> {out_path}: {e}")
        return False


def main(csv_path: Path = DEFAULT_CSV, out_dir: Path = DEFAULT_OUT_DIR):
    ensure_dir(out_dir)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # Expected: [URL] or [URL, FILENAME]
            url = row[0].strip()
            if not url or url.lower().startswith("#"):
                continue
            filename = (row[1].strip() if len(row) > 1 and row[1].strip() else derive_filename(url))
            out_path = out_dir / filename
            if out_path.exists() and out_path.stat().st_size > 0:
                print(f"Skip existing: {filename}")
                continue
            download(url, out_path)


if __name__ == "__main__":
    csv_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    out_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    main(csv_arg, out_arg)