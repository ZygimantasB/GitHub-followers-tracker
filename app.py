import os
import requests
import json
from flask import Flask, render_template, request
from datetime import datetime, timedelta
from decouple import config

app = Flask(__name__)

GITHUB_USERNAME = config('GITHUB_USERNAME')
GITHUB_TOKEN = config('GITHUB_TOKEN')

FOLLOWERS_URL = f'https://api.github.com/users/{GITHUB_USERNAME}/followers'
FOLLOWING_URL = f'https://api.github.com/users/{GITHUB_USERNAME}/following'

headers = {
    'Authorization': f'token {GITHUB_TOKEN}'
} if GITHUB_TOKEN else {}

PREVIOUS_FOLLOWERS_FILE = 'previous_followers.txt'
NEW_FOLLOWERS_FILE = 'new_followers.json'
IGNORE_LIST_FILE = 'ignore_list.txt'


@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    follow_url = f'https://api.github.com/user/following/{username}'
    response = requests.put(follow_url, headers=headers)

    if response.status_code == 204:
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    unfollow_url = f'https://api.github.com/user/following/{username}'
    response = requests.delete(unfollow_url, headers=headers)

    if response.status_code == 204:
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}


def get_github_data(url):
    data = []
    page = 1
    while True:
        response = requests.get(url, headers=headers, params={'page': page})
        try:
            response_data = response.json()
            if not isinstance(response_data, list):
                break  # Exit the loop if the response is not a list
            if not response_data:
                break
            data.extend([user['login'] for user in response_data])
            page += 1
        except json.JSONDecodeError:
            break  # Exit the loop if the response is not valid JSON
    return data


def load_previous_followers():
    """Load previous followers from a file."""
    if os.path.exists(PREVIOUS_FOLLOWERS_FILE):
        with open(PREVIOUS_FOLLOWERS_FILE, 'r') as file:
            return file.read().splitlines()
    return []


def save_followers(followers):
    with open(PREVIOUS_FOLLOWERS_FILE, 'w') as file:
        for follower in followers:
            file.write(follower + '\n')


def load_new_followers():
    if os.path.exists(NEW_FOLLOWERS_FILE):
        try:
            with open(NEW_FOLLOWERS_FILE, 'r') as file:
                content = file.read().strip()
                if content:
                    return json.loads(content)
        except json.JSONDecodeError:
            pass
    return {}


def save_new_followers(new_followers):
    with open(NEW_FOLLOWERS_FILE, 'w') as file:
        json.dump(new_followers, file)


def load_ignore_list():
    if os.path.exists(IGNORE_LIST_FILE):
        with open(IGNORE_LIST_FILE, 'r') as file:
            return file.read().splitlines()
    return []


@app.route('/')
def index():
    current_followers = get_github_data(FOLLOWERS_URL)
    current_following = get_github_data(FOLLOWING_URL)

    previous_followers = load_previous_followers()
    stored_new_followers = load_new_followers()
    ignore_list = load_ignore_list()

    unfollowers = list(set(previous_followers) - set(current_followers))
    not_following_back = list(set(current_following) - set(current_followers))
    new_followers = list(set(current_followers) - set(previous_followers))

    unfollowers = [user for user in unfollowers if user not in ignore_list]
    not_following_back = [user for user in not_following_back if user not in ignore_list]
    new_followers = [user for user in new_followers if user not in ignore_list]

    current_time = datetime.now()
    for follower in new_followers:
        if follower not in stored_new_followers:
            stored_new_followers[follower] = current_time.isoformat()

    recent_new_followers = {
        user: timestamp for user, timestamp in stored_new_followers.items()
        if datetime.fromisoformat(timestamp) >= current_time - timedelta(days=3)
    }

    save_followers(current_followers)
    save_new_followers(recent_new_followers)

    return render_template('index.html',
                           followers=current_followers,
                           following=current_following,
                           unfollowers=unfollowers,
                           not_following_back=not_following_back,
                           new_followers=recent_new_followers.keys())


if __name__ == "__main__":
    app.run(debug=True)

