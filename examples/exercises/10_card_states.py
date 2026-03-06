"""CardState lifecycle walkthrough.

Walks through every `CardState` transition using the low-level
`review()` API: NEW -> LEARNING -> REVIEW -> RELEARNING ->
SUSPENDED. Prints state, interval, step index, and lapse count
after each review.

Usage::

    uv run python examples/exercises/10_card_states.py
"""

from rembrandt import CardState, ReviewConfig
from rembrandt.models import UserProgress
from rembrandt.spaced_repetition import review

# Use deterministic config: no fuzz, low leech threshold
_CONFIG = ReviewConfig(
    learning_steps=[1, 10],
    graduating_interval=1,
    relearning_steps=[10],
    leech_threshold=3,
    max_fuzz_factor=0.0,
)


def _print_step(
    label: str, quality: int, p: UserProgress,
) -> None:
    """Print one row of the walkthrough."""
    print(
        f"  {label:<30} q={quality}  "
        f"state={p.state.value:<13} "
        f"step={p.step_index}  "
        f"interval={p.interval}d  "
        f"lapses={p.lapse_count}"
    )


def main() -> None:
    p = UserProgress(user_id=1, word_id=1)
    print("=== CardState Lifecycle ===\n")
    print(f"  Initial state: {p.state.value}\n")

    # 1. NEW -> LEARNING (first review enters learning steps)
    p = review(p, 4, config=_CONFIG)
    _print_step("NEW -> LEARNING", 4, p)
    assert p.state == CardState.LEARNING

    # 2. LEARNING step 0 -> step 1 (pass advances)
    p = review(p, 4, config=_CONFIG)
    _print_step("LEARNING step 0 -> 1", 4, p)
    assert p.state == CardState.LEARNING

    # 3. LEARNING -> REVIEW (graduate after last step)
    p = review(p, 5, config=_CONFIG)
    _print_step("LEARNING -> REVIEW", 5, p)
    assert p.state == CardState.REVIEW

    # 4. REVIEW -> REVIEW (successful review)
    p = review(p, 5, config=_CONFIG)
    _print_step("REVIEW (pass)", 5, p)
    assert p.state == CardState.REVIEW

    # Build up some interval for the lapse demo
    p = review(p, 4, config=_CONFIG)
    _print_step("REVIEW (pass)", 4, p)

    # 5. REVIEW -> RELEARNING (lapse on fail)
    p = review(p, 1, config=_CONFIG)
    _print_step("REVIEW -> RELEARNING", 1, p)
    assert p.state == CardState.RELEARNING

    # 6. RELEARNING -> REVIEW (pass relearning)
    p = review(p, 4, config=_CONFIG)
    _print_step("RELEARNING -> REVIEW", 4, p)
    assert p.state == CardState.REVIEW

    # 7. Two more lapses to trigger leech (threshold=3)
    p = review(p, 1, config=_CONFIG)
    _print_step("REVIEW -> RELEARNING", 1, p)

    p = review(p, 4, config=_CONFIG)
    _print_step("RELEARNING -> REVIEW", 4, p)

    # 8. REVIEW -> SUSPENDED (leech threshold reached)
    p = review(p, 1, config=_CONFIG)
    _print_step("REVIEW -> SUSPENDED", 1, p)
    assert p.state == CardState.SUSPENDED

    # 9. SUSPENDED cards are frozen (no state change)
    p = review(p, 5, config=_CONFIG)
    _print_step("SUSPENDED (frozen)", 5, p)
    assert p.state == CardState.SUSPENDED

    print(f"\n  Final lapses: {p.lapse_count}")
    print("  Done! Card is suspended (leech detected).")


if __name__ == "__main__":
    main()
