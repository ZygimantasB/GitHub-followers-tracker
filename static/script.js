// script.js

function toggleVisibility(id) {
    const element = document.getElementById(id);
    if (element.style.maxHeight) {
        element.style.maxHeight = null;
    } else {
        element.style.maxHeight = element.scrollHeight + "px";
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

            const usernameSpan = document.createElement('span');
            usernameSpan.className = 'username';
            usernameSpan.textContent = item.login || item;

            userInfoDiv.appendChild(usernameSpan);

            // Add follower and following counts if available
            if (item.followers !== undefined && item.following !== undefined) {
                const countsSpan = document.createElement('span');
                countsSpan.className = 'counts';
                countsSpan.textContent = ` (Followers: ${item.followers}, Following: ${item.following})`;
                userInfoDiv.appendChild(countsSpan);

                // For "Users Following More Than Followed", show the difference
                if (dataType === 'users_more_following') {
                    const differenceSpan = document.createElement('span');
                    differenceSpan.className = 'difference';
                    const diff = item.following - item.followers;
                    differenceSpan.textContent = ` Difference: ${diff}`;
                    userInfoDiv.appendChild(differenceSpan);
                }
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
                const unfollowForm = document.createElement('form');
                unfollowForm.action = `/unfollow/${item.login || item}`;
                unfollowForm.method = 'post';
                unfollowForm.className = 'unfollow-form';

                const unfollowButton = document.createElement('button');
                unfollowButton.type = 'submit';
                unfollowButton.className = 'btn-unfollow';
                unfollowButton.textContent = 'Unfollow';

                unfollowForm.appendChild(unfollowButton);
                buttonGroup.appendChild(unfollowForm);
            }

            if (['new_followers'].includes(dataType)) {
                const followForm = document.createElement('form');
                followForm.action = `/follow/${item.login || item}`;
                followForm.method = 'post';
                followForm.className = 'follow-form';

                const followButton = document.createElement('button');
                followButton.type = 'submit';
                followButton.className = 'btn-follow';
                followButton.textContent = 'Follow';

                followForm.appendChild(followButton);
                buttonGroup.appendChild(followForm);
            }

            if (buttonGroup.childElementCount > 0) {
                li.appendChild(buttonGroup);
            }

            listElement.appendChild(li);
        });

        addFormEventListeners();
    }

    function addFormEventListeners() {
        document.querySelectorAll('.unfollow-form').forEach(form => {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                const username = this.action.split('/').pop();
                fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.parentElement.parentElement.style.display = 'none';
                        } else {
                            alert('Failed to unfollow ' + username);
                        }
                    });
            });
        });

        document.querySelectorAll('.follow-form').forEach(form => {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                const username = this.action.split('/').pop();
                fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.parentElement.parentElement.style.display = 'none';
                        } else {
                            alert('Failed to follow ' + username);
                        }
                    });
            });
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
});
