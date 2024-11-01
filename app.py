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
                __typename
                id
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
            following(first: 100, after: $followingCursor) {
              nodes {
                login
                __typename
                id
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

        # Process followers (only users with valid id)
        followers.extend([
            node['login']
            for node in viewer['followers']['nodes']
            if node['__typename'] == 'User' and node['id'] is not None
        ])
        if viewer['followers']['pageInfo']['hasNextPage']:
            followers_cursor = viewer['followers']['pageInfo']['endCursor']
        else:
            followers_cursor = None

        # Process following (include both users and organizations with valid id)
        for node in viewer['following']['nodes']:
            if node['id'] is not None:
                following.append({
                    'login': node['login'],
                    'type': node['__typename'],
                    'id': node['id']
                })
            else:
                logger.info(json.dumps({
                    'action': 'Skipped non-existent account',
                    'login': node['login']
                }))
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
                                __typename
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
                            cache[user_login] = [
                                node['login']
                                for node in following_nodes
                                if node['__typename'] == 'User'
                            ]
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
    # Use all following users (extract logins)
    user_logins = [f['login'] for f in current_following if f['type'] == 'User']
    logger.info(json.dumps({
        'action': 'Fetching suggested users'
    }))
    suggested_users = get_multiple_users_following(user_logins)

    # Remove users you're already following or who are following you
    current_following_logins = set([f['login'] for f in current_following])
    suggested_users -= current_following_logins
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

def get_repository_owner_id(username):
    query = '''
    query ($username: String!) {
      repositoryOwner(login: $username) {
        id
        __typename
      }
    }
    '''
    variables = {'username': username}
    try:
        result = execute_github_graphql_query(query, variables)
        owner = result['data']['repositoryOwner']
        if owner:
            return owner['id'], owner['__typename']
        else:
            return None, None
    except Exception as e:
        logger.error(json.dumps({
            'action': 'Error fetching repository owner ID',
            'username': username,
            'error': str(e)
        }))
        return None, None

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        return json.dumps({'success': False, 'message': 'User not found'}), 400, {'ContentType': 'application/json'}

    mutation_user = '''
    mutation ($userId: ID!) {
      followUser(input: {userId: $userId}) {
        clientMutationId
      }
    }
    '''
    mutation_org = '''
    mutation ($organizationId: ID!) {
      followOrganization(input: {organizationId: $organizationId}) {
        clientMutationId
      }
    }
    '''
    if owner_type == 'User':
        mutation = mutation_user
        variables = {'userId': owner_id}
    elif owner_type == 'Organization':
        mutation = mutation_org
        variables = {'organizationId': owner_id}
    else:
        return json.dumps({'success': False, 'message': 'Unsupported owner type'}), 400, {'ContentType': 'application/json'}

    try:
        result = execute_github_graphql_query(mutation, variables)
        logger.info(json.dumps({
            'action': 'Successfully followed',
            'username': username,
            'type': owner_type
        }))
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        logger.error(json.dumps({
            'action': 'Error following',
            'username': username,
            'type': owner_type,
            'error': str(e)
        }))
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        return json.dumps({'success': False, 'message': 'User not found'}), 400, {'ContentType': 'application/json'}

    mutation_user = '''
    mutation ($userId: ID!) {
      unfollowUser(input: {userId: $userId}) {
        clientMutationId
      }
    }
    '''
    mutation_org = '''
    mutation ($organizationId: ID!) {
      unfollowOrganization(input: {organizationId: $organizationId}) {
        clientMutationId
      }
    }
    '''
    if owner_type == 'User':
        mutation = mutation_user
        variables = {'userId': owner_id}
    elif owner_type == 'Organization':
        mutation = mutation_org
        variables = {'organizationId': owner_id}
    else:
        return json.dumps({'success': False, 'message': 'Unsupported owner type'}), 400, {'ContentType': 'application/json'}

    try:
        result = execute_github_graphql_query(mutation, variables)
        logger.info(json.dumps({
            'action': 'Successfully unfollowed',
            'username': username,
            'type': owner_type
        }))
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        logger.error(json.dumps({
            'action': 'Error unfollowing',
            'username': username,
            'type': owner_type,
            'error': str(e)
        }))
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

@app.route('/bulk_follow', methods=['POST'])
def bulk_follow():
    usernames = request.json.get('usernames', [])
    results = {}
    for username in usernames:
        try:
            owner_id, owner_type = get_repository_owner_id(username)
            if not owner_id:
                results[username] = {'success': False, 'message': 'User not found'}
                continue

            mutation_user = '''
            mutation ($userId: ID!) {
              followUser(input: {userId: $userId}) {
                clientMutationId
              }
            }
            '''
            mutation_org = '''
            mutation ($organizationId: ID!) {
              followOrganization(input: {organizationId: $organizationId}) {
                clientMutationId
              }
            }
            '''
            if owner_type == 'User':
                mutation = mutation_user
                variables = {'userId': owner_id}
            elif owner_type == 'Organization':
                mutation = mutation_org
                variables = {'organizationId': owner_id}
            else:
                results[username] = {'success': False, 'message': 'Unsupported owner type'}
                continue

            result = execute_github_graphql_query(mutation, variables)
            logger.info(json.dumps({
                'action': 'Successfully followed',
                'username': username,
                'type': owner_type
            }))
            results[username] = {'success': True}
        except Exception as e:
            logger.error(json.dumps({
                'action': 'Error following',
                'username': username,
                'error': str(e)
            }))
            results[username] = {'success': False, 'message': str(e)}
    return json.dumps(results), 200, {'ContentType': 'application/json'}

@app.route('/bulk_unfollow', methods=['POST'])
def bulk_unfollow():
    usernames = request.json.get('usernames', [])
    results = {}
    for username in usernames:
        try:
            owner_id, owner_type = get_repository_owner_id(username)
            if not owner_id:
                results[username] = {'success': False, 'message': 'User not found'}
                continue

            mutation_user = '''
            mutation ($userId: ID!) {
              unfollowUser(input: {userId: $userId}) {
                clientMutationId
              }
            }
            '''
            mutation_org = '''
            mutation ($organizationId: ID!) {
              unfollowOrganization(input: {organizationId: $organizationId}) {
                clientMutationId
              }
            }
            '''
            if owner_type == 'User':
                mutation = mutation_user
                variables = {'userId': owner_id}
            elif owner_type == 'Organization':
                mutation = mutation_org
                variables = {'organizationId': owner_id}
            else:
                results[username] = {'success': False, 'message': 'Unsupported owner type'}
                continue

            result = execute_github_graphql_query(mutation, variables)
            logger.info(json.dumps({
                'action': 'Successfully unfollowed',
                'username': username,
                'type': owner_type
            }))
            results[username] = {'success': True}
        except Exception as e:
            logger.error(json.dumps({
                'action': 'Error unfollowing',
                'username': username,
                'error': str(e)
            }))
            results[username] = {'success': False, 'message': str(e)}
    return json.dumps(results), 200, {'ContentType': 'application/json'}

@app.route('/')
def index():
    logger.info(json.dumps({
        'action': 'Loading index page'
    }))
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    data_type = request.args.get('type')
    logger.info(json.dumps({
        'action': 'Fetching data via get_data route',
        'data_type': data_type
    }))

    # Load necessary data files
    previous_followers = load_previous_followers()
    stored_new_followers = load_new_followers()
    ignore_list = load_ignore_list()

    current_time = datetime.now()

    # Now, depending on data_type, fetch the appropriate data
    if data_type == 'followers':
        current_followers, _ = get_followers_and_following()
        # Apply ignore list
        current_followers = [user for user in current_followers if user not in ignore_list]
        data = {'followers': current_followers}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    elif data_type == 'following':
        _, current_following = get_followers_and_following()
        # Apply ignore list
        current_following = [f for f in current_following if f['login'] not in ignore_list]
        data = {'following': current_following}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    elif data_type == 'new_followers':
        current_followers, _ = get_followers_and_following()
        current_follower_logins = set(current_followers)
        new_followers = list(current_follower_logins - set(previous_followers))
        # Apply ignore list
        new_followers = [user for user in new_followers if user not in ignore_list]
        # Update stored_new_followers
        for follower in new_followers:
            if follower not in stored_new_followers:
                stored_new_followers[follower] = current_time.isoformat()
        recent_new_followers = {
            user: timestamp for user, timestamp in stored_new_followers.items()
            if datetime.fromisoformat(timestamp) >= current_time - timedelta(days=3)
        }
        save_new_followers(recent_new_followers)
        data = {'new_followers': list(recent_new_followers.keys())}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    elif data_type == 'unfollowers':
        current_followers, _ = get_followers_and_following()
        current_follower_logins = set(current_followers)
        unfollowers = list(set(previous_followers) - current_follower_logins)
        # Apply ignore list
        unfollowers = [user for user in unfollowers if user not in ignore_list]
        data = {'unfollowers': unfollowers}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    elif data_type == 'not_following_back':
        current_followers, current_following = get_followers_and_following()
        current_follower_logins = set(current_followers)
        not_following_back = [
            f['login'] for f in current_following
            if f['login'] not in current_follower_logins and f['type'] == 'User' and f['id'] is not None
        ]
        # Apply ignore list
        not_following_back = [user for user in not_following_back if user not in ignore_list]
        data = {'not_following_back': not_following_back}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    elif data_type == 'suggested_users':
        current_followers, current_following = get_followers_and_following()
        suggested_users = get_suggested_users(current_following, current_followers)
        # Apply ignore list
        suggested_users = [user for user in suggested_users if user not in ignore_list]
        data = {'suggested_users': suggested_users}
        return json.dumps(data), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps({'error': 'Invalid data type requested'}), 400, {'ContentType': 'application/json'}

if __name__ == "__main__":
    app.run(debug=True)
