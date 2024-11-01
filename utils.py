import os
import json
import logging

CACHE_FILE = 'user_following_cache.json'

logger = logging.getLogger(__name__)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logger.error('Failed to decode cache JSON.')
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as file:
        json.dump(cache, file)
