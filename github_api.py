import requests
import json
import logging
import time
import random
from decouple import config
from utils import chunks

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
        if response.status_code == 403:
            logger.error('403 Forbidden: Check your token permissions and rate limits.')
            raise Exception('403 Forbidden: Check your token permissions and rate limits.')
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
        limit
        cost
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
    logger.info(f'Rate limit: {remaining} remaining, resets at {reset_at}')
    if remaining < 100:
        logger.warning(f'Approaching rate limit: {remaining} requests remaining until {reset_at}')
        return False
    return True

def get_random_users_with_more_following():
    logger.info("Fetching random users with more following than followers")
    accumulated_users = []
    per_page = 100  # Maximum allowed by the API
    since = 0  # Starting user ID
    try:
        while len(accumulated_users) < 2000:  # Fetch until we have enough users
            response = requests.get(
                f'https://api.github.com/users?per_page={per_page}&since={since}',
                headers=headers
            )
            if response.status_code == 403:
                logger.error('403 Forbidden: Check your token permissions and rate limits.')
                raise Exception('403 Forbidden: Check your token permissions and rate limits.')
            response.raise_for_status()
            users = response.json()
            if not users:
                break  # No more users to fetch
            accumulated_users.extend(users)
            since = users[-1]['id']  # Update 'since' to the last user's ID
            if len(accumulated_users) >= 2000:
                break
            time.sleep(1)  # Sleep to respect rate limits
        # Fetch detailed info
        usernames = [user['login'] for user in accumulated_users]
        users_info = get_users_info_with_more_following(usernames)
        logger.info(f"Users with more following fetched: {len(users_info)} users")
        # Select random 25 users
        random_users = random.sample(users_info, min(25, len(users_info)))
        return random_users
    except Exception as e:
        logger.error(f'Error fetching random users with more following: {e}')
        return []

def get_users_info_with_more_following(usernames):
    logger.info(f"Fetching info for users: {usernames}")
    users_info = []
    for chunk in chunks(usernames, 10):  # Increased chunk size to 10
        try:
            query_fragments = []
            for index, username in enumerate(chunk):
                query_fragments.append(f'''
                    user_{index}: user(login: "{username}") {{
                        login
                        followers {{
                            totalCount
                        }}
                        following {{
                            totalCount
                        }}
                        bio
                        repositories(privacy: PUBLIC) {{
                            totalCount
                        }}
                    }}
                ''')
            query = f'''
            query {{
                {"".join(query_fragments)}
            }}
            '''
            result = execute_github_graphql_query(query)
            data = result.get('data', {})
            for key in data:
                user_data = data[key]
                if user_data:
                    followers_count = user_data['followers']['totalCount']
                    following_count = user_data['following']['totalCount']
                    if following_count > followers_count:
                        users_info.append({
                            'login': user_data['login'],
                            'followers': followers_count,
                            'following': following_count,
                            'bio': user_data.get('bio', ''),
                            'public_repos': user_data['repositories']['totalCount'],
                        })
            time.sleep(1)
        except Exception as e:
            logger.error(f'Error fetching user info: {e}')
            if 'rate limit' in str(e).lower():
                logger.info('Waiting for rate limit reset...')
                time.sleep(60)  # Wait 60 seconds before retrying
            else:
                continue
    return users_info

def get_users_info(usernames):
    logger.info(f"Fetching info for users: {usernames}")
    users_info = []
    for chunk in chunks(usernames, 5):  # Chunk size of 5
        try:
            query_fragments = []
            for index, username in enumerate(chunk):
                query_fragments.append(f'''
                    user_{index}: user(login: "{username}") {{
                        login
                        followers {{
                            totalCount
                        }}
                        following {{
                            totalCount
                        }}
                        bio
                        repositories(privacy: PUBLIC) {{
                            totalCount
                        }}
                    }}
                ''')
            query = f'''
            query {{
                {"".join(query_fragments)}
            }}
            '''
            result = execute_github_graphql_query(query)
            data = result.get('data', {})
            for key in data:
                user_data = data[key]
                if user_data:
                    users_info.append({
                        'login': user_data['login'],
                        'followers': user_data['followers']['totalCount'],
                        'following': user_data['following']['totalCount'],
                        'bio': user_data.get('bio', ''),
                        'public_repos': user_data['repositories']['totalCount'],
                    })
            time.sleep(1)
        except Exception as e:
            logger.error(f'Error fetching user info: {e}')
            if 'rate limit' in str(e).lower():
                logger.info('Waiting for rate limit reset...')
                time.sleep(60)  # Wait 60 seconds before retrying
            else:
                continue
    return users_info

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
        time.sleep(1)  # Delay to prevent hitting rate limits
    return results

def bulk_unfollow_users(usernames):
    logger.info(f"Bulk unfollowing users: {usernames}")
    results = {}
    for username in usernames:
        success, message = unfollow_user(username)
        results[username] = {'success': success, 'message': message}
        time.sleep(1)  # Delay to prevent hitting rate limits
    return results

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

def get_followers_with_counts():
    logger.info("Fetching followers with counts")
    followers = []
    cursor = None
    while True:
        try:
            query = '''
            query ($cursor: String) {
              viewer {
                followers(first: 100, after: $cursor) {
                  nodes {
                    login
                    followers {
                      totalCount
                    }
                    following {
                      totalCount
                    }
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
            batch_followers = [
                {
                    'login': node['login'],
                    'followers': node['followers']['totalCount'],
                    'following': node['following']['totalCount']
                }
                for node in viewer['followers']['nodes']
            ]
            followers.extend(batch_followers)
            logger.debug(f"Fetched {len(batch_followers)} followers in this batch")
            if viewer['followers']['pageInfo']['hasNextPage']:
                cursor = viewer['followers']['pageInfo']['endCursor']
                time.sleep(1)  # Delay to prevent hitting rate limits
            else:
                break
        except Exception as e:
            logger.error(f'Error fetching followers with counts: {e}')
            break
    logger.info(f"Total followers fetched: {len(followers)}")
    return followers

def get_followers():
    logger.info("Fetching followers")
    followers = []
    cursor = None
    while True:
        try:
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
                time.sleep(1)
            else:
                break
        except Exception as e:
            logger.error(f'Error fetching followers: {e}')
            break
    logger.info(f"Total followers fetched: {len(followers)}")
    return followers

def get_following():
    logger.info("Fetching following")
    following = []
    cursor = None
    while True:
        try:
            query = '''
            query ($cursor: String) {
              viewer {
                following(first: 100, after: $cursor) {
                  nodes {
                    login
                    __typename
                    id
                    followers {
                        totalCount
                    }
                    following {
                        totalCount
                    }
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
                    'id': node['id'],
                    'followers': node['followers']['totalCount'],
                    'following': node['following']['totalCount']
                }
                for node in viewer['following']['nodes']
            ]
            following.extend(batch_following)
            logger.debug(f"Fetched {len(batch_following)} following in this batch")
            if viewer['following']['pageInfo']['hasNextPage']:
                cursor = viewer['following']['pageInfo']['endCursor']
                time.sleep(1)
            else:
                break
        except Exception as e:
            logger.error(f'Error fetching following: {e}')
            break
    logger.info(f"Total following fetched: {len(following)}")
    return following

def check_if_user_follows_viewer(username):
    logger.debug(f"Checking if user {username} follows the viewer")
    query = '''
    query ($username: String!) {
      user(login: $username) {
        isFollowingViewer
      }
    }
    '''
    variables = {'username': username}
    try:
        result = execute_github_graphql_query(query, variables)
        user_data = result['data']['user']
        if user_data is None:
            logger.error(f"User {username} not found")
            raise Exception('User not found')
        follows_viewer = user_data['isFollowingViewer']
        logger.debug(f"User {username} follows viewer: {follows_viewer}")
        return follows_viewer
    except Exception as e:
        logger.error(f'Error checking if user {username} follows viewer: {e}')
        raise
