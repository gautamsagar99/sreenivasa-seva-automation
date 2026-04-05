#!/usr/bin/env python3
"""
God Images Downloader - Download copyright-free images based on config.json
Saves to the images/ folder for use with create_reel.py
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image
from io import BytesIO
from typing import List, Dict

# ============================================
# Load Configuration
# ============================================

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Validate download config
    if "download" not in config:
        raise ValueError("Missing 'download' section in config.json")

    download_config = config["download"]
    required = ["gods", "images_per_god"]
    for field in required:
        if field not in download_config:
            raise ValueError(f"Missing download config: {field}")

    return config

try:
    CONFIG = load_config()
except Exception as e:
    print(f"[ERROR] Configuration error: {e}", file=sys.stderr)
    sys.exit(1)

# ============================================
# Settings from Config
# ============================================

DOWNLOAD_CONFIG = CONFIG["download"]
TARGET_GODS = DOWNLOAD_CONFIG["gods"]  # List of gods to download
IMAGES_PER_GOD = DOWNLOAD_CONFIG.get("images_per_god", 20)
SOURCE = DOWNLOAD_CONFIG.get("source", "wikimedia")  # wikimedia, pexels, unsplash, pixabay

# API keys (optional - only needed for non-wikimedia sources)
API_KEYS = {
    "pexels": CONFIG.get("pexels_api_key", ""),
    "unsplash": CONFIG.get("unsplash_access_key", ""),
    "pixabay": CONFIG.get("pixabay_api_key", "")
}

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
IMAGES_FOLDER = BASE_DIR / CONFIG.get("images_folder", "images")

# Constants
MIN_IMAGE_SIZE = (1920, 1080)  # Minimum resolution
USER_AGENT = "GodReelImages/1.0 (https://github.com/yourrepo) - Personal video creation"
REQUEST_TIMEOUT = 15

# Search keywords for gods (expandable)
GOD_KEYWORDS = {
    "shiva": ["Shiva", "Shiva lingam", "Nataraja", "Shiva statue", "Mahadeva"],
    "vishnu": ["Vishnu", "Venkateswara", "Narasimha", "Rama", "Krishna"],
    "ganesha": ["Ganesha", "Ganesh", "Ganapati", "Elephant god"],
    "lakshmi": ["Lakshmi", "Goddess Lakshmi", "Sri Lakshmi"],
    "saraswati": ["Saraswati", "Goddess Saraswati", "Veena"],
    "durga": ["Durga", "Goddess Durga", "Maa Durga", "Shakti"],
    "kali": ["Kali", "Goddess Kali", "Kali Ma"],
    "krishna": ["Krishna", "Radha Krishna", "Govinda", "Flute Krishna"],
    "ram": ["Ram", "Rama", "Ram Lalla", "Ayodhya"],
    "hanuman": ["Hanuman", "Bajrang Bali", "Anjaneya"],
    "sai": ["Sai Baba", "Shirdi Sai"],
    "temple": ["Hindu temple", "mandir", "temple architecture", "temple India"]
}

# ============================================
# Utility Functions
# ============================================

def ensure_folder(path: Path) -> None:
    """Create folder if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(text: str) -> str:
    """Convert text to safe filename"""
    import re
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')[:80]

def download_and_validate(url: str, save_path: Path, min_size: tuple = MIN_IMAGE_SIZE) -> bool:
    """Download image and validate size"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'image' not in content_type:
            return False

        # Load image
        img_data = response.content
        img = Image.open(BytesIO(img_data))
        width, height = img.size

        if width < min_size[0] or height < min_size[1]:
            return False

        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background

        # Save as optimized JPEG
        img.save(save_path, "JPEG", quality=90, optimize=True)
        return True

    except Exception:
        return False

# ============================================
# Wikimedia Commons (No API Key Required)
# ============================================

def search_wikimedia(query: str, limit: int = 20) -> List[Dict]:
    """Search Wikimedia Commons for images -真正免费，无需API密钥"""
    api_url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srnamespace": "6",  # File namespace
        "srsearch": query,
        "srlimit": min(limit, 50),
        "srprop": "titlesnippet"
    }

    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 403:
            # Rate limited, wait and retry once
            time.sleep(2)
            response = requests.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        response.raise_for_status()
        data = response.json()

        images = []
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            if title.startswith("File:"):
                img_info = get_wikimedia_image_info(title)
                if img_info:
                    images.append(img_info)

        return images

    except Exception as e:
        print(f"[WARN] Wikimedia search failed for '{query}': {e}")
        return []

def get_wikimedia_image_info(title: str) -> Dict:
    """Get image URL and check license"""
    api_url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata"
    }

    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 403:
            time.sleep(2)
            response = requests.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        response.raise_for_status()
        data = response.json()

        page = next(iter(data.get("query", {}).get("pages", {}).values()))
        if "-1" in page:  # Missing page
            return None

        imageinfo = page.get("imageinfo", [{}])[0]
        url = imageinfo.get("url")
        if not url:
            return None

        width = imageinfo.get("width", 0)
        height = imageinfo.get("height", 0)

        # Check license
        extmetadata = imageinfo.get("extmetadata", {})
        license_data = extmetadata.get("License", {})
        license_url = license_data.get("value", "").lower() if isinstance(license_data, dict) else str(license_data).lower()

        # Accept only free licenses
        free_keywords = ["public domain", "cc0", "cc-by", "cc-by-sa", "pd", "pdm"]
        is_free = any(kw in license_url for kw in free_keywords) or not license_url

        if not is_free:
            return None

        return {
            "url": url,
            "title": title.replace("File:", "")[:80],
            "width": width,
            "height": height
        }

    except Exception:
        return None

# ============================================
# Pexels (Requires API Key)
# ============================================

def search_pexels(query: str, api_key: str, limit: int = 20) -> List[Dict]:
    """Search Pexels API"""
    if not api_key:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": min(limit, 80),
        "orientation": "portrait"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        images = []
        for photo in data.get("photos", [])[:limit]:
            img_url = photo.get("src", {}).get("original") or photo.get("src", {}).get("large")
            if img_url:
                images.append({
                    "url": img_url,
                    "title": f"pexels_{photo.get('id', 'unknown')}",
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0)
                })

        return images

    except Exception as e:
        print(f"[WARN] Pexels failed for '{query}': {e}")
        return []

# ============================================
# Unsplash (Requires Access Key)
# ============================================

def search_unsplash(query: str, access_key: str, limit: int = 20) -> List[Dict]:
    """Search Unsplash API"""
    if not access_key:
        return []

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {
        "query": query,
        "per_page": min(limit, 30),
        "orientation": "portrait"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        images = []
        for result in data.get("results", [])[:limit]:
            img_url = result.get("urls", {}).get("raw") or result.get("urls", {}).get("full")
            if img_url:
                images.append({
                    "url": img_url,
                    "title": f"unsplash_{result.get('id', 'unknown')}",
                    "width": result.get("width", 0),
                    "height": result.get("height", 0)
                })

        return images

    except Exception as e:
        print(f"[WARN] Unsplash failed for '{query}': {e}")
        return []

# ============================================
# Pixabay (Requires API Key)
# ============================================

def search_pixabay(query: str, api_key: str, limit: int = 20) -> List[Dict]:
    """Search Pixabay API"""
    if not api_key:
        return []

    url = "https://pixabay.com/api/"
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "per_page": min(limit, 200),
        "orientation": "vertical"
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        images = []
        for hit in data.get("hits", [])[:limit]:
            img_url = hit.get("largeImageURL")
            if img_url:
                images.append({
                    "url": img_url,
                    "title": f"pixabay_{hit.get('id', 'unknown')}",
                    "width": hit.get("imageWidth", 0),
                    "height": hit.get("imageHeight", 0)
                })

        return images

    except Exception as e:
        print(f"[WARN] Pixabay failed for '{query}': {e}")
        return []

# ============================================
# Main Downloader
# ============================================

def download_images_to_folder(god_name: str, max_images: int) -> tuple:
    """Download images for a specific god directly to images folder"""

    print(f"\n{'='*60}")
    print(f"Downloading: {god_name.upper()}")
    print(f"Target: ~{max_images} images")
    print(f"Source: {SOURCE}")
    print('='*60)

    # Get search keywords
    keywords = GOD_KEYWORDS.get(god_name.lower(), [god_name])
    print(f"Using keywords: {', '.join(keywords[:3])}...")

    all_images = []

    # Search based on source
    if SOURCE == "wikimedia":
        for keyword in keywords:
            print(f"  Searching Wikimedia: '{keyword}'")
            results = search_wikimedia(keyword, limit=15)
            all_images.extend(results)
            time.sleep(0.5)  # Be respectful

    elif SOURCE == "pexels":
        api_key = API_KEYS.get("pexels", "")
        if not api_key:
            print("[ERROR] Pexels API key not configured in config.json")
            return 0, 0
        for keyword in keywords:
            print(f"  Searching Pexels: '{keyword}'")
            results = search_pexels(keyword, api_key, limit=10)
            all_images.extend(results)
            time.sleep(0.5)

    elif SOURCE == "unsplash":
        api_key = API_KEYS.get("unsplash", "")
        if not api_key:
            print("[ERROR] Unsplash access key not configured in config.json")
            return 0, 0
        for keyword in keywords:
            print(f"  Searching Unsplash: '{keyword}'")
            results = search_unsplash(keyword, api_key, limit=10)
            all_images.extend(results)
            time.sleep(0.5)

    elif SOURCE == "pixabay":
        api_key = API_KEYS.get("pixabay", "")
        if not api_key:
            print("[ERROR] Pixabay API key not configured in config.json")
            return 0, 0
        for keyword in keywords:
            print(f"  Searching Pixabay: '{keyword}'")
            results = search_pixabay(keyword, api_key, limit=15)
            all_images.extend(results)
            time.sleep(0.5)

    elif SOURCE == "all":
        # Use all available sources
        print("  Using ALL sources (requires all API keys for full results)")
        for keyword in keywords:
            results = search_wikimedia(keyword, limit=10)
            all_images.extend(results)
            if API_KEYS.get("pexels"):
                results = search_pexels(keyword, API_KEYS["pexels"], limit=5)
                all_images.extend(results)
            if API_KEYS.get("unsplash"):
                results = search_unsplash(keyword, API_KEYS["unsplash"], limit=5)
                all_images.extend(results)
            if API_KEYS.get("pixabay"):
                results = search_pixabay(keyword, API_KEYS["pixabay"], limit=5)
                all_images.extend(results)
            time.sleep(0.5)
    else:
        print(f"[ERROR] Unknown source: {SOURCE}. Use: wikimedia, pexels, unsplash, pixabay, all")
        return 0, 0

    # Deduplicate by URL
    seen_urls = set()
    unique_images = []
    for img in all_images:
        if img["url"] not in seen_urls:
            seen_urls.add(img["url"])
            unique_images.append(img)

    print(f"\nFound {len(unique_images)} unique images")

    if not unique_images:
        print("[WARN] No images found. Try different keywords or source.")
        return 0, 0

    # Download images directly to images folder
    downloaded = 0
    failed = 0
    max_to_download = min(max_images, len(unique_images))

    print(f"Downloading {max_to_download} images to: {IMAGES_FOLDER}")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []

        for idx, img_info in enumerate(unique_images[:max_to_download]):
            # Create filename with god name prefix to avoid conflicts
            title = img_info.get("title", f"image_{idx}")
            god_prefix = sanitize_filename(god_name)
            filename = f"{god_prefix}_{sanitize_filename(title)}_{idx+1:03d}.jpg"
            save_path = IMAGES_FOLDER / filename

            if save_path.exists():
                continue

            futures.append(
                executor.submit(download_and_validate, img_info["url"], save_path)
            )

        for future in as_completed(futures):
            try:
                if future.result():
                    downloaded += 1
                    print(f"[OK] Downloaded ({downloaded}/{len(futures)})")
                else:
                    failed += 1
            except Exception as e:
                print(f"[ERROR] Download failed: {e}")
                failed += 1

    print(f"\n{'='*60}")
    print(f"COMPLETE: {god_name}")
    print(f"  Downloaded: {downloaded}")
    print(f"  Failed: {failed}")
    print(f"  Location: {IMAGES_FOLDER}")
    print('='*60)

    return downloaded, failed

def main():
    start_time = time.time()

    print("\n" + "="*60)
    print("God Images Downloader")
    print("="*60)
    print(f"Source: {SOURCE}")
    print(f"Images per god: {IMAGES_PER_GOD}")
    print(f"Output folder: {IMAGES_FOLDER}")
    print("="*60)

    # Create main images folder
    ensure_folder(IMAGES_FOLDER)

    total_downloaded = 0
    total_failed = 0

    # Download for each god directly to images folder
    for god in TARGET_GODS:
        down, fail = download_images_to_folder(god, IMAGES_PER_GOD)
        total_downloaded += down
        total_failed += fail
        time.sleep(1)  # Pause between gods

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print("ALL DOWNLOADS COMPLETE!")
    print(f"  Total images: {total_downloaded}")
    print(f"  Failed: {total_failed}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Images saved to: {IMAGES_FOLDER}")
    print("="*60)
    print("\nNext step: Run 'python scripts/create_reel.py' to generate videos")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Download cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
