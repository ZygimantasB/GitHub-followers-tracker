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

    // Fetch data function using async/await
    async function fetchData(dataType) {
        try {
            const response = await fetch(`/get_data?type=${dataType}`);
            const data = await response.json();
            populateData(dataType, data);
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    // Handle bulk follow/unfollow buttons
    document.getElementById('follow-all-suggested-users-button').addEventListener('click', function() {
        bulkAction('suggested-users-list', '/bulk_follow');
    });

    document.getElementById('unfollow-all-not-following-back-button').addEventListener('click', function() {
        bulkAction('not-following-back-list', '/bulk_unfollow');
    });

    document.getElementById('unfollow-all-unfollowers-button').addEventListener('click', function() {
        bulkAction('unfollowers-list', '/bulk_unfollow');
    });

    async function bulkAction(listId, endpoint) {
        const list = document.getElementById(listId);
        const usernames = Array.from(list.querySelectorAll('.list-item span')).map(span => span.textContent);
        if (usernames.length > 0) {
            try {
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
            }
        }
    }

    function populateData(dataType, data) {
        const counts = {
            'followers': 'followers-count',
            'following': 'following-count',
            'new_followers': 'new-followers-count',
            'unfollowers': 'unfollowers-count',
            'not_following_back': 'not-following-back-count',
            'suggested_users': 'suggested-users-count'
        };

        const lists = {
            'followers': 'followers-list',
            'following': 'following-list',
            'new_followers': 'new-followers-list',
            'unfollowers': 'unfollowers-list',
            'not_following_back': 'not-following-back-list',
            'suggested_users': 'suggested-users-list'
        };

        const dataKeys = {
            'followers': 'followers',
            'following': 'following',
            'new_followers': 'new_followers',
            'unfollowers': 'unfollowers',
            'not_following_back': 'not_following_back',
            'suggested_users': 'suggested_users'
        };

        const countElement = document.getElementById(counts[dataType]);
        const listElement = document.getElementById(lists[dataType]);
        const dataList = data[dataKeys[dataType]];

        // Update counts
        countElement.textContent = dataList.length;
        // Clear existing list
        listElement.innerHTML = '';

        dataList.forEach(item => {
            const li = document.createElement('li');
            const span = document.createElement('span');
            span.textContent = item.login || item;
            li.appendChild(span);
            li.className = 'list-item';
            li.dataset.username = item.login || item;

            const buttonGroup = document.createElement('div');
            buttonGroup.className = 'button-group';

            if (['following', 'not_following_back', 'unfollowers'].includes(dataType)) {
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

            if (['new_followers', 'suggested_users'].includes(dataType)) {
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
});
