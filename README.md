# GitHub Follower Tracker

This project is a simple Flask web application that tracks your GitHub followers, following, unfollowers, and new followers. It allows you to monitor changes in your GitHub social connections, filter out certain users, and see which users are not following you back.

## Features

- **Followers**: View a list of all users currently following you.
- **Following**: View a list of all users you are currently following.
- **Unfollowers**: See users who have unfollowed you since the last time you checked.
- **Not Following Back**: View users you follow but who do not follow you back.
- **New Followers**: Track users who have followed you within the last 3 days.
- **Ignore List**: Specify users who should be excluded from the "Not Following Back" list.

## Requirements

- **Python 3.6+**
- **Flask**: A lightweight WSGI web application framework.
- **Requests**: A simple HTTP library for Python.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/github-follower-tracker.git
cd github-follower-tracker
