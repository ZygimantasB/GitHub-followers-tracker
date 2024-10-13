import os
import requests
import json
import random
from flask import Flask, render_template, request
from datetime import datetime, timedelta
from decouple import config

app = Flask(__name__)

GITHUB_USERNAME = config('GITHUB_USERNAME')
GITHUB_TOKEN = config('GITHUB_TOKEN')

headers = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

PREVIOUS_FOLLOWERS_FILE = 'previous_followers.txt'
NEW_FOLLOWERS_FILE = 'new_followers.json'
IGNORE_LIST_FILE = 'ignore_list.txt'

def execute_github_graphql_query(query, variables=None):
    url = 'https://api.github.com/graphql'
    payload = {'query': query, 'variables': variables or {}}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    if 'errors' in result:
        error_messages = '; '.join([error['message'] for error in result['errors']])
        raise Exception(f"GraphQL query failed: {error_messages}")
    return result

def get_followers_and_following():
    followers = []
    following = []
    followers_cursor = None
    following_cursor = None

    while True:
        query = '''
        query ($followersCursor: String, $followingCursor: String) {
          viewer {
            followers(first: 100, after: $followersCursor) {
              nodes {
                login
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
            following(first: 100, after: $followingCursor) {
              nodes {
                login
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        '''
        variables = {
            'followersCursor': followers_cursor,
            'followingCursor': following_cursor
        }
        result = execute_github_graphql_query(query, variables)
        viewer = result['data']['viewer']

        # Process followers
        followers.extend([node['login'] for node in viewer['followers']['nodes']])
        if viewer['followers']['pageInfo']['hasNextPage']:
            followers_cursor = viewer['followers']['pageInfo']['endCursor']
        else:
            followers_cursor = None

        # Process following
        following.extend([node['login'] for node in viewer['following']['nodes']])
        if viewer['following']['pageInfo']['hasNextPage']:
            following_cursor = viewer['following']['pageInfo']['endCursor']
        else:
            following_cursor = None

        if not followers_cursor and not following_cursor:
            break

    return followers, following

def load_previous_followers():
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

def get_suggested_users(current_following, current_followers):
    suggested_users = set()
    # Randomly select up to 20 users from your following list
    num_following = min(len(current_following), 20)
    limited_following = random.sample(current_following, num_following)

    for user_login in limited_following:
        try:
            user_following = get_user_following(user_login)
            suggested_users.update(user_following)
        except Exception as e:
            print(f"Skipping '{user_login}': {e}")
            continue

    # Remove users you're already following or who are following you
    suggested_users -= set(current_following)
    suggested_users -= set(current_followers)
    # Remove yourself
    suggested_users.discard(GITHUB_USERNAME)
    suggested_users = list(suggested_users)
    # Limit to 25 random users
    if len(suggested_users) > 25:
        suggested_users = random.sample(suggested_users, 25)
    return suggested_users

def get_user_following(username):
    following = []
    following_cursor = None

    while True:
        query = '''
        query ($username: String!, $followingCursor: String) {
          repositoryOwner(login: $username) {
            __typename
            ... on User {
              following(first: 100, after: $followingCursor) {
                nodes {
                  login
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
        }
        '''
        variables = {
            'username': username,
            'followingCursor': following_cursor
        }
        try:
            result = execute_github_graphql_query(query, variables)
            repository_owner = result['data']['repositoryOwner']
            if repository_owner is None:
                # User or organization not found
                print(f"'{username}' not found.")
                break

            if repository_owner['__typename'] != 'User':
                # The login corresponds to an organization
                print(f"'{username}' is an organization, skipping.")
                break

            following_data = repository_owner['following']
            following.extend([node['login'] for node in following_data['nodes']])
            if following_data['pageInfo']['hasNextPage']:
                following_cursor = following_data['pageInfo']['endCursor']
            else:
                break
        except Exception as e:
            # Log the error and continue with the next user
            print(f"Error fetching following for '{username}': {e}")
            break

    return following

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    mutation = '''
    mutation ($userId: ID!) {
      followUser(input: {userId: $userId}) {
        clientMutationId
      }
    }
    '''
    user_id = get_user_id(username)
    if not user_id:
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}
    variables = {'userId': user_id}
    try:
        result = execute_github_graphql_query(mutation, variables)
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        print(f"Error following '{username}': {e}")
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    mutation = '''
    mutation ($userId: ID!) {
      unfollowUser(input: {userId: $userId}) {
        clientMutationId
      }
    }
    '''
    user_id = get_user_id(username)
    if not user_id:
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}
    variables = {'userId': user_id}
    try:
        result = execute_github_graphql_query(mutation, variables)
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        print(f"Error unfollowing '{username}': {e}")
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

def get_user_id(username):
    query = '''
    query ($username: String!) {
      user(login: $username) {
        id
      }
    }
    '''
    variables = {'username': username}
    try:
        result = execute_github_graphql_query(query, variables)
        user = result['data']['user']
        return user['id'] if user else None
    except Exception as e:
        print(f"Error fetching user ID for '{username}': {e}")
        return None

@app.route('/')
def index():
    current_followers, current_following = get_followers_and_following()

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

    suggested_users = get_suggested_users(current_following, current_followers)

    return render_template('index.html',
                           followers=current_followers,
                           following=current_following,
                           unfollowers=unfollowers,
                           not_following_back=not_following_back,
                           new_followers=recent_new_followers.keys(),
                           suggested_users=suggested_users)

if __name__ == "__main__":
    app.run(debug=True)
