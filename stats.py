import os
import re
import requests
import time
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
    all_repos = []
    
    while True:
        r = requests.get(f"{repos_url}&page={page}", headers=HEADERS)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_repos.extend(batch)
        stars += sum(repo["stargazers_count"] for repo in batch)
        page += 1

    # --- Calculate Lines of Code (LOC) ---
    total_additions = 0
    total_deletions = 0

    for repo in all_repos:
        if repo["fork"]:
            continue  # Skip forks to count only your own code
            
        repo_name = repo["name"]
        stats_url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/stats/contributors"
        stats_res = requests.get(stats_url, headers=HEADERS)
        
        # GitHub's stats endpoint is asynchronous and returns 202 while building cache
        if stats_res.status_code == 202:
            time.sleep(1)
            stats_res = requests.get(stats_url, headers=HEADERS)
            
        if stats_res.status_code == 200 and isinstance(stats_res.json(), list):
            for contributor in stats_res.json():
                if contributor.get("author", {}).get("login") == USERNAME:
                    for week in contributor.get("weeks", []):
                        total_additions += week.get("a", 0)
                        total_deletions += week.get("d", 0)

    # Calculate net lines of code added
    loc = total_additions - total_deletions

    # --- GraphQL Query for Commits & Contributed Repos ---
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

    return stars, commits, contributed, loc, total_additions, total_deletions

TEMPLATES = [
    ("profileLightMode.template.svg", "profileLightMode.svg"),
    ("profileDarkMode.template.svg", "profileDarkMode.svg")
]

def update_readme_cache_buster():
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Appends/updates epoch timestamp on SVG URLs to bust GitHub Camo CDN cache
    timestamp = int(time.time())
    content = re.sub(r'profileLightMode\.svg(\?v=\d+)?', f'profileLightMode.svg?v={timestamp}', content)
    content = re.sub(r'profileDarkMode\.svg(\?v=\d+)?', f'profileDarkMode.svg?v={timestamp}', content)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def render(values):
    for src_path, dest_path in TEMPLATES:
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()

        for key, val in values.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            content = re.sub(pattern, str(val), content)

        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)

TOTAL_LINE_WIDTH = 56

def generate_dots(label: str, value: str, total_width: int = TOTAL_LINE_WIDTH) -> str:
    val_str = str(value)
    needed_dots = total_width - len(label) - len(val_str)
    return "." * max(needed_dots, 1)

if __name__ == "__main__":
    repos_count, followers = get_user_stats()
    stars, commits, contributed, loc, additions, deletions = get_stars_and_commits()

    profile_data = {
        # Static Fields
        "USER": "Rohan Mukherjee",
        "OS": "Linux, Windows, WSL",
        "DOMAIN": "Quantitative Finance, Astrophysics, Cosmology",
        "HOST": "TBU",
        "LANG_PROG": "Python, C++, C, Java, R, SQL",
        "LANG_MARKUP": "HTML, LaTeX, Markdown, YAML, JSON",
        "LANG_SPOKEN": "English, Hindi, Bengali, Assamese",
        "PROJ_DOMAIN": "Astrophysics, Quant-Finance, ML, DS",
        "PROJ_NUM": "13",
        "PROJ_TOOLS": "TBU",
        "EXP_RESEARCH": "3 years, 10 months",
        "EXP_HOSTS": "NASA, Caltech, Perimeter, TIFR, IIA",
        "EXP_WORK": "5 years, 7 months",
        "WORK_HOSTS": "Galileo Multiverse, CENTA, NoBroker",
        "EMAIL_PERSONAL": "rohanmukherjeemails@gmail.com",
        "EMAIL_WORK": "TBU",
        "LINKEDIN": "@rohanmukherjeee",
        "MEDIUM": "@astrodud",
        "TWITTER": "@theastrodud",

        # Dynamic Fields
        "UPTIME": get_uptime(),
        "REPOS": repos_count,
        "CONTRIBUTED": contributed,
        "COMMITS": f"{commits:,}",
        "STARS": f"{stars:,}",
        "FOLLOWERS": f"{followers:,}",
        "LOC": f"{loc:,}",
        "ADDITIONS": f"+{additions:,}",
        "DELETIONS": f"-{deletions:,}",
    }

    # Map labels to keys for dot calculation: (Template Tag, Label Text, Value Key)
    label_mappings = [
        ("USER", "User:", "USER"),
        ("UPTIME", "Uptime:", "UPTIME"),
        ("OS", "OS:", "OS"),
        ("DOMAIN", "Domain:", "DOMAIN"),
        ("HOST", "Host:", "HOST"),
        ("LANG_PROG", "Languages.Programming:", "LANG_PROG"),
        ("LANG_MARKUP", "Languages.Markup:", "LANG_MARKUP"),
        ("LANG_SPOKEN", "Languages.Spoken:", "LANG_SPOKEN"),
        ("PROJ_DOMAIN", "Projects.Domain:", "PROJ_DOMAIN"),
        ("PROJ_NUM", "Projects.Number:", "PROJ_NUM"),
        ("PROJ_TOOLS", "Projects.Tools:", "PROJ_TOOLS"),
        ("EXP_RESEARCH", "Experience.Research:", "EXP_RESEARCH"),
        ("EXP_HOSTS", "Experience.Hosts:", "EXP_HOSTS"),
        ("EXP_WORK", "Experience.Work:", "EXP_WORK"),
        ("WORK_HOSTS", "Work.Hosts:", "WORK_HOSTS"),
        ("EMAIL_PERSONAL", "Email.Personal:", "EMAIL_PERSONAL"),
        ("EMAIL_WORK", "Email.Work:", "EMAIL_WORK"),
        ("LINKEDIN", "LinkedIn:", "LINKEDIN"),
        ("MEDIUM", "Medium:", "MEDIUM"),
        ("TWITTER", "Twitter:", "TWITTER"),
    ]

    values = {}

    for tag, label, val_key in label_mappings:
        val_str = str(profile_data[val_key])
        values[tag] = val_str
        values[f"{tag}_DOTS"] = generate_dots(label, val_str)

    values["REPOS"] = str(profile_data["REPOS"])
    values["CONTRIBUTED"] = str(profile_data["CONTRIBUTED"])
    values["COMMITS"] = str(profile_data["COMMITS"])
    values["STARS"] = str(profile_data["STARS"])
    values["FOLLOWERS"] = str(profile_data["FOLLOWERS"])
    values["LOC"] = str(profile_data["LOC"])
    values["ADDITIONS"] = str(profile_data["ADDITIONS"])
    values["DELETIONS"] = str(profile_data["DELETIONS"])

    # Calculate Dots for GitHub Stats Sub-Columns
    values["COMMITS_DOTS"] = generate_dots("Commits:", profile_data["COMMITS"], total_width=29)
    values["STARS_DOTS"] = generate_dots("Stars:", profile_data["STARS"], total_width=22)
    values["REPOS_DOTS"] = generate_dots("Repos:", profile_data["REPOS"], total_width=12)
    values["FOLLOWERS_DOTS"] = generate_dots("Followers:", profile_data["FOLLOWERS"], total_width=22)
    values["LOC_DOTS"] = generate_dots("Lines.Of.Code:", profile_data["LOC"], total_width=30)

    render(values)
    update_readme_cache_buster()