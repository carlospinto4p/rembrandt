"""Exercise generation and answer evaluation."""

import random
import re
import unicodedata

from rembrandt.spaced_repetition import QUALITY_PASS_THRESHOLD
from rembrandt.models import (
    AnswerResult,
    Concept,
    Exercise,
    ExerciseType,
)

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


# --- Exercise Generators ---


def generate_flashcard(concept: Concept) -> Exercise:
    """Create a simple flashcard exercise.

    :param concept: The concept to test.
    :return: A flashcard `Exercise`.
    """
    return Exercise(
        concept=concept,
        exercise_type=ExerciseType.FLASHCARD,
    )


def generate_multiple_choice(
    concept: Concept,
    all_concepts: list[Concept],
    num_options: int = 4,
    *,
    preferred: list[Concept] | None = None,
) -> Exercise:
    """Create a multiple-choice exercise with distractors.

    When `preferred` is given, distractors are drawn from it
    first (e.g. same-topic concepts). Remaining slots are
    filled from `all_concepts`.

    :param concept: The concept to test (correct answer).
    :param all_concepts: Fallback pool of concepts to draw
        distractors from.
    :param num_options: Total number of options including the
        correct answer.
    :param preferred: Preferred distractor pool (e.g.
        same-topic concepts). Used first before falling
        back to `all_concepts`.
    :return: A multiple-choice `Exercise`.
    """
    need = num_options - 1
    chosen: list[Concept] = []
    used_ids = {concept.id}

    if preferred:
        pool = [
            c for c in preferred
            if c.id not in used_ids
        ]
        take = min(need, len(pool))
        chosen = random.sample(pool, take)
        used_ids.update(c.id for c in chosen)

    remaining = need - len(chosen)
    if remaining > 0:
        fallback = [
            c for c in all_concepts
            if c.id not in used_ids
        ]
        take = min(remaining, len(fallback))
        chosen += random.sample(fallback, take)

    options = [concept.back] + [c.back for c in chosen]
    random.shuffle(options)

    return Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=options,
    )


def generate_self_graded(concept: Concept) -> Exercise:
    """Create a self-graded flashcard exercise.

    The user sees the front, mentally recalls the back,
    then reveals it and self-assesses with a quality score.

    :param concept: The concept to test.
    :return: A self-graded `Exercise`.
    """
    return Exercise(
        concept=concept,
        exercise_type=ExerciseType.SELF_GRADED,
    )


def generate_exercise(
    concept: Concept,
    all_concepts: list[Concept],
    *,
    preferred: list[Concept] | None = None,
) -> Exercise:
    """Generate an exercise for a concept.

    Picks uniformly from all exercise types. Falls back to
    flashcard/self-graded when fewer than 2 concepts are
    available (multiple choice needs distractors).

    :param concept: The concept to test.
    :param all_concepts: Pool of concepts for multiple-choice
        distractors.
    :param preferred: Preferred distractor pool passed to
        `generate_multiple_choice` (e.g. same-topic
        concepts).
    :return: A generated `Exercise`.
    """
    if len(all_concepts) < 2:
        pool = [
            ExerciseType.FLASHCARD,
            ExerciseType.SELF_GRADED,
        ]
    else:
        pool = list(ExerciseType)

    chosen = random.choice(pool)
    if chosen == ExerciseType.FLASHCARD:
        return generate_flashcard(concept)
    if chosen == ExerciseType.MULTIPLE_CHOICE:
        return generate_multiple_choice(
            concept, all_concepts,
            preferred=preferred,
        )
    return generate_self_graded(concept)


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

    For `SELF_GRADED` exercises the `quality` parameter (0-5)
    is required; `correct` is `True` when `quality >= 3`.

    `FLASHCARD` exercises support both modes: when `quality`
    is provided, quality-based evaluation is used (same as
    `SELF_GRADED`); when omitted, text-based matching is
    used.

    :param exercise: The exercise being answered.
    :param answer_text: The user's answer text (ignored for
        self-graded exercises and when `quality` is
        provided).
    :param quality: Self-assessment score 0-5 (required for
        `SELF_GRADED`, optional for `FLASHCARD`, ignored
        for `MULTIPLE_CHOICE`).
    :return: An `AnswerResult` indicating correctness.
    :raises ValueError: If `quality` is missing or out of
        range for a `SELF_GRADED` exercise.
    """
    etype = exercise.exercise_type

    # Quality-based path: required for SELF_GRADED,
    # optional for FLASHCARD.
    use_quality = (
        etype == ExerciseType.SELF_GRADED
        or (etype == ExerciseType.FLASHCARD
            and quality is not None)
    )
    if use_quality:
        if quality is None:
            raise ValueError(
                "quality is required for SELF_GRADED "
                "exercises"
            )
        if not 0 <= quality <= 5:
            raise ValueError(
                f"quality must be 0-5, got {quality}"
            )
        expected = exercise.concept.back
        return AnswerResult(
            correct=quality >= QUALITY_PASS_THRESHOLD,
            expected=expected,
            given=str(quality),
            concept=exercise.concept,
        )

    if exercise.expected_answer:
        expected = exercise.expected_answer
    else:
        expected = exercise.concept.back

    given = _resolve_option_number(
        answer_text.strip(), exercise.options,
    )

    match = _answers_match(given, expected)
    return AnswerResult(
        correct=match in ("exact", "fuzzy"),
        expected=expected,
        given=given,
        concept=exercise.concept,
        near_miss=match == "fuzzy",
    )
