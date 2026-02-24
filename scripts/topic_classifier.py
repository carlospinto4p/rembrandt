"""Keyword-based topic classifier for vocabulary words.

Assigns topic tags to words by matching their English
definitions against curated keyword lists using word-boundary
regex.

Usage::

    from scripts.topic_classifier import classify

    tags = classify("a piece of bread")  # ["food"]
"""

import re

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "food": [
        "eat", "food", "drink", "meal", "cook",
        "bread", "meat", "fish", "fruit", "vegetable",
        "rice", "soup", "sugar", "salt", "pepper",
        "cheese", "milk", "butter", "oil", "wine",
        "beer", "coffee", "tea", "water", "juice",
        "breakfast", "lunch", "dinner", "dessert",
        "kitchen", "recipe", "dish", "plate", "cup",
        "spoon", "fork", "knife", "hunger", "thirst",
    ],
    "travel": [
        "travel", "trip", "journey", "airport", "hotel",
        "train", "bus", "car", "plane", "boat",
        "ticket", "passport", "luggage", "tourist",
        "road", "highway", "bridge", "station", "port",
        "map", "destination", "arrive", "depart",
    ],
    "body": [
        "body", "head", "face", "eye", "ear", "nose",
        "mouth", "tooth", "tongue", "hair", "hand",
        "finger", "arm", "leg", "foot", "knee",
        "shoulder", "chest", "back", "stomach", "skin",
        "bone", "blood", "heart", "brain", "muscle",
    ],
    "emotions": [
        "feel", "emotion", "happy", "sad", "angry",
        "fear", "afraid", "joy", "love", "hate",
        "surprise", "disgust", "anxiety", "hope",
        "pride", "shame", "guilt", "jealous", "envy",
        "lonely", "bored", "excited", "calm", "nervous",
        "worry", "grief", "sorrow", "delight",
    ],
    "family": [
        "family", "mother", "father", "parent", "child",
        "son", "daughter", "brother", "sister", "husband",
        "wife", "baby", "grandparent", "grandmother",
        "grandfather", "uncle", "aunt", "cousin",
        "nephew", "niece", "relative", "marriage",
        "wedding", "birth", "pregnant",
    ],
    "home": [
        "house", "home", "room", "door", "window",
        "wall", "floor", "roof", "garden", "bedroom",
        "bathroom", "kitchen", "furniture", "chair",
        "table", "bed", "sofa", "lamp", "mirror",
        "stairs", "apartment", "building",
    ],
    "nature": [
        "nature", "tree", "flower", "plant", "forest",
        "mountain", "river", "sea", "ocean", "lake",
        "rain", "snow", "wind", "sun", "moon", "star",
        "sky", "cloud", "earth", "stone", "sand",
        "animal", "bird", "insect", "leaf", "grass",
    ],
    "work": [
        "work", "job", "office", "company", "business",
        "employee", "boss", "salary", "meeting",
        "project", "task", "profession", "career",
        "hire", "employ", "manage", "industry",
    ],
    "time": [
        "time", "hour", "minute", "second", "day",
        "week", "month", "year", "morning", "afternoon",
        "evening", "night", "today", "tomorrow",
        "yesterday", "clock", "watch", "calendar",
        "season", "spring", "summer", "autumn", "winter",
    ],
    "clothing": [
        "clothing", "clothes", "shirt", "pants", "dress",
        "skirt", "jacket", "coat", "shoe", "boot",
        "hat", "sock", "glove", "scarf", "belt",
        "pocket", "button", "fabric", "wear",
    ],
    "health": [
        "health", "sick", "ill", "disease", "doctor",
        "hospital", "medicine", "pain", "fever", "cough",
        "wound", "injury", "surgery", "cure", "heal",
        "symptom", "treatment", "patient", "nurse",
    ],
    "education": [
        "education", "school", "university", "student",
        "teacher", "class", "lesson", "study", "learn",
        "book", "read", "write", "exam", "test",
        "knowledge", "science", "math", "history",
        "library", "degree", "course", "homework",
    ],
}

# Pre-compile patterns: one regex per topic with all keywords
# joined by alternation, anchored to word boundaries.
_TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    topic: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in kws)
        + r")\b",
        re.IGNORECASE,
    )
    for topic, kws in _TOPIC_KEYWORDS.items()
}


def classify(definition: str) -> list[str]:
    """Classify a definition into zero or more topic tags.

    Uses word-boundary regex matching on the English definition
    to find matching topics.

    :param definition: The English definition/gloss to classify.
    :return: Sorted list of matching topic names.
    """
    return sorted(
        topic
        for topic, pattern in _TOPIC_PATTERNS.items()
        if pattern.search(definition)
    )
