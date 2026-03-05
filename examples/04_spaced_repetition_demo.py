"""Spaced-repetition (SM-2) demo.

Shows how `easiness_factor`, `interval`, `repetitions`, and
`next_review` evolve as a word is reviewed with different quality
scores. No database is needed — this works directly with the
low-level `review()` function and `UserProgress` model.

Usage::

    uv run python examples/04_spaced_repetition_demo.py
"""

from rembrandt.models import UserProgress
from rembrandt.spaced_repetition import review

# Quality labels for readability
LABELS = {
    0: "blackout",
    1: "wrong",
    2: "hard fail",
    3: "hard pass",
    4: "good",
    5: "perfect",
}


def main() -> None:
    progress = UserProgress(user_id="demo", word_id=1)

    # Simulate a sequence of reviews with varying quality
    qualities = [5, 4, 5, 2, 5, 5, 4, 5]

    header = (
        f"{'#':<4}"
        f"{'Quality':<14}"
        f"{'EF':>6}"
        f"{'Interval':>10}"
        f"{'Reps':>6}"
    )
    print("=== SM-2 Spaced-Repetition Demo ===\n")
    print(f"Word ID: {progress.word_id}")
    print(
        f"Initial EF: {progress.easiness_factor}  "
        f"Interval: {progress.interval}  "
        f"Reps: {progress.repetitions}\n"
    )
    print(header)
    print("-" * len(header))

    for i, q in enumerate(qualities, 1):
        progress = review(progress, q)
        label = f"{q} ({LABELS[q]})"
        print(
            f"{i:<4}"
            f"{label:<14}"
            f"{progress.easiness_factor:>6.2f}"
            f"{progress.interval:>10}d"
            f"{progress.repetitions:>6}"
        )

    print(
        f"\nFinal state: EF={progress.easiness_factor}, "
        f"interval={progress.interval}d, "
        f"reps={progress.repetitions}"
    )
    print(
        f"Next review: "
        f"{progress.next_review:%Y-%m-%d %H:%M}"
    )


if __name__ == "__main__":
    main()
