import re

def clean_story(text: str) -> str:
    # Remove 'Original post here: [link]' lines
    text = re.sub(r'Original post here: ?\\?\\?\[.*?\]\(.*?\)', '', text, flags=re.IGNORECASE)
    # Remove 'Edit:' and everything after (common for updates)
    text = re.sub(r'Edit:.*', '', text, flags=re.IGNORECASE)
    # Remove 'TL;DR:' and everything after (common for summaries)
    text = re.sub(r'TL;DR:.*', '', text, flags=re.IGNORECASE)
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove excessive newlines and whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\*\*|__|\*|_', '', text)
    text = text.replace('"', "'")
    text = text.strip()
    return text

def word_count(text: str) -> int:
    return len(text.split())
