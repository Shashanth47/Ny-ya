import os
import re
import csv
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dpar.karnataka.gov.in/servicerules/public/info-3/Acts+and+Rules/en"
OUTPUT_DIR = os.path.join("data", "karnataka_acts")
CSV_PATH = "karnataka_acts_index.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"
}


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_soup(url: str) -> BeautifulSoup:
    s = requests.Session()
    s.headers.update(HEADERS)
    resp = s.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_pdf_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    links = []
    # Collect anchors with href containing .pdf (handles querystring variants too)
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if ".pdf" in href.lower():
            url = urljoin(base_url, href)
            text = a.get_text(strip=True)
            links.append({"url": url, "text": text})
    # Deduplicate by URL
    seen = set()
    unique = []
    for item in links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique


def parse_year(text: str) -> str:
    # Extract the first 4-digit year if present
    m = re.search(r"(19|20)\d{2}", text)
    return m.group(0) if m else ""


def download_file(url: str, filepath: str) -> bool:
    try:
        with requests.get(url, stream=True, headers=HEADERS, timeout=60) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def main():
    ensure_dirs()

    print(f"Fetching index page: {BASE_URL}")
    soup = get_soup(BASE_URL)
    pdf_links = extract_pdf_links(soup, BASE_URL)
    print(f"Found {len(pdf_links)} PDF link(s)")

    # Write CSV header
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Act Name", "Year", "URL", "Filename", "Downloaded On"])  # schema per your example

        for item in pdf_links:
            url = item["url"]
            act_name = item["text"] or os.path.basename(url)
            year = parse_year(act_name)
            filename = os.path.basename(url.split("?")[0])
            filepath = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                print(f"Skipping existing: {filename}")
                downloaded_on = datetime.utcnow().isoformat()
                writer.writerow([act_name, year, url, filename, downloaded_on])
                continue

            print(f"Downloading: {filename}")
            ok = download_file(url, filepath)
            downloaded_on = datetime.utcnow().isoformat() if ok else ""
            writer.writerow([act_name, year, url, filename, downloaded_on])
            time.sleep(0.5)  # be polite

    print(f"Done. CSV index: {CSV_PATH}\nFiles saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()