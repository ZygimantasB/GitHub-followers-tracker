import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify
from decouple import config
from github_api import (
    get_followers,
    get_following,
    follow_user,
    unfollow_user,
    bulk_follow_users,
    bulk_unfollow_users,
    get_followers_with_counts,
    get_users_info,
    get_random_users_with_more_following,
)
from data_manager import (
    load_previous_followers,
    save_followers,
    load_new_followers,
    save_new_followers,
    load_ignore_list,
)
from datetime import datetime, timedelta

app = Flask(__name__)

GITHUB_USERNAME = config('GITHUB_USERNAME')

LOG_FILE = 'app.log'

# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set the logging level

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set level for console handler

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)  # Set level for file handler

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

@app.route('/')
def index():
    logger.info('Loading index page')
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    data_type = request.args.get('type')
    logger.info(f'Fetching data for {data_type}')

    # Load necessary data files
    previous_followers = load_previous_followers()
    stored_new_followers = load_new_followers()
    ignore_list = load_ignore_list()

    current_time = datetime.now()

    # Fetch data based on the requested type
    try:
        if data_type == 'followers':
            current_followers = get_followers_with_counts()
            # Apply ignore list
            current_followers = [user for user in current_followers if user['login'] not in ignore_list]
            data = {'followers': current_followers}
            return jsonify(data)
        elif data_type == 'following':
            current_following = get_following()
            # Apply ignore list
            current_following = [f for f in current_following if f['login'] not in ignore_list]
            data = {'following': current_following}
            return jsonify(data)
        elif data_type == 'new_followers':
            current_followers = get_followers()
            new_followers = list(set(current_followers) - set(previous_followers))
            # Apply ignore list
            new_followers = [user for user in new_followers if user not in ignore_list]
            # Update stored_new_followers
            for follower in new_followers:
                if follower not in stored_new_followers:
                    stored_new_followers[follower] = current_time.isoformat()
            recent_new_followers = {
                user: timestamp
                for user, timestamp in stored_new_followers.items()
                if datetime.fromisoformat(timestamp) >= current_time - timedelta(days=3)
            }
            save_new_followers(recent_new_followers)
            new_followers_info = get_users_info(list(recent_new_followers.keys()))
            data = {'new_followers': new_followers_info}
            return jsonify(data)
        elif data_type == 'unfollowers':
            current_followers = get_followers()
            unfollowers = list(set(previous_followers) - set(current_followers))
            # Apply ignore list
            unfollowers = [user for user in unfollowers if user not in ignore_list]
            unfollowers_info = get_users_info(unfollowers)
            data = {'unfollowers': unfollowers_info}
            return jsonify(data)
        elif data_type == 'not_following_back':
            current_followers = get_followers()
            current_following = get_following()
            current_follower_logins = set(current_followers)
            not_following_back = [
                f['login']
                for f in current_following
                if f['login'] not in current_follower_logins and f['login'] not in ignore_list
            ]
            not_following_back_info = get_users_info(not_following_back)
            data = {'not_following_back': not_following_back_info}
            return jsonify(data)
        elif data_type == 'suggested_users':
            # Fetch random users who have more following than followers
            random_users = get_random_users_with_more_following()
            # Apply ignore list
            random_users = [user for user in random_users if user['login'] not in ignore_list]
            data = {'suggested_users': random_users}
            return jsonify(data)
        elif data_type == 'users_more_following':
            followers_with_counts = get_followers_with_counts()
            users_more_following = [
                {
                    'login': follower['login'],
                    'followers': follower['followers'],
                    'following': follower['following'],
                    'difference': follower['following'] - follower['followers']
                }
                for follower in followers_with_counts
                if follower['following'] > follower['followers'] and follower['login'] not in ignore_list
            ]
            # Sort users by the biggest difference
            users_more_following.sort(key=lambda x: x['difference'], reverse=True)
            data = {'users_more_following': users_more_following}
            return jsonify(data)
        else:
            logger.error(f'Invalid data type requested: {data_type}')
            return jsonify({'error': 'Invalid data type requested'}), 400
    except Exception as e:
        logger.exception(f"Error fetching data for {data_type}: {e}")
        return jsonify({'error': 'An error occurred while fetching data'}), 500

@app.route('/bulk_follow', methods=['POST'])
def bulk_follow():
    usernames = request.json.get('usernames', [])
    logger.info(f'Attempting to bulk follow users: {usernames}')
    results = bulk_follow_users(usernames)
    return jsonify(results)

@app.route('/bulk_unfollow', methods=['POST'])
def bulk_unfollow():
    usernames = request.json.get('usernames', [])
    logger.info(f'Attempting to bulk unfollow users: {usernames}')
    results = bulk_unfollow_users(usernames)
    return jsonify(results)

# Add these routes for individual follow/unfollow actions
@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    logger.info(f'Attempting to unfollow user: {username}')
    success, message = unfollow_user(username)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': message}), 500

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    logger.info(f'Attempting to follow user: {username}')
    success, message = follow_user(username)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': message}), 500

if __name__ == "__main__":
    app.run(debug=True)
