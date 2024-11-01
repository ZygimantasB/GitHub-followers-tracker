function toggleVisibility(id) {
    var element = document.getElementById(id);
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
            fetch(`/get_data?type=${dataType}`)
                .then(response => response.json())
                .then(data => {
                    populateData(dataType, data);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        });
    });

    // Handle Follow All button for Suggested Users
    document.getElementById('follow-all-suggested-users-button').addEventListener('click', function() {
        const suggestedUsersList = document.getElementById('suggested-users-list');
        const usernames = [];
        suggestedUsersList.querySelectorAll('.list-item').forEach(li => {
            const username = li.querySelector('span').textContent;
            usernames.push(username);
        });
        if (usernames.length > 0) {
            fetch('/bulk_follow', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ usernames: usernames })
            })
                .then(response => response.json())
                .then(data => {
                    // Handle results
                    console.log('Bulk follow results:', data);
                    usernames.forEach(username => {
                        if (data[username] && data[username].success) {
                            // Remove the user from the list or update UI
                            const li = suggestedUsersList.querySelector(`.list-item[data-username="${username}"]`);
                            if (li) {
                                li.style.display = 'none';
                            }
                        }
                    });
                })
                .catch(error => {
                    console.error('Error during bulk follow:', error);
                });
        }
    });

    // Handle Unfollow All button for Not Following Back
    document.getElementById('unfollow-all-not-following-back-button').addEventListener('click', function() {
        const list = document.getElementById('not-following-back-list');
        const usernames = [];
        list.querySelectorAll('.list-item').forEach(li => {
            const username = li.querySelector('span').textContent;
            usernames.push(username);
        });
        if (usernames.length > 0) {
            fetch('/bulk_unfollow', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ usernames: usernames })
            })
                .then(response => response.json())
                .then(data => {
                    // Handle results
                    console.log('Bulk unfollow results:', data);
                    usernames.forEach(username => {
                        if (data[username] && data[username].success) {
                            // Remove the user from the list or update UI
                            const li = list.querySelector(`.list-item[data-username="${username}"]`);
                            if (li) {
                                li.style.display = 'none';
                            }
                        }
                    });
                })
                .catch(error => {
                    console.error('Error during bulk unfollow:', error);
                });
        }
    });

    // Handle Unfollow All button for Unfollowers
    document.getElementById('unfollow-all-unfollowers-button').addEventListener('click', function() {
        const list = document.getElementById('unfollowers-list');
        const usernames = [];
        list.querySelectorAll('.list-item').forEach(li => {
            const username = li.querySelector('span').textContent;
            usernames.push(username);
        });
        if (usernames.length > 0) {
            fetch('/bulk_unfollow', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ usernames: usernames })
            })
                .then(response => response.json())
                .then(data => {
                    // Handle results
                    console.log('Bulk unfollow results:', data);
                    usernames.forEach(username => {
                        if (data[username] && data[username].success) {
                            // Remove the user from the list or update UI
                            const li = list.querySelector(`.list-item[data-username="${username}"]`);
                            if (li) {
                                li.style.display = 'none';
                            }
                        }
                    });
                })
                .catch(error => {
                    console.error('Error during bulk unfollow:', error);
                });
        }
    });

    function populateData(dataType, data) {
        if (dataType === 'followers') {
            // Update counts
            document.getElementById('followers-count').textContent = data.followers.length;
            // Populate followers
            const followersList = document.getElementById('followers-list');
            followersList.innerHTML = '';
            data.followers.forEach(follower => {
                const li = document.createElement('li');
                li.textContent = follower;
                li.className = 'list-item';
                li.dataset.username = follower;
                followersList.appendChild(li);
            });
        } else if (dataType === 'following') {
            // Update counts
            document.getElementById('following-count').textContent = data.following.length;
            // Populate following
            const followingList = document.getElementById('following-list');
            followingList.innerHTML = '';
            data.following.forEach(follow => {
                const li = document.createElement('li');
                const span = document.createElement('span');
                span.textContent = follow.login;
                li.appendChild(span);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'button-group';

                // Since we don't have followers data here, omit the check
                const unfollowForm = document.createElement('form');
                unfollowForm.action = '/unfollow/' + follow.login;
                unfollowForm.method = 'post';
                unfollowForm.className = 'unfollow-form';
                unfollowForm.style.display = 'inline';

                const unfollowButton = document.createElement('button');
                unfollowButton.type = 'submit';
                unfollowButton.className = 'btn-unfollow';
                unfollowButton.textContent = 'Unfollow';

                unfollowForm.appendChild(unfollowButton);
                buttonGroup.appendChild(unfollowForm);

                li.appendChild(buttonGroup);
                li.className = 'list-item';
                li.dataset.username = follow.login;
                followingList.appendChild(li);
            });
            addFormEventListeners();
        } else if (dataType === 'new_followers') {
            // Update counts
            document.getElementById('new-followers-count').textContent = data.new_followers.length;
            // Populate new followers
            const newFollowersList = document.getElementById('new-followers-list');
            newFollowersList.innerHTML = '';
            data.new_followers.forEach(newFollower => {
                const li = document.createElement('li');
                const span = document.createElement('span');
                span.textContent = newFollower;
                li.appendChild(span);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'button-group';

                // Since we don't have following data here, just add follow button
                const followForm = document.createElement('form');
                followForm.action = '/follow/' + newFollower;
                followForm.method = 'post';
                followForm.className = 'follow-form';
                followForm.style.display = 'inline';

                const followButton = document.createElement('button');
                followButton.type = 'submit';
                followButton.className = 'btn-follow';
                followButton.textContent = 'Follow';

                followForm.appendChild(followButton);
                buttonGroup.appendChild(followForm);

                li.appendChild(buttonGroup);
                li.className = 'list-item';
                li.dataset.username = newFollower;
                newFollowersList.appendChild(li);
            });
            addFormEventListeners();
        } else if (dataType === 'unfollowers') {
            // Update counts
            document.getElementById('unfollowers-count').textContent = data.unfollowers.length;
            // Populate unfollowers
            const unfollowersList = document.getElementById('unfollowers-list');
            unfollowersList.innerHTML = '';
            data.unfollowers.forEach(unfollower => {
                const li = document.createElement('li');
                const span = document.createElement('span');
                span.textContent = unfollower;
                li.appendChild(span);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'button-group';

                const unfollowForm = document.createElement('form');
                unfollowForm.action = '/unfollow/' + unfollower;
                unfollowForm.method = 'post';
                unfollowForm.className = 'unfollow-form';
                unfollowForm.style.display = 'inline';

                const unfollowButton = document.createElement('button');
                unfollowButton.type = 'submit';
                unfollowButton.className = 'btn-unfollow';
                unfollowButton.textContent = 'Unfollow';

                unfollowForm.appendChild(unfollowButton);
                buttonGroup.appendChild(unfollowForm);

                li.appendChild(buttonGroup);
                li.className = 'list-item';
                li.dataset.username = unfollower;
                unfollowersList.appendChild(li);
            });
            addFormEventListeners();
        } else if (dataType === 'not_following_back') {
            // Update counts
            document.getElementById('not-following-back-count').textContent = data.not_following_back.length;
            // Populate not following back
            const list = document.getElementById('not-following-back-list');
            list.innerHTML = '';
            data.not_following_back.forEach(user => {
                const li = document.createElement('li');
                const span = document.createElement('span');
                span.textContent = user;
                li.appendChild(span);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'button-group';

                const unfollowForm = document.createElement('form');
                unfollowForm.action = '/unfollow/' + user;
                unfollowForm.method = 'post';
                unfollowForm.className = 'unfollow-form';
                unfollowForm.style.display = 'inline';

                const unfollowButton = document.createElement('button');
                unfollowButton.type = 'submit';
                unfollowButton.className = 'btn-unfollow';
                unfollowButton.textContent = 'Unfollow';

                unfollowForm.appendChild(unfollowButton);
                buttonGroup.appendChild(unfollowForm);

                li.appendChild(buttonGroup);
                li.className = 'list-item';
                li.dataset.username = user;
                list.appendChild(li);
            });
            addFormEventListeners();
        } else if (dataType === 'suggested_users') {
            // Update counts
            document.getElementById('suggested-users-count').textContent = data.suggested_users.length;
            // Populate suggested users
            const suggestedUsersList = document.getElementById('suggested-users-list');
            suggestedUsersList.innerHTML = '';
            data.suggested_users.forEach(user => {
                const li = document.createElement('li');
                const span = document.createElement('span');
                span.textContent = user;
                li.appendChild(span);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'button-group';

                const followForm = document.createElement('form');
                followForm.action = '/follow/' + user;
                followForm.method = 'post';
                followForm.className = 'follow-form';
                followForm.style.display = 'inline';

                const followButton = document.createElement('button');
                followButton.type = 'submit';
                followButton.className = 'btn-follow';
                followButton.textContent = 'Follow';

                followForm.appendChild(followButton);
                buttonGroup.appendChild(followForm);

                li.appendChild(buttonGroup);
                li.className = 'list-item';
                li.dataset.username = user;
                suggestedUsersList.appendChild(li);
            });
            addFormEventListeners();
        }
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
