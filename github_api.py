import requests
import json
import threading
import logging
from decouple import config
from utils import chunks, load_cache, save_cache

GITHUB_TOKEN = config('GITHUB_TOKEN')
GITHUB_USERNAME = config('GITHUB_USERNAME')

headers = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

logger = logging.getLogger(__name__)

def execute_github_graphql_query(query, variables=None):
    url = 'https://api.github.com/graphql'
    payload = {'query': query, 'variables': variables or {}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if 'errors' in result:
            error_messages = '; '.join([error['message'] for error in result['errors']])
            raise Exception(f"GraphQL query failed: {error_messages}")
        return result
    except requests.exceptions.HTTPError as http_err:
        logger.error(f'HTTP error occurred: {http_err}')
        raise
    except Exception as err:
        logger.error(f'Other error occurred: {err}')
        raise

def get_rate_limit_status():
    query = '''
    {
      rateLimit {
        remaining
        resetAt
      }
    }
    '''
    result = execute_github_graphql_query(query)
    return result['data']['rateLimit']

def check_rate_limit():
    rate_limit = get_rate_limit_status()
    remaining = rate_limit['remaining']
    reset_at = rate_limit['resetAt']
    if remaining < 100:
        logger.warning(f'Approaching rate limit: {remaining} requests remaining until {reset_at}')
        return False
    return True

def get_followers():
    followers = []
    cursor = None
    while True:
        query = '''
        query ($cursor: String) {
          viewer {
            followers(first: 100, after: $cursor) {
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
        variables = {'cursor': cursor}
        result = execute_github_graphql_query(query, variables)
        viewer = result['data']['viewer']
        followers.extend([node['login'] for node in viewer['followers']['nodes']])
        if viewer['followers']['pageInfo']['hasNextPage']:
            cursor = viewer['followers']['pageInfo']['endCursor']
        else:
            break
    return followers

def get_following():
    following = []
    cursor = None
    while True:
        query = '''
        query ($cursor: String) {
          viewer {
            following(first: 100, after: $cursor) {
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
        variables = {'cursor': cursor}
        result = execute_github_graphql_query(query, variables)
        viewer = result['data']['viewer']
        for node in viewer['following']['nodes']:
            following.append({
                'login': node['login'],
                'type': node['__typename'],
                'id': node['id']
            })
        if viewer['following']['pageInfo']['hasNextPage']:
            cursor = viewer['following']['pageInfo']['endCursor']
        else:
            break
    return following

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
        logger.error(f'Error fetching repository owner ID for {username}: {e}')
        return None, None

def follow_user(username):
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        return False, 'User not found'

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
        return False, 'Unsupported owner type'

    try:
        execute_github_graphql_query(mutation, variables)
        logger.info(f'Successfully followed {username}')
        return True, ''
    except Exception as e:
        logger.error(f'Error following {username}: {e}')
        return False, str(e)

def unfollow_user(username):
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        return False, 'User not found'

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
        return False, 'Unsupported owner type'

    try:
        execute_github_graphql_query(mutation, variables)
        logger.info(f'Successfully unfollowed {username}')
        return True, ''
    except Exception as e:
        logger.error(f'Error unfollowing {username}: {e}')
        return False, str(e)

def bulk_follow_users(usernames):
    results = {}
    for username in usernames:
        success, message = follow_user(username)
        results[username] = {'success': success, 'message': message}
    return results

def bulk_unfollow_users(usernames):
    results = {}
    for username in usernames:
        success, message = unfollow_user(username)
        results[username] = {'success': success, 'message': message}
    return results

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
                        }}
                    }}
                }}
            ''')
        query = f'''
        query {{
            {"".join(query_fragments)}
        }}
        '''
        try:
            result = execute_github_graphql_query(query)
            data = result.get('data', {})
            for key in data:
                user_data = data[key]
                if user_data and user_data['__typename'] == 'User':
                    following_nodes = user_data['following']['nodes']
                    user_login = user_data.get('login')
                    if user_login:
                        with lock:
                            cache[user_login] = [node['login'] for node in following_nodes]
                            suggested_users.update(cache[user_login])
        except Exception as e:
            logger.error(f'Error fetching data for users {chunk}: {e}')

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
    user_logins = [f['login'] for f in current_following if f['type'] == 'User']
    suggested_users = get_multiple_users_following(user_logins)

    # Remove users you're already following or who are following you
    current_following_logins = set([f['login'] for f in current_following])
    suggested_users -= current_following_logins
    suggested_users -= set(current_followers)
    suggested_users.discard(GITHUB_USERNAME)

    # Convert to list and limit to 25 users
    suggested_users = list(suggested_users)
    if len(suggested_users) > 25:
        import random
        suggested_users = random.sample(suggested_users, 25)
    return suggested_users
