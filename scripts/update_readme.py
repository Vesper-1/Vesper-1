#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, sys, time, datetime
import requests
import feedparser

README_PATH = "README.md"

USER = os.getenv("GITHUB_USERNAME", "").strip()
RSS_URL = os.getenv("BLOG_RSS", "").strip()
WAKATIME_API_KEY = os.getenv("WAKATIME_API_KEY", "").strip()

def replace_between_markers(content, marker, new_block):
    pattern = re.compile(
        rf"(<!--START_SECTION:{marker}-->)(.*?)(<!--END_SECTION:{marker}-->)",
        re.DOTALL,
    )
    return pattern.sub(rf"\1\n{new_block}\n\3", content)

def fetch_recent_commits(user, limit=5):
    # 获取用户最近 Push 的 Event，再解析出 commit
    url = f"https://api.github.com/users/{user}/events/public"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    events = r.json()

    commits = []
    for ev in events:
        if ev.get("type") == "PushEvent":
            repo = ev["repo"]["name"]
            for c in ev["payload"].get("commits", []):
                msg = c.get("message", "").split("\n")[0][:80]
                sha = c.get("sha", "")[:7]
                commit_url = f"https://github.com/{repo}/commit/{c.get('sha')}"
                commits.append(f"- `{sha}` {msg} · [{repo}]({commit_url})")
                if len(commits) >= limit:
                    return commits
    return commits

def fetch_blog_posts(rss_url, limit=5):
    if not rss_url:
        return []
    d = feedparser.parse(rss_url)
    items = []
    for e in d.entries[:limit]:
        title = e.get("title", "Untitled")
        link = e.get("link", "")
        # 处理时间
        if hasattr(e, "published_parsed") and e.published_parsed:
            dt = datetime.datetime.fromtimestamp(time.mktime(e.published_parsed))
            date_str = dt.strftime("%Y-%m-%d")
        else:
            date_str = ""
        items.append(f"- [{title}]({link}) {('· ' + date_str) if date_str else ''}")
    return items

def fetch_wakatime_summary(api_key):
    if not api_key:
        return "WakaTime 未配置。"
    # 最近 7 天汇总
    url = "https://wakatime.com/api/v1/users/current/summaries"
    params = {
        "range": "last_7_days"
    }
    headers = {"Authorization": f"Basic {api_key}"}
    # 注意：官方是 Basic base64(api_key)；有些人把 api_key 当 token 用也能过
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        # 计算总时长
        total_seconds = 0
        for day in data.get("data", []):
            total_seconds += day.get("grand_total", {}).get("total_seconds", 0)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours} hrs {minutes} mins (last 7 days)"
    except Exception as e:
        return f"WakaTime 获取失败：{e}"

def main():
    if not USER:
        print("GITHUB_USERNAME 未设置")
        sys.exit(1)

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # BLOG
    blog_lines = fetch_blog_posts(RSS_URL, limit=5)
    blog_md = "\n".join(blog_lines) if blog_lines else "_No posts found or RSS not set._"
    content = replace_between_markers(content, "BLOG", blog_md)

    # COMMITS
    commits = fetch_recent_commits(USER, limit=5)
    commits_md = "\n".join(commits) if commits else "_No recent commits found._"
    content = replace_between_markers(content, "COMMITS", commits_md)

    # WAKATIME
    waka_text = fetch_wakatime_summary(WAKATIME_API_KEY)
    content = replace_between_markers(content, "WAKATIME", waka_text)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("README updated.")

if __name__ == "__main__":
    main()

