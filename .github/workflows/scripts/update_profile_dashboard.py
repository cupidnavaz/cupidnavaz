#!/usr/bin/env python3
"""Refresh the profile README dashboard from GitHub's public profile API."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.request

USERNAME = "cupidnavaz"
README = Path("README.md")
START = "<!-- PROFILE-DASHBOARD:START -->"
END = "<!-- PROFILE-DASHBOARD:END -->"
API_ROOT = "https://api.github.com"

def api_get(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cupidnavaz-profile-dashboard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

def safe_text(value, limit=120):
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text

def activity_item(event):
    event_type = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    repo_url = f"https://github.com/{repo}"
    payload = event.get("payload", {})
    repo_link = f"[{repo}]({repo_url})" if repo else "a repository"

    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        count = payload.get("size", len(commits))
        branch = str(payload.get("ref", "")).removeprefix("refs/heads/")
        head = payload.get("head", "")
        destination = f"{repo_url}/commit/{head}" if head else repo_url
        details = f"pushed {count} commit{'s' if count != 1 else ''}"
        if branch:
            details += f" to `{safe_text(branch, 60)}`"
        if commits:
            message = safe_text(commits[0].get("message", ""), 90)
            if message:
                details += f" — {message}"
        return f"🔨 **Pushed code** to [{repo}]({destination}) — {details}."

    if event_type == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        title = safe_text(pr.get("title", "Pull request"))
        url = pr.get("html_url", repo_url)
        action = safe_text(payload.get("action", "updated"), 30)
        return f"🔀 **Pull request {action}:** [{title}]({url}) in {repo_link}."

    if event_type == "IssuesEvent":
        issue = payload.get("issue", {})
        title = safe_text(issue.get("title", "Issue"))
        url = issue.get("html_url", repo_url)
        action = safe_text(payload.get("action", "updated"), 30)
        return f"🧩 **Issue {action}:** [{title}]({url}) in {repo_link}."

    if event_type == "IssueCommentEvent":
        issue = payload.get("issue", {})
        title = safe_text(issue.get("title", "an issue"))
        url = issue.get("html_url", repo_url)
        return f"💬 **Commented** on [{title}]({url}) in {repo_link}."

    if event_type == "CreateEvent":
        ref_type = safe_text(payload.get("ref_type", "item"), 30)
        ref = payload.get("ref")
        details = f" `{safe_text(ref, 60)}`" if ref else ""
        return f"🌱 **Created {ref_type}{details}** in {repo_link}."

    if event_type == "ReleaseEvent":
        release = payload.get("release", {})
        title = safe_text(release.get("name") or release.get("tag_name") or "a release")
        url = release.get("html_url", repo_url)
        return f"🚀 **Published a release:** [{title}]({url}) in {repo_link}."

    if event_type == "WatchEvent":
        return f"⭐ **Starred** {repo_link}."

    if event_type == "ForkEvent":
        return f"🍴 **Forked** {repo_link}."

    if event_type == "PublicEvent":
        return f"🌍 **Made** {repo_link} **public**."

    return None

def build_dashboard():
    profile = api_get(f"/users/{USERNAME}")
    events = api_get(f"/users/{USERNAME}/events/public?per_page=100")

    lines = [
        "### ⚡ Latest public activity",
        "",
        "| Public repositories | Followers | Following | Public gists |",
        "|:---:|:---:|:---:|:---:|",
        f"| {profile.get('public_repos', 0)} | {profile.get('followers', 0)} | {profile.get('following', 0)} | {profile.get('public_gists', 0)} |",
        "",
    ]

    items = []
    for event in events:
        rendered = activity_item(event)
        if rendered:
            items.append(rendered)
        if len(items) == 8:
            break

    if items:
        lines.extend(f"- {item}" for item in items)
    else:
        lines.append("_No recent public events were returned by GitHub. New public profile activity will appear here after the next refresh._")

    refreshed = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.extend(["", f"<sub>Fetched from the GitHub public API · Last refreshed: {refreshed}</sub>"])
    return "\n".join(lines)

def main():
    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        raise SystemExit("Dashboard markers are missing from README.md")
    before, remainder = content.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = f"{before}{START}\n{build_dashboard()}\n{END}{after}"
    README.write_text(updated, encoding="utf-8")

if __name__ == "__main__":
    main()
