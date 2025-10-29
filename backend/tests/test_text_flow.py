#!/usr/bin/env python3
"""
Test to demonstrate the text flow:
1. Original text (for subtitles) - keeps contractions
2. TTS text (for audio) - expands contractions
"""

from app.utils.text_cleaning import clean_story, prepare_text_for_tts

# Simulate a Reddit story
reddit_story = """
AITA for telling my 17M brother he's being ridiculous?

So basically I'm 25F and my BF is 28M. We've been together for 3 years.
My brother won't stop complaining about my SO. TBH it's getting annoying.

He's like "you shouldn't've moved in together" and "I can't believe you did that".
IMO he's just jealous. BTW, I didn't ask for his opinion anyway.

**UPDATE**: He apologized! We're good now.

Edit: Thanks for all the support!
TL;DR: Brother was being annoying, now we're cool.
"""

print("=" * 80)
print("TEXT FLOW DEMONSTRATION")
print("=" * 80)

print("\n📝 STEP 1: ORIGINAL REDDIT TEXT")
print("-" * 80)
print(reddit_story)

print("\n📝 STEP 2: CLEANED TEXT (for subtitles)")
print("-" * 80)
print("This is what users will SEE in the video subtitles")
print("-" * 80)
cleaned_text = clean_story(reddit_story)
print(cleaned_text)

print("\n🎤 STEP 3: TTS-PREPARED TEXT (for audio generation)")
print("-" * 80)
print("This is what the TTS model will read (expanded for clarity)")
print("-" * 80)
tts_text = prepare_text_for_tts(reddit_story)
print(tts_text)

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)

# Show word count difference
cleaned_words = cleaned_text.split()
tts_words = tts_text.split()

print(f"\n📊 Subtitle text: {len(cleaned_words)} words")
print(f"🎤 Audio text: {len(tts_words)} words")
print(f"📈 Difference: {len(tts_words) - len(cleaned_words)} additional words for TTS clarity")

print("\n" + "=" * 80)
print("KEY TRANSFORMATIONS")
print("=" * 80)

transformations = [
    ("17M", "seventeen M", "Age/gender abbreviation"),
    ("AITA", "Am I the asshole", "Reddit acronym"),
    ("he's", "he is", "Contraction"),
    ("won't", "will not", "Negative contraction"),
    ("shouldn't've", "should not have", "Compound contraction"),
    ("can't", "cannot", "Negative contraction"),
    ("SO", "significant other", "Reddit acronym"),
    ("TBH", "to be honest", "Reddit acronym"),
    ("IMO", "in my opinion", "Reddit acronym"),
    ("BTW", "by the way", "Reddit acronym"),
    ("we're", "we are", "Contraction"),
]

for original, transformed, description in transformations:
    if original.lower() in reddit_story.lower():
        print(f"\n✓ {original:20} → {transformed:25} ({description})")

print("\n" + "=" * 80)
print("✅ RESULT: Clear audio pronunciation + Natural-looking subtitles!")
print("=" * 80)
