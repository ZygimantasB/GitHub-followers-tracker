# GitHub Follower Tracker

This project is a Flask web application that helps you manage and track your GitHub social connections. It provides a comprehensive dashboard to monitor your followers, following, unfollowers, and new followers, with additional features for user management and automated actions.

## Features

- **Followers Dashboard**: View a list of all users currently following you with their follower/following counts.
- **Following Management**: See all users you're following and easily unfollow them if needed.
- **Unfollowers Tracking**: Identify users who have unfollowed you since the last time you checked.
- **Not Following Back**: View users you follow who don't follow you back, with an option to exclude specific users via an ignore list.
- **New Followers**: Track users who have followed you within the last 3 days.
- **Suggested Users**: Discover new users to follow based on activity and follower counts.
- **Following > Followers**: Find users who follow more people than they have followers (potential follow-back users).
- **User Search**: Check if a specific user follows you.
- **Bulk Actions**: Follow or unfollow multiple users at once.
- **Automated Tasks**: Daily task to automatically follow suggested users and monthly task to unfollow users who don't follow you back.
- **Dark/Light Theme**: Toggle between dark and light themes for comfortable viewing.
- **Responsive Design**: Works well on both desktop and mobile devices.
## Requirements

- **Python 3.6+**
- **Flask**: A lightweight WSGI web application framework
- **Requests**: HTTP library for making API calls to GitHub
- **APScheduler**: For scheduling automated tasks
- **python-decouple**: For reading environment variables from .env file
- **GitHub API Token**: A GitHub personal access token to authenticate API requests

The full list of dependencies can be found in the `requirements.txt` file.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/GitHub-followers-tracker.git
cd GitHub-followers-tracker
```

### 2. Set Up a Virtual Environment (Optional but Recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

### 3. Install the Required Dependencies

Install the required dependencies using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 4. Configuration

#### Creating the `.env` File

Create a `.env` file in the project root with your GitHub username and API token:

```env
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token
```

You can obtain a GitHub personal access token by following these steps:
1. Go to your GitHub account settings
2. Select "Developer settings" from the sidebar
3. Click on "Personal access tokens" and then "Tokens (classic)"
4. Click "Generate new token" and select the appropriate scopes (at minimum, you need `user:follow`)
5. Copy the generated token and paste it into your `.env` file

#### Setting Up Data Files

The application uses several files to track followers and manage user data. Create these empty files in the project root:

- `ignore_list.txt`: Add GitHub usernames (one per line) that you want to exclude from the "Not Following Back" list
- `new_followers.json`: This will be automatically populated with new followers and their timestamps
- `previous_followers.txt`: This will be automatically populated with your current followers list

These files are essential for tracking followers, filtering users, and recording changes.

#### Understanding the Data Files

- **ignore_list.txt**: This file lets you specify users who should be excluded from the "Not Following Back" section. This is useful for accounts you want to follow regardless of whether they follow you back (e.g., official accounts, friends, etc.).
- **new_followers.json**: This file stores information about new followers, including when they started following you. The application uses this to display users who followed you within the last 3 days.
- **previous_followers.txt**: This file keeps a record of your followers from the last time you ran the application. It's used to determine who has unfollowed you since then.

### 5. Project Structure

The project directory is organized as follows:

```
GitHub-followers-tracker/
│
├── app.py                          # Main Flask application
├── github_api.py                   # GitHub API interaction functions
├── data_manager.py                 # Data persistence functions
├── utils.py                        # Utility functions
├── daily_tasks.py                  # Automated daily tasks
├── monthly_tasks.py                # Automated monthly tasks
├── previous_followers.txt          # Stores the list of previous followers
├── new_followers.json              # Stores new followers with timestamps
├── ignore_list.txt                 # Stores usernames to ignore
├── user_following_cache.json       # Cache for API responses
├── requirements.txt                # Lists all the Python dependencies
├── .env                            # Environment variables
├── static/
│   ├── styles.css                  # CSS styles for the application
│   └── script.js                   # JavaScript for frontend functionality
├── templates/
│   └── index.html                  # HTML template for the main page
└── .venv/                          # Virtual environment directory (optional)
```

### 6. Key Components

#### Core Files

- **app.py**: The main Flask application that handles HTTP requests, renders templates, and manages the application flow. It also sets up scheduled tasks using APScheduler.
- **github_api.py**: Contains functions for interacting with the GitHub API, including fetching followers/following lists, following/unfollowing users, and handling rate limits.
- **data_manager.py**: Manages data persistence, including loading and saving followers, new followers, and the ignore list.
- **utils.py**: Contains utility functions used throughout the application, such as caching and list chunking.

#### Scheduled Tasks

- **daily_tasks.py**: Contains the automated daily task that runs at 6 AM to follow random suggested users.
- **monthly_tasks.py**: Contains the automated monthly task that runs at 1 AM on the first day of each month to unfollow users who don't follow back.

#### Data Files

- **previous_followers.txt**: Stores the list of your followers from the last check to identify unfollowers.
- **new_followers.json**: Tracks new followers with timestamps to show recent followers (within 3 days).
- **ignore_list.txt**: Contains usernames to exclude from the "Not Following Back" list.
- **user_following_cache.json**: Caches API responses to reduce the number of API calls and improve performance.

#### Frontend Files

- **templates/index.html**: The main HTML template that defines the structure of the web interface.
- **static/styles.css**: Contains all the CSS styles for the application, including dark/light theme support.
- **static/script.js**: Contains the JavaScript code for frontend functionality, including API calls, UI updates, and user interactions.

### 7. Running the Application

Start the Flask development server by running:

```bash
python app.py
```

This will start the server on port 9999. Open your web browser and go to `http://localhost:9999/` to view the application.

### 8. Using the Application

#### Dashboard Overview

The application provides a dashboard with summary statistics and several tabs for different features:

- **Followers**: View all users currently following you, with their follower and following counts.
- **Following**: View all users you're currently following, with options to unfollow.
- **New Followers**: See users who have started following you in the last 3 days.
- **Unfollowers**: See users who have unfollowed you since the last check.
- **Not Following Back**: View users you follow who don't follow you back (excluding those in your ignore list).
- **Suggested Users**: Discover new users to follow based on activity and follower counts.
- **Following > Followers**: Find users who follow more people than they have followers.

#### User Actions

For each user displayed in the lists, you can perform various actions:

- **Follow/Unfollow**: Follow or unfollow individual users with a single click.
- **Bulk Actions**: Select multiple users to follow or unfollow at once.
- **Search**: Use the search box to check if a specific user follows you.

#### Theme Toggle

Toggle between dark and light themes using the moon/sun icon in the top-right corner of the application.

### 9. Automated Tasks

The application includes two automated tasks:

1. **Daily Task (6 AM)**: Automatically follows random suggested users to help grow your network.
2. **Monthly Task (1 AM on the 1st of each month)**: Automatically unfollows users who don't follow you back.

These tasks run in the background as long as the application is running. You can modify the scheduling in `app.py` if needed.

### 10. Customization

- **Ignore List**: Add usernames to `ignore_list.txt` (one per line) to exclude them from the "Not Following Back" list and automated unfollowing.
- **New Follower Retention**: The application is configured to show new followers for 3 days. You can modify the `timedelta(days=3)` in `app.py` to change this duration.
- **Rate Limiting**: The application includes sophisticated rate limiting to avoid hitting GitHub API limits. You can adjust the thresholds in `github_api.py` if needed.

### 11. Troubleshooting

- **API Rate Limits**: If you encounter rate limit errors, the application will automatically slow down requests. You may need to wait for the rate limit to reset.
- **Empty Data Files**: If you encounter JSON decode errors, it might be due to empty or malformed data files. The application should handle these cases automatically by reinitializing the files.
- **Authentication Issues**: Ensure your GitHub token has the correct permissions (at minimum, `user:follow` scope).

### 12. Contributing

If you'd like to contribute to this project, please fork the repository and create a pull request with your changes. Bug reports, feature requests, and feedback are always welcome.


### 13. Scheduling and Automation

You have two ways to run the automated follow/unfollow tasks. No external cron is required if you keep one of these processes running.

Option A — Run the Flask app (built‑in scheduler)
- Command: python app.py
- Schedules (local time):
  - Daily follow at 6:00 AM
  - Monthly unfollow at 1:00 AM on the 1st of each month
- Runs automatically as long as the Flask app process stays running.

Option B — Run the standalone scheduler (no web server)
- Command: python scheduler.py
- Schedules (local time):
  - Daily follow at 2:00 PM
  - Monthly unfollow at 2:05 PM on the last day of the month
- Use this if you want the 2 PM daily behavior and end‑of‑month unfollow without running the web UI.

Do I need Linux cron?
- Not required if you keep app.py or scheduler.py running in a terminal/service. The scheduler inside the process will trigger tasks at the configured times.
- Optional: Use cron or systemd to auto‑start and keep it running after logout or reboot.

Examples (optional, for convenience):

Systemd service (Linux)
1) Create file at ~/.config/systemd/user/github-follower-scheduler.service with:

[Unit]
Description=GitHub Followers Tracker Scheduler
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/GitHub-followers-tracker
ExecStart=%h/GitHub-followers-tracker/.venv/bin/python scheduler.py
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target

2) Enable and start:
- systemctl --user daemon-reload
- systemctl --user enable --now github-follower-scheduler.service

Cron (Linux) to run at boot in background
- @reboot /usr/bin/bash -lc 'cd "$HOME/GitHub-followers-tracker" && . .venv/bin/activate && exec python scheduler.py >> app.log 2>&1'

Windows Task Scheduler
- Create a basic task to run python with Program/script: path\to\python.exe, Add arguments: scheduler.py, Start in: the project folder. Set Trigger: At log on or On a schedule.

Notes
- Timezone: Both app.py and scheduler.py use local time. The standalone scheduler uses tzlocal to honor your system timezone.
- Choose only one scheduler at a time to avoid duplicate actions (don’t run app.py and scheduler.py concurrently unless you deliberately want both schedules).


## Managing the Ignore List from the Web UI

You can now manage the ignore list directly from the application without editing files manually.

- Open the app in your browser (default: http://localhost:9999/).
- Scroll to the "Ignore List" card near the top of the page.
- To add a username: enter the GitHub username and click "Add to Ignore".
- To remove a username: click the "Remove" button next to it.
- Click "Refresh" to reload the current list from disk.

Technical notes:
- The ignore list is persisted in the file `ignore_list.txt` (one username per line) in the project root.
- Usernames are normalized (trimmed and lowercased) and duplicates are removed automatically.
- The ignore list affects multiple views (Followers, Following, New Followers, Unfollowers, Not Following Back, Suggested Users). Users in the ignore list are hidden from these sections.
