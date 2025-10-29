import re

def number_to_words(num: int) -> str:
    """Convert numbers 0-99 to words for TTS."""
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
    teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 
             'sixteen', 'seventeen', 'eighteen', 'nineteen']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
    
    if num < 10:
        return ones[num]
    elif num < 20:
        return teens[num - 10]
    elif num < 100:
        ten = num // 10
        one = num % 10
        if one == 0:
            return tens[ten]
        return f"{tens[ten]} {ones[one]}"
    return str(num)

def preprocess_for_tts(text: str) -> str:
    """
    Preprocess text specifically for TTS to handle Reddit-specific patterns
    and problematic phrases. This runs BEFORE clean_story to handle TTS issues.
    """
    # Convert age/gender abbreviations (17M, 25F, etc.) to spoken form
    # Pattern: number followed by M or F (case insensitive)
    def replace_age_gender(match):
        num = int(match.group(1))
        gender = match.group(2).upper()
        num_words = number_to_words(num)
        return f"{num_words} {gender}"
    
    # Match patterns like "17M", "25F", "(17M)", "I'm 17M", "I am 17F"
    text = re.sub(r'\b(\d{1,2})([MF])\b', replace_age_gender, text, flags=re.IGNORECASE)
    
    # Handle common Reddit acronyms for better pronunciation
    reddit_acronyms = {
        r'\bAITA\b': 'Am I the asshole',
        r'\bTIFU\b': 'Today I fucked up',
        r'\bIMO\b': 'in my opinion',
        r'\bIMHO\b': 'in my humble opinion',
        r'\bTBH\b': 'to be honest',
        r'\bIRL\b': 'in real life',
        r'\bBTW\b': 'by the way',
        r'\bFWIW\b': 'for what it\'s worth',
        r'\bSO\b': 'significant other',  # Context: "my SO"
        r'\bBF\b': 'boyfriend',
        r'\bGF\b': 'girlfriend',
        r'\bDH\b': 'dear husband',
        r'\bDW\b': 'dear wife',
    }
    
    for acronym, expansion in reddit_acronyms.items():
        text = re.sub(acronym, expansion, text, flags=re.IGNORECASE)
    
    # Expand contractions that TTS struggles with
    # Order matters - do compound contractions first, then simple ones
    contractions = {
        # Compound contractions (do these first)
        r"\bshouldn't've\b": "should not have",
        r"\bcouldn't've\b": "could not have",
        r"\bwouldn't've\b": "would not have",
        r"\bmightn't've\b": "might not have",
        r"\bmustn't've\b": "must not have",
        r"\by'all'd've\b": "you all would have",
        r"\bwould've\b": "would have",
        r"\bcould've\b": "could have",
        r"\bshould've\b": "should have",
        r"\bmight've\b": "might have",
        r"\bmust've\b": "must have",
        
        # Negative contractions
        r"\bwon't\b": "will not",
        r"\bcan't\b": "cannot",
        r"\bain't\b": "am not",
        r"\baren't\b": "are not",
        r"\bwasn't\b": "was not",
        r"\bweren't\b": "were not",
        r"\bhasn't\b": "has not",
        r"\bhaven't\b": "have not",
        r"\bhadn't\b": "had not",
        r"\bdoesn't\b": "does not",
        r"\bdon't\b": "do not",
        r"\bdidn't\b": "did not",
        r"\bisn't\b": "is not",
        r"\bshouldn't\b": "should not",
        r"\bcouldn't\b": "could not",
        r"\bwouldn't\b": "would not",
        r"\bmightn't\b": "might not",
        r"\bmustn't\b": "must not",
        
        # Positive contractions (these are trickier - be careful with context)
        r"\bI'm\b": "I am",
        r"\byou're\b": "you are",
        r"\bhe's\b": "he is",
        r"\bshe's\b": "she is",
        r"\bit's\b": "it is",
        r"\bwe're\b": "we are",
        r"\bthey're\b": "they are",
        r"\bthat's\b": "that is",
        r"\bwho's\b": "who is",
        r"\bwhat's\b": "what is",
        r"\bwhere's\b": "where is",
        r"\bwhen's\b": "when is",
        r"\bwhy's\b": "why is",
        r"\bhow's\b": "how is",
        r"\bthere's\b": "there is",
        r"\bhere's\b": "here is",
        
        # Other common ones
        r"\bI'll\b": "I will",
        r"\byou'll\b": "you will",
        r"\bhe'll\b": "he will",
        r"\bshe'll\b": "she will",
        r"\bit'll\b": "it will",
        r"\bwe'll\b": "we will",
        r"\bthey'll\b": "they will",
        r"\bthat'll\b": "that will",
        
        r"\bI've\b": "I have",
        r"\byou've\b": "you have",
        r"\bwe've\b": "we have",
        r"\bthey've\b": "they have",
        
        r"\bI'd\b": "I would",
        r"\byou'd\b": "you would",
        r"\bhe'd\b": "he would",
        r"\bshe'd\b": "she would",
        r"\bwe'd\b": "we would",
        r"\bthey'd\b": "they would",
        r"\bthat'd\b": "that would",
        
        r"\by'all\b": "you all",
    }
    
    for contraction, expansion in contractions.items():
        text = re.sub(contraction, expansion, text, flags=re.IGNORECASE)
    
    return text

def clean_story(text: str) -> str:
    """
    Clean Reddit story text - remove markdown, links, etc.
    Returns the ORIGINAL text (with contractions) for display/subtitles.
    """
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

def prepare_text_for_tts(text: str) -> str:
    """
    Prepare text specifically for TTS audio generation.
    This expands contractions and handles Reddit patterns for clear pronunciation.
    Use this for generating audio, but keep original text for subtitles.
    """
    # First clean the story (remove markdown, links, etc)
    text = clean_story(text)
    
    # Then apply TTS preprocessing (expand contractions, handle age/gender, etc)
    text = preprocess_for_tts(text)
    
    return text

def word_count(text: str) -> int:
    return len(text.split())
