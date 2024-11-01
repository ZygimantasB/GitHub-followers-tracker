import os
import json
import logging

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

def load_ignore_list():
    logger.debug("Loading ignore list")
    if os.path.exists(IGNORE_LIST_FILE):
        with open(IGNORE_LIST_FILE, 'r') as file:
            ignore_list = file.read().splitlines()
            logger.debug(f"Loaded ignore list with {len(ignore_list)} entries")
            return ignore_list
    else:
        logger.debug("Ignore list file not found")
    return []
