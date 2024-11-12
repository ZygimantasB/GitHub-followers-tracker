// script.js

function toggleVisibility(id) {
    const element = document.getElementById(id);
    const list = element.querySelector('.collapsible-list');
    if (list.classList.contains('open')) {
        list.classList.remove('open');
    } else {
        list.classList.add('open');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Handle Load Data buttons
    document.querySelectorAll('.load-data-button').forEach(button => {
        button.addEventListener('click', function() {
            const dataType = this.getAttribute('data-type');
            fetchData(dataType);
        });
    });

    // Handle bulk follow/unfollow buttons
    document.getElementById('follow-all-new-followers-button').addEventListener('click', function() {
        bulkAction('new-followers-list', '/bulk_follow');
    });

    document.getElementById('unfollow-all-followers-button').addEventListener('click', function() {
        bulkAction('followers-list', '/bulk_unfollow');
    });

    document.getElementById('unfollow-all-following-button').addEventListener('click', function() {
        bulkAction('following-list', '/bulk_unfollow');
    });

    document.getElementById('unfollow-all-unfollowers-button').addEventListener('click', function() {
        bulkAction('unfollowers-list', '/bulk_unfollow');
    });

    document.getElementById('unfollow-all-not-following-back-button').addEventListener('click', function() {
        bulkAction('not-following-back-list', '/bulk_unfollow');
    });

    document.getElementById('follow-selected-suggested-users-button').addEventListener('click', function() {
        followSelectedUsers();
    });

    // Add this event listener for the "Follow All" button
    document.getElementById('follow-all-suggested-users-button').addEventListener('click', function() {
        followAllSuggestedUsers();
    });

    // Handle Search Form Submission
    const searchForm = document.getElementById('search-form');
    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const username = document.getElementById('search-username').value.trim();
        if (username) {
            searchUser(username);
        }
    });

    async function searchUser(username) {
        try {
            const response = await fetch(`/check_follow?username=${encodeURIComponent(username)}`);
            const data = await response.json();
            const searchResultDiv = document.getElementById('search-result');
            if (data.error) {
                searchResultDiv.textContent = `Error: ${data.error}`;
            } else {
                const followsYouText = data.follows_you ? 'follows you' : 'does not follow you';
                searchResultDiv.textContent = `${username} ${followsYouText}.`;
            }
        } catch (error) {
            console.error('Error searching user:', error);
        }
    }

    async function fetchData(dataType) {
        try {
            showLoadingIndicator();
            const response = await fetch(`/get_data?type=${dataType}`);
            const data = await response.json();
            populateData(dataType, data);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            hideLoadingIndicator();
        }
    }

    async function bulkAction(listId, endpoint) {
        const list = document.getElementById(listId);
        const usernames = Array.from(list.querySelectorAll('.list-item .username')).map(span => span.textContent);
        if (usernames.length > 0) {
            try {
                showLoadingIndicator();
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ usernames: usernames })
                });
                const results = await response.json();
                usernames.forEach(username => {
                    if (results[username] && results[username].success) {
                        const li = list.querySelector(`.list-item[data-username="${username}"]`);
                        if (li) {
                            li.style.display = 'none';
                        }
                    } else {
                        console.error(`Failed to process ${username}: ${results[username].message}`);
                    }
                });
            } catch (error) {
                console.error('Error during bulk action:', error);
            } finally {
                hideLoadingIndicator();
            }
        }
    }

    async function followSelectedUsers() {
        const list = document.getElementById('suggested-users-list');
        const selectedCheckboxes = list.querySelectorAll('.list-item input[type="checkbox"]:checked');
        const usernames = Array.from(selectedCheckboxes).map(checkbox => checkbox.dataset.username);
        if (usernames.length > 0) {
            try {
                showLoadingIndicator();
                const response = await fetch('/bulk_follow', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ usernames: usernames })
                });
                const results = await response.json();
                usernames.forEach(username => {
                    if (results[username] && results[username].success) {
                        const li = list.querySelector(`.list-item[data-username="${username}"]`);
                        if (li) {
                            li.style.display = 'none';
                        }
                    } else {
                        console.error(`Failed to follow ${username}: ${results[username].message}`);
                    }
                });
            } catch (error) {
                console.error('Error during following selected users:', error);
            } finally {
                hideLoadingIndicator();
            }
        } else {
            alert('No users selected.');
        }
    }

    // Add this function for the "Follow All" action
    async function followAllSuggestedUsers() {
        const list = document.getElementById('suggested-users-list');
        const usernames = Array.from(list.querySelectorAll('.list-item')).map(li => li.dataset.username);
        if (usernames.length > 0) {
            try {
                showLoadingIndicator();
                const response = await fetch('/bulk_follow', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ usernames: usernames })
                });
                const results = await response.json();
                usernames.forEach(username => {
                    if (results[username] && results[username].success) {
                        const li = list.querySelector(`.list-item[data-username="${username}"]`);
                        if (li) {
                            li.style.display = 'none';
                        }
                    } else {
                        console.error(`Failed to follow ${username}: ${results[username].message}`);
                    }
                });
            } catch (error) {
                console.error('Error during following all suggested users:', error);
            } finally {
                hideLoadingIndicator();
            }
        } else {
            alert('No users available to follow.');
        }
    }

    function populateData(dataType, data) {
        const counts = {
            'followers': 'followers-count',
            'following': 'following-count',
            'new_followers': 'new-followers-count',
            'unfollowers': 'unfollowers-count',
            'not_following_back': 'not-following-back-count',
            'suggested_users': 'suggested-users-count',
            'users_more_following': 'users-more-following-count'
        };

        const lists = {
            'followers': 'followers-list',
            'following': 'following-list',
            'new_followers': 'new-followers-list',
            'unfollowers': 'unfollowers-list',
            'not_following_back': 'not-following-back-list',
            'suggested_users': 'suggested-users-list',
            'users_more_following': 'users-more-following-list'
        };

        const dataKeys = {
            'followers': 'followers',
            'following': 'following',
            'new_followers': 'new_followers',
            'unfollowers': 'unfollowers',
            'not_following_back': 'not_following_back',
            'suggested_users': 'suggested_users',
            'users_more_following': 'users_more_following'
        };

        const countElement = document.getElementById(counts[dataType]);
        const listElement = document.getElementById(lists[dataType]);
        const dataList = data[dataKeys[dataType]];

        // Update counts
        if (countElement) {
            countElement.textContent = dataList.length;
        }
        // Clear existing list
        listElement.innerHTML = '';

        dataList.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-item';
            li.dataset.username = item.login || item;

            const userInfoDiv = document.createElement('div');
            userInfoDiv.className = 'user-info';

            // Add avatar if available
            if (item.avatar_url) {
                const avatarImg = document.createElement('img');
                avatarImg.src = item.avatar_url;
                avatarImg.alt = `${item.login}'s avatar`;
                avatarImg.className = 'avatar';
                userInfoDiv.appendChild(avatarImg);
            }

            const usernameSpan = document.createElement('span');
            usernameSpan.className = 'username';
            usernameSpan.textContent = item.login || item;

            userInfoDiv.appendChild(usernameSpan);

            // Add follower and following counts if available
            if (item.followers !== undefined && item.following !== undefined) {
                const countsSpan = document.createElement('span');
                countsSpan.className = 'counts';
                countsSpan.textContent = `Followers: ${item.followers}, Following: ${item.following}`;
                userInfoDiv.appendChild(countsSpan);
            }

            // Add additional information for suggested users
            if (dataType === 'suggested_users') {
                // Add checkbox for selecting users
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.dataset.username = item.login || item;
                li.appendChild(checkbox);
            }

            li.appendChild(userInfoDiv);

            const buttonGroup = document.createElement('div');
            buttonGroup.className = 'button-group';

            if (['following', 'followers', 'not_following_back', 'unfollowers', 'users_more_following'].includes(dataType)) {
                const unfollowButton = document.createElement('button');
                unfollowButton.className = 'btn-unfollow';
                unfollowButton.textContent = 'Unfollow';
                unfollowButton.addEventListener('click', function() {
                    unfollowUser(item.login || item, li);
                });
                buttonGroup.appendChild(unfollowButton);
            }

            if (['new_followers'].includes(dataType)) {
                const followButton = document.createElement('button');
                followButton.className = 'btn-follow';
                followButton.textContent = 'Follow';
                followButton.addEventListener('click', function() {
                    followUser(item.login || item, li);
                });
                buttonGroup.appendChild(followButton);
            }

            if (buttonGroup.childElementCount > 0) {
                li.appendChild(buttonGroup);
            }

            listElement.appendChild(li);
        });
    }

    function showLoadingIndicator() {
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'block';
    }

    function hideLoadingIndicator() {
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'none';
    }

    async function unfollowUser(username, listItem) {
        try {
            const response = await fetch(`/unfollow/${username}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            if (data.success) {
                listItem.style.display = 'none';
            } else {
                alert('Failed to unfollow ' + username);
            }
        } catch (error) {
            console.error('Error unfollowing user:', error);
        }
    }

    async function followUser(username, listItem) {
        try {
            const response = await fetch(`/follow/${username}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            if (data.success) {
                listItem.style.display = 'none';
            } else {
                alert('Failed to follow ' + username);
            }
        } catch (error) {
            console.error('Error following user:', error);
        }
    }
});
