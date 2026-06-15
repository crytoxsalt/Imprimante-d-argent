import random
from curl_cffi import requests

SUBREDDITS = ["AmItheAsshole", "relationship_advice", "tifu", "confessions"]

_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"


def get_story(subreddit_name=None, min_chars=500, max_chars=3000):
    sub = subreddit_name or random.choice(SUBREDDITS)

    r = requests.get(
        _URL,
        params={"subreddit": sub, "limit": 50},
        impersonate="chrome",
        timeout=30,
    )
    r.raise_for_status()
    posts = r.json().get("data", [])

    candidates = [
        p for p in posts
        if p.get("is_self")
        and not p.get("stickied")
        and min_chars <= len((p.get("selftext") or "").strip()) <= max_chars
        and (p.get("selftext") or "").strip() not in ("[removed]", "[deleted]")
        and not p.get("title", "").startswith("[")
    ]

    if not candidates:
        raise ValueError(f"No suitable post found in r/{sub}")

    post = random.choice(candidates)
    return {
        "id":        post["id"],
        "title":     post["title"],
        "text":      f"{post['title']}. {post['selftext'].strip()}",
        "subreddit": sub,
        "url":       f"https://reddit.com{post['permalink']}",
    }
