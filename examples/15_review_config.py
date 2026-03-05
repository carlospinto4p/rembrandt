"""Customising ReviewConfig for Anki-style scheduling.

Demonstrates how to tune spaced-repetition parameters:
learning steps, graduating interval, relearning steps,
leech threshold, daily card limits, and fuzz factor.

Usage::

    uv run python examples/15_review_config.py
"""

from rembrandt import ReviewConfig
from rembrandt.models import UserProgress
from rembrandt.spaced_repetition import review


def _show_config(label: str, cfg: ReviewConfig) -> None:
    """Print a ReviewConfig side-by-side."""
    print(f"\n--- {label} ---")
    print(f"  learning_steps:       {cfg.learning_steps}")
    print(f"  graduating_interval:  {cfg.graduating_interval}d")
    print(f"  relearning_steps:     {cfg.relearning_steps}")
    print(f"  lapse_new_interval:   {cfg.lapse_new_interval_factor}")
    print(f"  lapse_min_interval:   {cfg.lapse_min_interval}d")
    print(f"  leech_threshold:      {cfg.leech_threshold}")
    print(f"  max_fuzz_factor:      {cfg.max_fuzz_factor}")
    print(f"  max_new_cards:        {cfg.max_new_cards}")
    print(f"  max_review_cards:     {cfg.max_review_cards}")


def _run_reviews(
    label: str, cfg: ReviewConfig, qualities: list[int],
) -> None:
    """Run a sequence of reviews and show state evolution."""
    progress = UserProgress(user_id=1, word_id=1)

    header = (
        f"{'#':<4}"
        f"{'Q':>2}"
        f"{'State':<14}"
        f"{'Step':>5}"
        f"{'Interval':>10}"
        f"{'Lapses':>8}"
    )
    print(f"\n=== {label} ===\n")
    print(header)
    print("-" * len(header))

    for i, q in enumerate(qualities, 1):
        progress = review(progress, q, config=cfg)
        print(
            f"{i:<4}"
            f"{q:>2}"
            f"  {progress.state.value:<12}"
            f"{progress.step_index:>5}"
            f"{progress.interval:>9}d"
            f"{progress.lapse_count:>8}"
        )


def main() -> None:
    # --- Compare default vs custom config ---
    default = ReviewConfig()
    custom = ReviewConfig(
        learning_steps=[1, 5, 15],
        graduating_interval=2,
        relearning_steps=[5, 10],
        lapse_new_interval_factor=0.5,
        lapse_min_interval=2,
        leech_threshold=4,
        max_fuzz_factor=0.0,
        max_new_cards=20,
        max_review_cards=100,
    )

    _show_config("Default Config", default)
    _show_config("Custom Config", custom)

    # --- Same review sequence, different configs ---
    # Good answers to graduate, then a lapse, then recovery
    qualities = [4, 4, 4, 4, 1, 4, 4]

    _run_reviews("Default Config", default, qualities)
    _run_reviews("Custom Config", custom, qualities)


if __name__ == "__main__":
    main()
