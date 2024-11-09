import logging
from github_api import (
    get_followers,
    get_following,
    bulk_unfollow_users,
)

logger = logging.getLogger('weekly_tasks')

def run_weekly_tasks():
    logger.info("Starting weekly tasks")

    # Unfollow users who are not following back
    logger.info("Removing users who are not following back")
    current_followers = get_followers()
    current_following = get_following()
    followers_set = set(current_followers)
    following_usernames = [user['login'] for user in current_following]
    not_following_back = [user for user in following_usernames if user not in followers_set]
    logger.info(f"Users not following back: {not_following_back}")
    if not_following_back:
        unfollow_results = bulk_unfollow_users(not_following_back)
        logger.info(f"Unfollow results: {unfollow_results}")
    else:
        logger.info("No users to unfollow")

    logger.info("Weekly tasks completed")
