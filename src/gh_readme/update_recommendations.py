import os
import re
from pathlib import Path
import niquests

USER = os.environ.get("GITHUB_USERNAME")
if not USER:
    raise SystemExit("GITHUB_USERNAME env required")

TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def fetch_repos():
    page = 1
    out = []
    while True:
        r = niquests.get(
            f"https://api.github.com/users/{USER}/repos",
            params={"per_page": 100, "sort": "updated", "page": page},
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        out += [x for x in batch if not x.get("fork")]
        if len(batch) < 100:
            break
        page += 1
    return out


def score(r):
    stars = r.get("stargazers_count", 0)
    forks = r.get("forks_count", 0)
    issues = r.get("open_issues_count", 0)
    return stars * 3 + forks * 2 + max(0, 20 - issues)


def badge(label, message, logo=None):
    from urllib.parse import quote

    base = f"https://img.shields.io/badge/{quote(label)}-{quote(str(message))}-0a0a0a?labelColor=0a0a0a"
    if logo:
        base += f"&logo={quote(logo)}"
    return base


def item(r):
    desc = (r.get("description") or "").replace("\n", " ").strip()[:140]
    stars = f'![stars]({badge("★", r.get("stargazers_count",0), "github")})'
    lg = f'![lang]({badge("lang", r.get("language","misc"))})'
    sz = f'![size]({badge("size", f"{round((r.get("size",0))/1024)} MB")})'
    return f'- [{r["name"]}]({r["html_url"]}) — {desc} {stars} {lg} {sz}'


def patch_readme(items):
    p = Path("README.md")
    md = p.read_text(encoding="utf-8")
    block = "\n".join(items)
    md = re.sub(
        r"(<!-- REPO_RECS_START -->)([\s\S]*?)(<!-- REPO_RECS_END -->)",
        r"\1\n" + block + r"\n\3",
        md,
    )
    p.write_text(md, encoding="utf-8")


def update_recommendations():
    repos = fetch_repos()
    repos.sort(key=score, reverse=True)
    top = [item(r) for r in repos[:8]]
    patch_readme(top)
