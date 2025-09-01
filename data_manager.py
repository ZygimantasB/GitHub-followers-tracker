import os
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

PREVIOUS_FOLLOWERS_FILE = 'previous_followers.txt'
NEW_FOLLOWERS_FILE = 'new_followers.json'
IGNORE_LIST_FILE = 'ignore_list.txt'


def load_previous_followers():
    logger.debug("Loading previous followers")
    if os.path.exists(PREVIOUS_FOLLOWERS_FILE):
        with open(PREVIOUS_FOLLOWERS_FILE, 'r') as file:
            followers = file.read().splitlines()
            logger.debug(f"Loaded {len(followers)} previous followers")
            return followers
    else:
        logger.debug("Previous followers file not found")
    return []


def save_followers(followers):
    logger.debug(f"Saving {len(followers)} followers to file")
    with open(PREVIOUS_FOLLOWERS_FILE, 'w') as file:
        for follower in followers:
            file.write(follower + '\n')
    logger.debug("Followers saved successfully")


def load_new_followers():
    logger.debug("Loading new followers")
    if os.path.exists(NEW_FOLLOWERS_FILE):
        try:
            with open(NEW_FOLLOWERS_FILE, 'r') as file:
                content = file.read().strip()
                if content:
                    new_followers = json.loads(content)
                    logger.debug(f"Loaded {len(new_followers)} new followers")
                    return new_followers
                else:
                    logger.debug("New followers file is empty")
        except json.JSONDecodeError:
            logger.error('Failed to decode new followers JSON.')
    else:
        logger.debug("New followers file not found")
    return {}


def save_new_followers(new_followers):
    logger.debug(f"Saving {len(new_followers)} new followers to file")
    with open(NEW_FOLLOWERS_FILE, 'w') as file:
        json.dump(new_followers, file)
    logger.debug("New followers saved successfully")


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def load_ignore_list() -> List[str]:
    logger.debug("Loading ignore list")
    if os.path.exists(IGNORE_LIST_FILE):
        with open(IGNORE_LIST_FILE, 'r') as file:
            ignore_list = [
                _normalize_username(line)
                for line in file.read().splitlines()
                if _normalize_username(line)
            ]
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for u in ignore_list:
                if u not in seen:
                    seen.add(u)
                    deduped.append(u)
            logger.debug(f"Loaded ignore list with {len(deduped)} entries")
            return deduped
    else:
        logger.debug("Ignore list file not found")
    return []


def save_ignore_list(usernames: List[str]) -> List[str]:
    """Persist the provided usernames (normalized, deduped) to IGNORE_LIST_FILE and return the saved list."""
    normalized = []
    seen = set()
    for name in usernames:
        n = _normalize_username(name)
        if n and n not in seen:
            seen.add(n)
            normalized.append(n)
    with open(IGNORE_LIST_FILE, 'w') as f:
        for u in normalized:
            f.write(u + '\n')
    logger.debug(f"Saved ignore list with {len(normalized)} entries")
    return normalized


def add_to_ignore_list(username: str) -> List[str]:
    """Add a username to ignore list; returns updated list."""
    if not username:
        return load_ignore_list()
    current = load_ignore_list()
    n = _normalize_username(username)
    if n and n not in current:
        current.append(n)
        save_ignore_list(current)
    return current


def remove_from_ignore_list(username: str) -> List[str]:
    """Remove a username from ignore list; returns updated list."""
    if not username:
        return load_ignore_list()
    current = load_ignore_list()
    n = _normalize_username(username)
    filtered = [u for u in current if u != n]
    if len(filtered) != len(current):
        save_ignore_list(filtered)
    return filtered
