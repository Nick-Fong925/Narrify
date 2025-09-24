import requests
from app.utils.text_cleaning import clean_story, word_count

class RedditScraper:
    def __init__(self, subreddit: str):
        self.subreddit = subreddit

    def fetch_top_posts(self, time_filter='week', limit=20):
        url = f"https://www.reddit.com/r/{self.subreddit}/top.json?limit={limit}&t={time_filter}"
        headers = {"User-Agent": "AITA-Scraper/0.1"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        posts = []
        for post in data["data"]["children"]:
            d = post["data"]
            posts.append({
                "reddit_id": d["id"],
                "subreddit": self.subreddit,
                "title": d["title"],
                "story": clean_story(d["selftext"]),
                "score": d["score"],
                "num_comments": d["num_comments"],
                "url": d["url"]
            })
        return posts
