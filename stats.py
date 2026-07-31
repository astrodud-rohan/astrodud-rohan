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
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        if prev_month in [1, 3, 5, 7, 8, 10, 12]:
            days_in_prev = 31
        elif prev_month in [4, 6, 9, 11]:
            days_in_prev = 30
        else:
            days_in_prev = 29 if (prev_year % 4 == 0 and (prev_year % 100 != 0 or prev_year % 400 == 0)) else 28
        
        days += days_in_prev

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

TEMPLATES = [
    ("profileLightMode.template.svg", "profileLightMode.svg"),
    ("profileDarkMode.template.svg", "profileDarkMode.svg")
]

def render(values):
    for src_path, dest_path in TEMPLATES:
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()

        for key, val in values.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            content = re.sub(pattern, str(val), content)

        with open(dest_path, "w", encoding="utf-8") as f:
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