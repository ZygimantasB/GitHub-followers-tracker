import requests
import json
import threading
import logging
from decouple import config
from utils import chunks, load_cache, save_cache

logger = logging.getLogger(__name__)

GITHUB_TOKEN = config('GITHUB_TOKEN')
GITHUB_USERNAME = config('GITHUB_USERNAME')

headers = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

def execute_github_graphql_query(query, variables=None):
    url = 'https://api.github.com/graphql'
    payload = {'query': query, 'variables': variables or {}}
    try:
        logger.debug(f"Executing GraphQL query: {query.strip()} with variables: {variables}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if 'errors' in result:
            error_messages = '; '.join([error['message'] for error in result['errors']])
            logger.error(f"GraphQL query failed: {error_messages}")
            raise Exception(f"GraphQL query failed: {error_messages}")
        logger.debug("GraphQL query executed successfully")
        return result
    except requests.exceptions.HTTPError as http_err:
        logger.error(f'HTTP error occurred: {http_err}')
        raise
    except Exception as err:
        logger.error(f'An error occurred: {err}')
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
    rate_limit = result['data']['rateLimit']
    logger.debug(f"Rate limit status: {rate_limit}")
    return rate_limit

def check_rate_limit():
    rate_limit = get_rate_limit_status()
    remaining = rate_limit['remaining']
    reset_at = rate_limit['resetAt']
    if remaining < 100:
        logger.warning(f'Approaching rate limit: {remaining} requests remaining until {reset_at}')
        return False
    logger.debug(f'Rate limit OK: {remaining} requests remaining')
    return True

def get_followers():
    logger.info("Fetching followers")
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
        batch_followers = [node['login'] for node in viewer['followers']['nodes']]
        followers.extend(batch_followers)
        logger.debug(f"Fetched {len(batch_followers)} followers in this batch")
        if viewer['followers']['pageInfo']['hasNextPage']:
            cursor = viewer['followers']['pageInfo']['endCursor']
        else:
            break
    logger.info(f"Total followers fetched: {len(followers)}")
    return followers

def get_following():
    logger.info("Fetching following")
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
        batch_following = [
            {
                'login': node['login'],
                'type': node['__typename'],
                'id': node['id']
            }
            for node in viewer['following']['nodes']
        ]
        following.extend(batch_following)
        logger.debug(f"Fetched {len(batch_following)} following in this batch")
        if viewer['following']['pageInfo']['hasNextPage']:
            cursor = viewer['following']['pageInfo']['endCursor']
        else:
            break
    logger.info(f"Total following fetched: {len(following)}")
    return following

def get_repository_owner_id(username):
    logger.debug(f"Fetching repository owner ID for {username}")
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
            logger.debug(f"Found repository owner ID for {username}: {owner['id']}")
            return owner['id'], owner['__typename']
        else:
            logger.warning(f"Repository owner not found for {username}")
            return None, None
    except Exception as e:
        logger.error(f'Error fetching repository owner ID for {username}: {e}')
        return None, None

def follow_user(username):
    logger.debug(f"Attempting to follow {username}")
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        logger.error(f"User not found: {username}")
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
        logger.error(f"Unsupported owner type for {username}: {owner_type}")
        return False, 'Unsupported owner type'

    try:
        execute_github_graphql_query(mutation, variables)
        logger.info(f"Successfully followed {username}")
        return True, ''
    except Exception as e:
        logger.error(f'Error following {username}: {e}')
        return False, str(e)

def unfollow_user(username):
    logger.debug(f"Attempting to unfollow {username}")
    owner_id, owner_type = get_repository_owner_id(username)
    if not owner_id:
        logger.error(f"User not found: {username}")
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
        logger.error(f"Unsupported owner type for {username}: {owner_type}")
        return False, 'Unsupported owner type'

    try:
        execute_github_graphql_query(mutation, variables)
        logger.info(f"Successfully unfollowed {username}")
        return True, ''
    except Exception as e:
        logger.error(f'Error unfollowing {username}: {e}')
        return False, str(e)

def bulk_follow_users(usernames):
    logger.info(f"Bulk following users: {usernames}")
    results = {}
    for username in usernames:
        success, message = follow_user(username)
        results[username] = {'success': success, 'message': message}
    return results

def bulk_unfollow_users(usernames):
    logger.info(f"Bulk unfollowing users: {usernames}")
    results = {}
    for username in usernames:
        success, message = unfollow_user(username)
        results[username] = {'success': success, 'message': message}
    return results

def get_multiple_users_following(user_logins):
    logger.info(f"Fetching following lists for multiple users")
    suggested_users = set()
    cache = load_cache()
    lock = threading.Lock()
    threads = []

    def fetch_following(chunk):
        nonlocal suggested_users
        if not check_rate_limit():
            logger.warning("Rate limit reached, stopping fetch")
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
                            logger.debug(f"Fetched following for {user_login}: {len(following_nodes)} users")
                else:
                    logger.warning(f"User data not found or not a User type for key: {key}")
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
    logger.info(f"Total suggested users fetched: {len(suggested_users)}")
    return suggested_users

def get_suggested_users(current_following, current_followers):
    logger.info("Calculating suggested users")
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
    logger.info(f"Suggested users ready: {len(suggested_users)} users")
    return suggested_users
