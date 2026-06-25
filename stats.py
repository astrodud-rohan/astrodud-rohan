import os
import re
import requests
from datetime import datetime

USERNAME = "astrodud-rohan"
TOKEN = os.environ["ACCESS_TOKEN"]
HEADERS = {"Authorization": f"token {TOKEN}"}
BIRTHDATE = datetime(1998, 4, 21)  # <--  actual DOB 

SVG_FILES = ["profileLightMode.svg", "profileDarkMode.svg"]  # <-- svg filenames


def get_uptime():
    now = datetime.now()
    years = now.year - BIRTHDATE.year
    months = now.month - BIRTHDATE.month
    days = now.day - BIRTHDATE.day
    if days < 0:
        months -= 1
        prev_month = now.month - 1 or 12
        prev_year = now.year if now.month > 1 else now.year - 1
        days_in_prev_month = (datetime(now.year, now.month, 1) - datetime(prev_year, prev_month, 1)).days
        days += days_in_prev_month
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def get_user_stats():
    r = requests.get(f"https://api.github.com/users/{USERNAME}", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data["public_repos"], data["followers"]


def get_stars_and_commits():
    repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
    stars = 0
    page = 1
    while True:
        r = requests.get(f"{repos_url}&page={page}", headers=HEADERS)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        stars += sum(repo["stargazers_count"] for repo in batch)
        page += 1

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
        }
        repositoriesContributedTo(first: 1) {
          totalCount
        }
      }
    }
    """
    gql = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": USERNAME}},
        headers=HEADERS,
    )
    gql.raise_for_status()
    gdata = gql.json()["data"]["user"]
    commits = gdata["contributionsCollection"]["totalCommitContributions"] + \
              gdata["contributionsCollection"]["restrictedContributionsCount"]
    contributed = gdata["repositoriesContributedTo"]["totalCount"]

    return stars, commits, contributed


def render(values):
    for path in SVG_FILES:
        with open(path, "r") as f:
            content = f.read()
        for key, val in values.items():
            content = re.sub(r"\{\{" + key + r"\}\}", str(val), content)
        with open(path, "w") as f:
            f.write(content)


if __name__ == "__main__":
    repos_count, followers = get_user_stats()
    stars, commits, contributed = get_stars_and_commits()

    values = {
        "UPTIME": get_uptime(),
        "REPOS": repos_count,
        "CONTRIBUTED": contributed,
        "COMMITS": f"{commits:,}",
        "STARS": f"{stars:,}",
        "FOLLOWERS": f"{followers:,}",
    }
    render(values)