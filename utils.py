import os
import json
import logging

logger = logging.getLogger(__name__)

CACHE_FILE = 'user_following_cache.json'

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    logger.debug(f"Creating chunks of size {n}")
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def load_cache():
    logger.debug("Loading cache")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            try:
                cache = json.load(file)
                logger.debug(f"Loaded cache with {len(cache)} entries")
                return cache
            except json.JSONDecodeError:
                logger.error('Failed to decode cache JSON.')
    else:
        logger.debug("Cache file not found")
    return {}

def save_cache(cache):
    logger.debug(f"Saving cache with {len(cache)} entries")
    with open(CACHE_FILE, 'w') as file:
        json.dump(cache, file)
    logger.debug("Cache saved successfully")
