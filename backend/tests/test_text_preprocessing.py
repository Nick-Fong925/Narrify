#!/usr/bin/env python3
"""
Test script for text preprocessing - shows how Reddit text gets cleaned for TTS
"""

from app.utils.text_cleaning import clean_story, preprocess_for_tts

# Test cases with common Reddit patterns
test_cases = [
    "AITA for telling my 17M brother he's being ridiculous?",
    "I (25F) just found out my BF (28M) has been lying to me",
    "TIFU by accidentally sending a text to my boss. BTW, I'm 23M",
    "My SO won't stop complaining and TBH it's getting annoying",
    "17M here, can't believe this happened IRL",
    "I'm a 32F and my GF is 29F, we've been together 5 years",
    "AITA? I told my 45M coworker he shouldn't've done that",
    "IMO, y'all are overreacting. I'm 19F BTW",
]

print("=" * 80)
print("TEXT PREPROCESSING TEST")
print("=" * 80)

for i, text in enumerate(test_cases, 1):
    print(f"\n{i}. ORIGINAL:")
    print(f"   {text}")
    print(f"\n   CLEANED (for TTS):")
    cleaned = clean_story(text)
    print(f"   {cleaned}")
    print("-" * 80)

# Test just the TTS preprocessing step
print("\n" + "=" * 80)
print("TTS PREPROCESSING ONLY (before cleaning)")
print("=" * 80)

specific_tests = [
    "17M",
    "25F",
    "I'm 17M and he's 25F",
    "AITA for this?",
    "won't, can't, shouldn't've",
    "My SO (28M) and I (25F)",
    "He's not going, wasn't caught",
    "I'm sure she's done, they're fine",
    "It's not fair, wasn't it yours?",
    "You're right, we're leaving, they've gone",
]

for text in specific_tests:
    processed = preprocess_for_tts(text)
    print(f"\nOriginal:  {text}")
    print(f"Processed: {processed}")
