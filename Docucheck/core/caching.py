"""Caching module for storing analysis results."""
import os, json, hashlib, sys

CACHE_DIR = ".docucheck_cache"

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return None

def get_cache(file_hash):
    """Retrieve cached analysis results."""
    if not os.path.exists(CACHE_DIR):
        return None
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None

def set_cache(file_hash, data):
    """Store analysis results to cache."""
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except: return
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except: pass
