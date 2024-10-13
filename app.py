import os
import requests
import json
import random
import threading
import logging
from logging.handlers import RotatingFileHandler
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
CACHE_FILE = 'user_following_cache.json'
LOG_FILE = 'app.log'

# Set up structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2)

# Create formatters
formatter = logging.Formatter(
    '{"time": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def execute_github_graphql_query(query, variables=None):
    url = 'https://api.github.com/graphql'
    payload = {'query': query, 'variables': variables or {}}
    logger.debug(json.dumps({
        'action': 'Sending GraphQL query',
        'query': query.strip(),
        'variables': variables
    }))
    try:
        response = requests.post(url, headers=headers, json=payload)
        logger.debug(json.dumps({
            'action': 'Received response',
            'status_code': response.status_code
        }))
        response.raise_for_status()
        result = response.json()
        logger.debug(json.dumps({
            'action': 'Response JSON',
            'data': result
        }))
        if 'errors' in result:
            error_messages = '; '.join([error['message'] for error in result['errors']])
            logger.error(json.dumps({
                'action': 'GraphQL errors',
                'errors': result['errors']
            }))
            raise Exception(f"GraphQL query failed: {error_messages}")
        return result
    except requests.exceptions.HTTPError as http_err:
        logger.error(json.dumps({
            'action': 'HTTP error occurred',
            'error': str(http_err),
            'response_content': response.text
        }))
        raise
    except Exception as err:
        logger.error(json.dumps({
            'action': 'Other error occurred',
            'error': str(err)
        }))
        raise

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
        logger.debug(json.dumps({
            'action': 'Fetching followers and following',
            'variables': variables
        }))
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

    logger.info(json.dumps({
        'action': 'Fetched followers and following',
        'total_followers': len(followers),
        'total_following': len(following)
    }))

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
            logger.error(json.dumps({
                'action': 'Failed to decode new followers JSON.'
            }))
    return {}

def save_new_followers(new_followers):
    with open(NEW_FOLLOWERS_FILE, 'w') as file:
        json.dump(new_followers, file)

def load_ignore_list():
    if os.path.exists(IGNORE_LIST_FILE):
        with open(IGNORE_LIST_FILE, 'r') as file:
            return file.read().splitlines()
    return []

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logger.error(json.dumps({
                    'action': 'Failed to decode cache JSON.'
                }))
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as file:
        json.dump(cache, file)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_rate_limit_status():
    query = '''
    {
      rateLimit {
        remaining
        resetAt
      }
    }
    '''
    logger.debug(json.dumps({
        'action': 'Checking rate limit status'
    }))
    result = execute_github_graphql_query(query)
    return result['data']['rateLimit']

def check_rate_limit():
    rate_limit = get_rate_limit_status()
    remaining = rate_limit['remaining']
    reset_at = rate_limit['resetAt']
    logger.info(json.dumps({
        'action': 'Rate limit status',
        'remaining': remaining,
        'resetAt': reset_at
    }))
    if remaining < 100:
        logger.warning(json.dumps({
            'action': 'Approaching rate limit',
            'remaining': remaining,
            'resetAt': reset_at
        }))
        return False
    return True

def get_multiple_users_following(user_logins):
    suggested_users = set()
    cache = load_cache()
    lock = threading.Lock()
    threads = []

    def fetch_following(chunk):
        nonlocal suggested_users
        if not check_rate_limit():
            return
        query_fragments = []
        for index, login in enumerate(chunk):
            query_fragments.append(f'''
                user_{index}: repositoryOwner(login: "{login}") {{
                    __typename
                    ... on User {{
                        login
                        following(first: 100) {{
                            nodes {{
                                login
                            }}
                            pageInfo {{
                                hasNextPage
                                endCursor
                            }}
                        }}
                    }}
                }}
            ''')
        query = f'''
        query {{
            {"".join(query_fragments)}
        }}
        '''
        logger.debug(json.dumps({
            'action': 'Fetching following for users',
            'users': chunk
        }))
        try:
            result = execute_github_graphql_query(query)
            data = result.get('data', {})
            for key in data:
                user_data = data[key]
                if user_data is None:
                    logger.warning(json.dumps({
                        'action': 'User not found',
                        'key': key
                    }))
                    continue
                if user_data['__typename'] == 'User':
                    following_nodes = user_data['following']['nodes']
                    user_login = user_data.get('login')
                    if user_login:
                        with lock:
                            cache[user_login] = [node['login'] for node in following_nodes]
                            suggested_users.update(cache[user_login])
                            logger.debug(json.dumps({
                                'action': 'Fetched following',
                                'user': user_login,
                                'following_count': len(cache[user_login])
                            }))
                    else:
                        logger.warning(json.dumps({
                            'action': 'User login not found',
                            'key': key
                        }))
                else:
                    login = user_data.get('login', 'Unknown')
                    logger.warning(json.dumps({
                        'action': 'Not a user or not found',
                        'login': login
                    }))
        except Exception as e:
            logger.error(json.dumps({
                'action': 'Error fetching data for users',
                'users': chunk,
                'error': str(e)
            }))

    # Split user logins into chunks and create threads
    for chunk in chunks(user_logins, 5):  # Adjust chunk size as needed
        thread = threading.Thread(target=fetch_following, args=(chunk,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    save_cache(cache)
    return suggested_users

def get_suggested_users(current_following, current_followers):
    # Use all following users
    user_logins = current_following
    logger.info(json.dumps({
        'action': 'Fetching suggested users'
    }))
    suggested_users = get_multiple_users_following(user_logins)

    # Remove users you're already following or who are following you
    suggested_users -= set(current_following)
    suggested_users -= set(current_followers)
    suggested_users.discard(GITHUB_USERNAME)

    # Convert to list and limit to 25 users
    suggested_users = list(suggested_users)
    if len(suggested_users) > 25:
        suggested_users = random.sample(suggested_users, 25)
    logger.info(json.dumps({
        'action': 'Total suggested users',
        'count': len(suggested_users)
    }))
    return suggested_users

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
        logger.error(json.dumps({
            'action': 'Error fetching user ID',
            'username': username,
            'error': str(e)
        }))
        return None

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
        logger.info(json.dumps({
            'action': 'Successfully followed user',
            'username': username
        }))
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        logger.error(json.dumps({
            'action': 'Error following user',
            'username': username,
            'error': str(e)
        }))
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
        logger.info(json.dumps({
            'action': 'Successfully unfollowed user',
            'username': username
        }))
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        logger.error(json.dumps({
            'action': 'Error unfollowing user',
            'username': username,
            'error': str(e)
        }))
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

@app.route('/')
def index():
    logger.info(json.dumps({
        'action': 'Loading index page'
    }))
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
