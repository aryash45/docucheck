import os 
import json
import hashlib
import sys
CACHE_DIR = ".Docucheck_Cache"
def get_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath,"rb") as f:
            for byte_block in iter(lambda:f.read(4096),b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"Error reading file for hashing : {e}",file=sys.stderr)
        return None
def get_cache(file_hash):
    if not os.path.exists(CACHE_DIR):
        return None
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r",encoding="utf-8") as f:
                return json.load(f)
        except (IOError,json.JSONDecodeError) as e:
            print(f"Error reading cache file. {e}", file=sys.stderr)
            return None
    return None
def set_cache(file_hash,data):
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except OSError as e:
            print(f"Warning: Could not create cache directory. {e}", file=sys.stderr)
            return
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    try:
        with open(cache_file, "w",encoding="utf-8") as f:
            json.dump(data, f,indent=2)
    except IOError as e:
        print(f"Error writing to cache file. {e}", file=sys.stderr)
    