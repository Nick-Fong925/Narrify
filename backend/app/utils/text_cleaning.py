import re
import json
import os


_SYSTEM_PROMPT = """\
Convert raw Reddit post text into TTS-ready output.
Return ONLY a JSON object with two keys — no markdown, no explanation.

"cleaned_text": the story rewritten for spoken narration (single string).
- Fix spelling and grammar
- Expand Reddit abbreviations: AITA→"Am I the asshole", TIFU→"Today I messed up", \
SO→"significant other", BF→"boyfriend", GF→"girlfriend", DH→"dear husband", \
DW→"dear wife", IMO→"in my opinion", IMHO→"in my humble opinion", \
TBH→"to be honest", IRL→"in real life", BTW→"by the way"
- Remove: markdown, URLs, "Edit:" blocks, "TL;DR:" blocks, emojis, special Unicode symbols
- Convert age/gender markers: 17M→"seventeen year old male", 34F→"thirty-four year old female"
- Keep contractions as-is: don't, can't, I'm, won't, it's, etc.
- Single space between words; no leading or trailing whitespace
- Preserve the original story tone and meaning

"chunks": array of strings — the story split into TTS speaking units.
- 1-2 sentences per chunk, ~60-150 characters each
- Split only at sentence or clause boundaries, never mid-thought
- chunks joined with a single space must exactly equal cleaned_text

Additionally, insert Orpheus TTS emotion tags at appropriate narrative moments.
Available tags: <gasp>, <sigh>, <sob>, <laugh>, <chuckle>, <groan>, <yawn>, <cough>, <sniffle>

Rules:
- Place tags INSIDE the chunk string, adjacent to the emotional moment
- Use sparingly — only at genuine narrative peaks (reveals, deaths, twists, grief)
- One tag per chunk maximum
- Tags can appear at the start or end of a sentence: "<gasp> The room was empty." or "He was gone. <sob>"
- Do not use <laugh> or <chuckle> in horror/dark contexts unless ironic
- Emotion tags are NOT part of the cleaned_text — only include them in the chunks array"""


def prepare_story_with_llm(text: str) -> tuple:
    """
    Use Claude Haiku to clean story text and split into TTS chunks.
    Returns (cleaned_text: str, chunks: list[str]).
    Raises RuntimeError if the API key is missing or the call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            from app.config import settings
            api_key = settings.anthropic_api_key
        except (ImportError, AttributeError):
            pass

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Cannot prepare story without LLM.")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if the model wraps the JSON despite instructions
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw)
    cleaned_text = data["cleaned_text"]
    chunks = data["chunks"]

    print(f"LLM cleaning complete: {len(chunks)} TTS chunks generated.")
    return cleaned_text, chunks


def clean_story(text: str) -> str:
    """
    Strip markdown, links, and Reddit boilerplate from raw post text.
    Used for display, word-count filtering, and storage — not for TTS.
    """
    text = re.sub(r'Original post here: ?\\?\\?\[.*?\]\(.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Edit:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'TL;DR:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\*\*|__|\*|_', '', text)
    text = text.replace('"', "'")
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())
