"""Exercise generation and answer evaluation."""

import json
import re
import random
import unicodedata
from functools import partial
from pathlib import Path

from rembrandt.conjugation import can_conjugate, conjugate, PERSONS, TENSES
from rembrandt.spaced_repetition import QUALITY_PASS_THRESHOLD
from rembrandt.sentences import (
    extend_cloze_templates,
    generate_cloze,
    generate_translation_cloze_sentence,
)
from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    LearningMode,
    Word,
    learning_mode,
)


# Definition-mode exercise distribution threshold
_DEF_MC_THRESHOLD = 0.95

# Maximum attempts to produce a non-identity shuffle
_MAX_SHUFFLE_ATTEMPTS = 20

# Fuzzy matching: max Levenshtein distance by word length
_FUZZY_MAX_SHORT = 1   # words with len <= 5
_FUZZY_MAX_LONG = 2    # words with len > 5

_RE_BRACKETS = re.compile(r"\s*\[.*?\]")
_RE_PARENS = re.compile(r"\s*\(.*?\)")

# --- Helpers ---


def _levenshtein(a: str, b: str) -> int:
    """Compute the Levenshtein edit distance between `a` and `b`.

    :param a: First string.
    :param b: Second string.
    :return: Minimum number of single-character edits.
    """
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + cost,
            ))
        prev = curr
    return prev[-1]


def _fuzzy_threshold(expected: str) -> int:
    """Return the maximum Levenshtein distance for `expected`.

    :param expected: The canonical expected answer.
    :return: Allowed edit distance.
    """
    if len(expected) <= 5:
        return _FUZZY_MAX_SHORT
    return _FUZZY_MAX_LONG


def _strip_accents(text: str) -> str:
    """Remove combining diacritical marks from `text`.

    :param text: Input string.
    :return: String with accents removed.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(
        ch for ch in nfkd
        if unicodedata.category(ch) != "Mn"
    )


def _spanish_word(word: Word) -> str:
    """Return the Spanish word from a bilingual `Word`.

    :param word: The word to inspect.
    :return: The Spanish side of the word pair.
    """
    if word.language_to == "es":
        return word.word_to
    return word.word_from


def _non_spanish_word(word: Word) -> str:
    """Return the non-Spanish word from a bilingual `Word`.

    :param word: The word to inspect.
    :return: The non-Spanish side of the word pair.
    """
    if word.language_to == "es":
        return word.word_from
    return word.word_to


# --- Exercise Generators ---


def generate_flashcard(word: Word) -> Exercise:
    """Create a simple flashcard exercise.

    :param word: The word to test.
    :return: A flashcard `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.FLASHCARD,
    )


def generate_multiple_choice(
    word: Word,
    all_words: list[Word],
    num_options: int = 4,
) -> Exercise:
    """Create a multiple-choice exercise with distractors.

    :param word: The word to test (correct answer).
    :param all_words: Pool of words to draw distractors from.
    :param num_options: Total number of options including the
        correct answer.
    :return: A multiple-choice `Exercise`.
    """
    distractors = [
        w for w in all_words
        if w.id != word.id
    ]
    num_distractors = min(
        num_options - 1, len(distractors)
    )
    chosen = random.sample(distractors, num_distractors)
    options = [word.word_to] + [w.word_to for w in chosen]
    random.shuffle(options)

    return Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=options,
    )


def generate_reverse_flashcard(word: Word) -> Exercise:
    """Create a reverse flashcard exercise.

    Shows the definition/translation; the user types the word.

    :param word: The word to test.
    :return: A reverse-flashcard `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.REVERSE_FLASHCARD,
    )


def generate_self_graded(word: Word) -> Exercise:
    """Create a self-graded flashcard exercise.

    The user sees the word, mentally recalls the definition,
    then reveals it and self-assesses with a quality score.

    :param word: The word to test.
    :return: A self-graded `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.SELF_GRADED,
    )


def generate_gender_match(word: Word) -> Exercise:
    """Create a gender/article matching exercise.

    The user selects the correct article (`el` or `la`) for a
    Spanish noun.

    :param word: The noun to test.
    :return: A gender-match `Exercise`.
    :raises ValueError: If `word.gender` is `None`.
    """
    if word.gender is None:
        raise ValueError(
            "gender_match requires a word with gender"
        )
    spanish = _spanish_word(word)
    article = "el" if word.gender == "m" else "la"
    return Exercise(
        word=word,
        exercise_type=ExerciseType.GENDER_MATCH,
        options=["el", "la"],
        prompt=f"___ {spanish}",
        expected_answer=article,
    )


def generate_conjugation(word: Word) -> Exercise:
    """Create a verb conjugation drill exercise.

    Picks a random tense and person, then conjugates the verb.

    :param word: The verb to test.
    :return: A conjugation `Exercise`.
    :raises ValueError: If `word.conjugation_group` is `None`
        or the verb cannot be conjugated.
    """
    if word.conjugation_group is None:
        raise ValueError(
            "conjugation requires a word with "
            "conjugation_group"
        )
    infinitive = _spanish_word(word)
    group = word.conjugation_group

    if not can_conjugate(infinitive, group):
        raise ValueError(
            f"Cannot conjugate {infinitive!r} "
            f"(group={group!r})"
        )

    tense = random.choice(TENSES)
    person_idx = random.randint(0, 5)
    form = conjugate(infinitive, group, tense, person_idx)

    return Exercise(
        word=word,
        exercise_type=ExerciseType.CONJUGATION,
        prompt=f"{infinitive} — {tense}, {PERSONS[person_idx]}",
        expected_answer=form,
    )


def generate_cloze_exercise(word: Word) -> Exercise:
    """Create a cloze (fill-in-the-blank) exercise.

    Uses template-based sentence generation to produce a
    sentence with a blank where the Spanish word should go.
    The English translation is shown as a hint so the user
    knows which word to fill in.

    :param word: The word to test.
    :return: A cloze `Exercise`.
    """
    spanish = _spanish_word(word)
    english = _non_spanish_word(word)
    sentence, answer = generate_cloze(
        spanish,
        gender=word.gender,
        conjugation_group=word.conjugation_group,
    )
    return Exercise(
        word=word,
        exercise_type=ExerciseType.CLOZE,
        prompt=f"{sentence} ({english})",
        expected_answer=answer,
    )


# Common adjectives as (masculine, feminine) pairs.
_ADJECTIVES: list[tuple[str, str]] = [
    ("blanco", "blanca"),
    ("negro", "negra"),
    ("rojo", "roja"),
    ("pequeño", "pequeña"),
    ("bonito", "bonita"),
    ("nuevo", "nueva"),
    ("viejo", "vieja"),
    ("alto", "alta"),
    ("bajo", "baja"),
    ("bueno", "buena"),
    ("malo", "mala"),
    ("largo", "larga"),
    ("corto", "corta"),
    ("limpio", "limpia"),
    ("rico", "rica"),
]


def extend_adjectives(
    pairs: list[list[str] | tuple[str, str]],
) -> int:
    """Extend the built-in adjective bank.

    :param pairs: List of `[masculine, feminine]` pairs.
    :return: Number of adjectives added.
    :raises ValueError: If a pair does not have exactly 2
        elements.
    """
    count = 0
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError(
                f"Adjective pair must have 2 elements, "
                f"got {len(pair)}: {pair!r}"
            )
        _ADJECTIVES.append((pair[0], pair[1]))
        count += 1
    return count


def load_exercise_config(path: str | Path) -> dict[str, int]:
    """Load exercise configuration from a JSON file.

    A single config file can extend both cloze templates and
    the adjective bank.  The JSON object may contain:

    - `"templates"`: a dict of template-bank keys to lists
      of template strings (same format as
      `load_cloze_templates()`).
    - `"adjectives"`: a list of `[masculine, feminine]`
      string pairs.

    Both keys are optional.

    :param path: Path to the JSON config file.
    :return: A dict with counts: `{"templates": N,
        "adjectives": M}`.
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If any entry is invalid.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result: dict[str, int] = {
        "templates": 0,
        "adjectives": 0,
    }
    if "templates" in data:
        result["templates"] = extend_cloze_templates(
            data["templates"],
        )
    if "adjectives" in data:
        result["adjectives"] = extend_adjectives(
            data["adjectives"],
        )
    return result


def generate_adjective_agreement(word: Word) -> Exercise:
    """Create an adjective gender agreement exercise.

    Shows a noun with its article and an adjective in its
    masculine base form; the user types the gender-agreed
    adjective.

    :param word: A noun with a known `gender`.
    :return: An adjective-agreement `Exercise`.
    :raises ValueError: If `word.gender` is `None`.
    """
    if word.gender is None:
        raise ValueError(
            "adjective_agreement requires a word "
            "with gender"
        )
    spanish = _spanish_word(word)
    article = "el" if word.gender == "m" else "la"
    adj_m, adj_f = random.choice(_ADJECTIVES)
    expected = adj_m if word.gender == "m" else adj_f
    return Exercise(
        word=word,
        exercise_type=ExerciseType.ADJECTIVE_AGREEMENT,
        prompt=f"{article} {spanish} ___ ({adj_m})",
        expected_answer=expected,
    )


def generate_translation_cloze(word: Word) -> Exercise:
    """Create a translation cloze exercise.

    Shows an English context sentence with a blank and the
    English word as a hint; the user types the Spanish
    translation.  Works regardless of language orientation.

    :param word: The word to test.
    :return: A translation-cloze `Exercise`.
    """
    english = _non_spanish_word(word)
    spanish = _spanish_word(word)
    sentence, hint = generate_translation_cloze_sentence(
        english,
        gender=word.gender,
        conjugation_group=word.conjugation_group,
    )
    return Exercise(
        word=word,
        exercise_type=ExerciseType.TRANSLATION_CLOZE,
        prompt=f"{sentence} ({hint})",
        expected_answer=spanish,
    )


def generate_sentence_order(word: Word) -> Exercise:
    """Create a sentence ordering exercise.

    Generates a complete Spanish sentence using the cloze
    template system, then scrambles the words.  The user
    must reconstruct the original word order.

    :param word: The word to build the sentence around.
    :return: A sentence-order `Exercise` whose `prompt`
        contains the scrambled words separated by ` / `.
    """
    spanish = _spanish_word(word)
    sentence, _ = generate_cloze(
        spanish,
        gender=word.gender,
        conjugation_group=word.conjugation_group,
    )
    complete = sentence.replace("___", spanish)
    words_list = complete.split()
    shuffled = words_list[:]
    # Ensure the shuffled order differs from the original.
    attempts = 0
    while shuffled == words_list and len(words_list) > 1:
        random.shuffle(shuffled)
        attempts += 1
        if attempts > _MAX_SHUFFLE_ATTEMPTS:
            break
    return Exercise(
        word=word,
        exercise_type=ExerciseType.SENTENCE_ORDER,
        prompt=" / ".join(shuffled),
        expected_answer=complete,
    )


def _eligible_translation_types(
    word: Word, all_words: list[Word],
) -> list[ExerciseType]:
    """Determine eligible exercise types for translation mode.

    Returns only `FLASHCARD` when fewer than 2 words are
    available (multiple choice needs distractors).

    :param word: The word to test.
    :param all_words: Pool of words for distractor exercises.
    :return: List of eligible exercise types.
    """
    if len(all_words) < 2:
        return [ExerciseType.FLASHCARD]

    pool: list[ExerciseType] = [
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
    ]
    if word.gender is not None:
        pool.append(ExerciseType.GENDER_MATCH)
        pool.append(ExerciseType.ADJECTIVE_AGREEMENT)
    if (
        word.conjugation_group is not None
        and can_conjugate(
            _spanish_word(word),
            word.conjugation_group,
        )
    ):
        pool.append(ExerciseType.CONJUGATION)
    # Cloze types need a known POS (nouns have gender,
    # verbs have conjugation_group). Words without
    # either produce nonsensical template sentences.
    if (
        word.gender is not None
        or word.conjugation_group is not None
    ):
        pool.append(ExerciseType.CLOZE)
        pool.append(ExerciseType.TRANSLATION_CLOZE)
        pool.append(ExerciseType.SENTENCE_ORDER)
    return pool


def generate_exercise(
    word: Word,
    all_words: list[Word],
) -> Exercise:
    """Generate an exercise appropriate for the word's mode.

    **Translation mode** (`language_from != language_to`):
    picks randomly from a pool of eligible exercise types.
    Falls back to flashcard when fewer than 2 words are
    available (multiple choice needs distractors).

    **Definition mode** (`language_from == language_to`):
    95% multiple choice, 5% self-graded (word discovery).
    Falls back to self-graded when fewer than 2 words are
    available. Never uses flashcard or reverse flashcard
    (typing exact definitions/words is bad UX due to
    synonyms).

    :param word: The word to test.
    :param all_words: Pool of words for multiple-choice
        distractors.
    :return: A generated `Exercise`.
    """
    mode = learning_mode(word)

    if mode == LearningMode.TRANSLATION:
        pool = _eligible_translation_types(
            word, all_words,
        )
        dispatch = {
            ExerciseType.FLASHCARD: partial(
                generate_flashcard, word,
            ),
            ExerciseType.MULTIPLE_CHOICE: partial(
                generate_multiple_choice, word, all_words,
            ),
            ExerciseType.GENDER_MATCH: partial(
                generate_gender_match, word,
            ),
            ExerciseType.ADJECTIVE_AGREEMENT: partial(
                generate_adjective_agreement, word,
            ),
            ExerciseType.CONJUGATION: partial(
                generate_conjugation, word,
            ),
            ExerciseType.CLOZE: partial(
                generate_cloze_exercise, word,
            ),
            ExerciseType.TRANSLATION_CLOZE: partial(
                generate_translation_cloze, word,
            ),
            ExerciseType.SENTENCE_ORDER: partial(
                generate_sentence_order, word,
            ),
        }
        chosen = random.choice(pool)
        return dispatch[chosen]()

    # Definition mode
    if len(all_words) < 2:
        return generate_self_graded(word)

    roll = random.random()
    if roll < _DEF_MC_THRESHOLD:
        return generate_multiple_choice(word, all_words)
    return generate_self_graded(word)


# --- Answer Evaluation ---


def _acceptable_answers(expected: str) -> list[str]:
    """Return variant forms of `expected` for flexible matching.

    Strips parenthetical `(...)` and bracket `[...]` content,
    then splits by semicolons and commas to yield individual
    senses (e.g. ``"to say, to tell"`` accepts ``"to say"``).

    :param expected: The canonical expected answer.
    :return: List of acceptable answer strings (always includes
        the original `expected`).
    """
    cleaned = _RE_BRACKETS.sub("", expected)
    cleaned = _RE_PARENS.sub("", cleaned)
    segments = [
        s.strip() for s in cleaned.split(";") if s.strip()
    ]
    # Also split comma-separated alternatives
    parts: list[str] = []
    for seg in segments:
        parts.extend(
            p.strip() for p in seg.split(",")
            if p.strip()
        )
    answers = [expected] + segments + parts
    seen: set[str] = set()
    unique: list[str] = []
    for a in answers:
        low = a.lower()
        if low not in seen:
            seen.add(low)
            unique.append(a)
    return unique


def _answers_match(
    given: str, expected: str,
) -> str:
    """Check if `given` matches `expected` with flexible rules.

    Handles parenthetical/bracket stripping, semicolon-separated
    senses, optional "to " verb prefix differences, accent
    tolerance, and fuzzy matching (Levenshtein distance).

    :param given: The user's answer (already stripped).
    :param expected: The canonical expected answer.
    :return: `"exact"` for an exact or accent-tolerant match,
        `"fuzzy"` for a near-miss within the edit-distance
        threshold, or `"no"` if no match.
    """
    g = given.lower()
    g_stripped = _strip_accents(g)
    candidates = _acceptable_answers(expected)
    best_distance = None
    for c in candidates:
        e = c.lower()
        if g == e:
            return "exact"
        # Accent-tolerant comparison
        e_stripped = _strip_accents(e)
        if g_stripped == e_stripped:
            return "exact"
        # "to X" ↔ "X" handling
        if g.startswith("to ") and g[3:] == e:
            return "exact"
        if e.startswith("to ") and e[3:] == g:
            return "exact"
        # Track best fuzzy distance
        threshold = _fuzzy_threshold(e)
        dist = _levenshtein(g_stripped, e_stripped)
        if dist <= threshold:
            if best_distance is None or dist < best_distance:
                best_distance = dist
    if best_distance is not None:
        return "fuzzy"
    return "no"


def _resolve_option_number(
    text: str,
    options: list[str],
) -> str:
    """Resolve a numeric answer to its option text.

    If `text` is a digit string and falls within the valid
    range of `options`, return the corresponding option.
    Otherwise return `text` unchanged.

    :param text: The user's raw answer.
    :param options: The exercise option list.
    :return: Resolved option text or the original `text`.
    """
    if text.isdigit() and options:
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return options[idx]
    return text


def evaluate_answer(
    exercise: Exercise,
    answer_text: str = "",
    quality: int | None = None,
) -> AnswerResult:
    """Evaluate a user's answer against the expected value.

    Comparison is case-insensitive and strips whitespace.

    For exercises with a non-empty `expected_answer` (e.g.
    `GENDER_MATCH`, `CONJUGATION`, `CLOZE`), that value is
    used as the expected answer directly.

    For `REVERSE_FLASHCARD` exercises the expected answer is
    `word_from` (the term) instead of `word_to`.

    For `SELF_GRADED` exercises the `quality` parameter (0-5)
    is required; `correct` is `True` when `quality >= 3`.

    :param exercise: The exercise being answered.
    :param answer_text: The user's answer text (ignored for
        self-graded exercises).
    :param quality: Self-assessment score 0-5 (required for
        `SELF_GRADED`, ignored otherwise).
    :return: An `AnswerResult` indicating correctness.
    :raises ValueError: If `quality` is missing or out of
        range for a `SELF_GRADED` exercise.
    """
    etype = exercise.exercise_type

    if etype == ExerciseType.SELF_GRADED:
        if quality is None:
            raise ValueError(
                "quality is required for SELF_GRADED "
                "exercises"
            )
        if not 0 <= quality <= 5:
            raise ValueError(
                f"quality must be 0-5, got {quality}"
            )
        expected = exercise.word.word_to
        return AnswerResult(
            correct=quality >= QUALITY_PASS_THRESHOLD,
            expected=expected,
            given=str(quality),
            word=exercise.word,
        )

    if exercise.expected_answer:
        expected = exercise.expected_answer
    elif etype == ExerciseType.REVERSE_FLASHCARD:
        expected = exercise.word.word_from
    else:
        expected = exercise.word.word_to

    given = _resolve_option_number(
        answer_text.strip(), exercise.options,
    )

    match = _answers_match(given, expected)
    return AnswerResult(
        correct=match in ("exact", "fuzzy"),
        expected=expected,
        given=given,
        word=exercise.word,
        near_miss=match == "fuzzy",
    )
