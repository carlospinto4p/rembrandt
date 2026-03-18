"""Tests for rembrandt.spaced_repetition."""

from datetime import datetime, timedelta

import pytest

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    ReviewConfig,
    SessionMode,
    UserProgress,
)
from rembrandt.spaced_repetition import (
    _fuzz_interval,
    review,
    select_concepts,
)

pytestmark = pytest.mark.asyncio


# --- SM-2 Review Tests (REVIEW state) ---


def _review_progress(**kwargs) -> UserProgress:
    """Create a REVIEW-state progress for tests."""
    defaults = dict(
        user_id=1,
        concept_id=1,
        state=CardState.REVIEW,
        next_review=datetime(2026, 1, 1),
    )
    defaults.update(kwargs)
    return UserProgress(**defaults)


async def test_review_first_correct():
    progress = _review_progress(
        repetitions=0, interval=0,
    )
    updated = review(progress, quality=5)
    assert updated.interval == 1
    assert updated.repetitions == 1
    assert updated.easiness_factor >= 2.5
    assert updated.state == CardState.REVIEW


async def test_review_second_correct():
    config = ReviewConfig(max_fuzz_factor=0)
    progress = _review_progress(
        repetitions=1, interval=1,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.interval == 6
    assert updated.repetitions == 2


async def test_review_third_correct():
    config = ReviewConfig(max_fuzz_factor=0)
    progress = _review_progress(
        repetitions=2, interval=6,
        easiness_factor=2.5,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.interval == 15
    assert updated.repetitions == 3


async def test_review_incorrect_enters_relearning():
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0
    assert updated.repetitions == 0


async def test_review_incorrect_no_relearning_steps():
    config = ReviewConfig(relearning_steps=[])
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(
        progress, quality=1, config=config,
    )
    assert updated.state == CardState.REVIEW
    assert updated.repetitions == 0
    assert updated.interval >= 1


async def test_review_ef_decreases_on_low_quality():
    progress = _review_progress(
        easiness_factor=2.5,
    )
    updated = review(progress, quality=3)
    assert updated.easiness_factor < 2.5


async def test_review_easiness_factor_minimum():
    progress = _review_progress(
        easiness_factor=1.3,
    )
    updated = review(progress, quality=0)
    assert updated.easiness_factor >= 1.3


async def test_review_invalid_quality():
    progress = _review_progress()
    with pytest.raises(
        ValueError, match="quality must be 0-5",
    ):
        review(progress, quality=6)

    with pytest.raises(
        ValueError, match="quality must be 0-5",
    ):
        review(progress, quality=-1)


async def test_review_next_review_in_future():
    progress = _review_progress()
    updated = review(progress, quality=5)
    assert updated.next_review > datetime.now()


# --- Learning Step Tests ---


async def test_new_card_enters_learning():
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = review(progress, quality=5)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0


async def test_new_card_fail_enters_learning():
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0


async def test_new_card_no_learning_steps_graduates():
    config = ReviewConfig(
        learning_steps=[],
        graduating_interval=3,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.REVIEW
    assert updated.interval == 3
    assert updated.repetitions == 1


async def test_learning_step_advancement():
    config = ReviewConfig(learning_steps=[1, 10])
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=0,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 1
    expected_delta = timedelta(minutes=10)
    actual_delta = (
        updated.next_review - datetime.now()
    )
    assert abs(
        actual_delta.total_seconds()
        - expected_delta.total_seconds()
    ) < 5


async def test_learning_graduation():
    config = ReviewConfig(
        learning_steps=[1, 10],
        graduating_interval=1,
    )
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=1,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.REVIEW
    assert updated.interval == 1
    assert updated.repetitions == 1
    assert updated.step_index == 0


async def test_learning_fail_resets_to_step_zero():
    config = ReviewConfig(learning_steps=[1, 10])
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=1,
    )
    updated = review(
        progress, quality=1, config=config,
    )
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0
    expected_delta = timedelta(minutes=1)
    actual_delta = (
        updated.next_review - datetime.now()
    )
    assert abs(
        actual_delta.total_seconds()
        - expected_delta.total_seconds()
    ) < 5


async def test_learning_ef_always_updated():
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
        easiness_factor=2.5,
    )
    updated = review(progress, quality=3)
    assert updated.easiness_factor < 2.5


# --- Relearning Step Tests ---


async def test_lapse_enters_relearning():
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0
    assert updated.repetitions == 0


async def test_relearning_step_advancement():
    config = ReviewConfig(relearning_steps=[5, 20])
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=30,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 1


async def test_relearning_returns_to_review():
    config = ReviewConfig(
        relearning_steps=[10],
        lapse_new_interval_factor=0.7,
        lapse_min_interval=1,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=30,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.REVIEW
    assert updated.repetitions == 1
    assert updated.interval == 21


async def test_relearning_min_interval():
    config = ReviewConfig(
        relearning_steps=[10],
        lapse_new_interval_factor=0.1,
        lapse_min_interval=5,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=10,
    )
    updated = review(
        progress, quality=5, config=config,
    )
    assert updated.state == CardState.REVIEW
    assert updated.interval == 5


async def test_relearning_fail_resets_to_step_zero():
    config = ReviewConfig(relearning_steps=[5, 20])
    progress = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.RELEARNING,
        step_index=1,
        interval=30,
    )
    updated = review(
        progress, quality=1, config=config,
    )
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0


# --- Config Tests ---


async def test_custom_learning_steps():
    config = ReviewConfig(
        learning_steps=[1, 5, 15],
        graduating_interval=2,
    )
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 0

    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 1

    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 2

    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW
    assert p.interval == 2


async def test_single_learning_step():
    config = ReviewConfig(
        learning_steps=[5],
        graduating_interval=1,
    )
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 0

    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW
    assert p.interval == 1


async def test_empty_learning_and_relearning_steps():
    config = ReviewConfig(
        learning_steps=[],
        relearning_steps=[],
        graduating_interval=1,
    )
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW

    p = review(p, quality=1, config=config)
    assert p.state == CardState.REVIEW


# --- Concept Selection Tests ---


async def test_select_concepts_returns_new(
    db_with_concepts,
):
    concepts = await select_concepts(
        db_with_concepts, 1, count=3,
    )
    assert len(concepts) == 3


async def test_select_concepts_empty_db(tmp_path):
    db = await Database.connect(
        tmp_path / "empty.db",
    )
    concepts = await select_concepts(
        db, 1, count=5,
    )
    assert concepts == []
    await db.close()


async def test_select_concepts_due_before_new(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    due_concept = all_concepts[0]

    progress = UserProgress(
        user_id=1,
        concept_id=due_concept.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    await db_with_concepts.upsert_progress(progress)

    concepts = await select_concepts(
        db_with_concepts, 1, count=1,
    )
    assert len(concepts) == 1
    assert concepts[0].id == due_concept.id


async def test_select_concepts_learning_before_due(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    learning_concept = all_concepts[0]
    review_concept = all_concepts[1]

    await db_with_concepts.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=learning_concept.id,
            state=CardState.LEARNING,
            next_review=datetime(2020, 1, 1),
        ),
    )
    await db_with_concepts.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=review_concept.id,
            state=CardState.REVIEW,
            next_review=datetime(2020, 1, 1),
        ),
    )

    concepts = await select_concepts(
        db_with_concepts, 1, count=1,
    )
    assert len(concepts) == 1
    assert concepts[0].id == learning_concept.id


async def test_select_concepts_respects_count(
    db_with_concepts,
):
    concepts = await select_concepts(
        db_with_concepts, 1, count=2,
    )
    assert len(concepts) == 2


# --- Session Mode Tests ---


async def test_select_concepts_learn_new_only(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    due_concept = all_concepts[0]
    progress = UserProgress(
        user_id=1,
        concept_id=due_concept.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    await db_with_concepts.upsert_progress(progress)

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        mode=SessionMode.LEARN_NEW,
    )
    ids = [c.id for c in concepts]
    assert due_concept.id not in ids
    assert len(concepts) == 4


async def test_select_concepts_review_due_only(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    due_concept = all_concepts[0]
    progress = UserProgress(
        user_id=1,
        concept_id=due_concept.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    await db_with_concepts.upsert_progress(progress)

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        mode=SessionMode.REVIEW_DUE,
    )
    assert len(concepts) == 1
    assert concepts[0].id == due_concept.id


async def test_select_concepts_mixed_default(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    due_concept = all_concepts[0]
    progress = UserProgress(
        user_id=1,
        concept_id=due_concept.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    await db_with_concepts.upsert_progress(progress)

    concepts = await select_concepts(
        db_with_concepts, 1, count=3,
    )
    assert len(concepts) == 3
    assert concepts[0].id == due_concept.id


async def test_select_concepts_concept_ids_filter(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    subset_ids = [
        all_concepts[0].id, all_concepts[1].id,
    ]

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        concept_ids=subset_ids,
    )
    assert len(concepts) == 2
    result_ids = {c.id for c in concepts}
    assert result_ids == set(subset_ids)


# --- Prioritize Weak Tests ---


async def test_select_concepts_prioritize_weak(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    strong = all_concepts[0]
    weak = all_concepts[1]

    for c in [strong, weak]:
        await db_with_concepts.upsert_progress(
            UserProgress(
                user_id=1,
                concept_id=c.id,
                state=CardState.REVIEW,
                next_review=datetime(2020, 1, 1),
            ),
        )

    for _ in range(4):
        await db_with_concepts.record_answer(
            1, strong.id, "flashcard", True, 5,
        )
        await db_with_concepts.record_answer(
            1, weak.id, "flashcard", False, 1,
        )

    concepts = await select_concepts(
        db_with_concepts, 1, count=2,
        mode=SessionMode.REVIEW_DUE,
        prioritize_weak=True,
    )
    assert len(concepts) == 2
    assert concepts[0].id == weak.id


async def test_select_concepts_no_prioritize_default(
    db_with_concepts,
):
    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
    )
    assert len(concepts) > 0


# --- Fuzz Factor Tests ---


async def test_fuzz_interval_no_fuzz_small():
    assert _fuzz_interval(1, 0.05) == 1
    assert _fuzz_interval(2, 0.05) == 2


async def test_fuzz_interval_disabled():
    assert _fuzz_interval(10, 0) == 10
    assert _fuzz_interval(30, 0) == 30
    assert _fuzz_interval(10, -0.1) == 10


async def test_fuzz_interval_applied(monkeypatch):
    monkeypatch.setattr(
        "rembrandt.spaced_repetition"
        ".random.randint",
        lambda lo, hi: lo,
    )
    assert _fuzz_interval(20, 0.05) == 19

    monkeypatch.setattr(
        "rembrandt.spaced_repetition"
        ".random.randint",
        lambda lo, hi: hi,
    )
    assert _fuzz_interval(20, 0.05) == 21


async def test_fuzz_interval_minimum_one(
    monkeypatch,
):
    monkeypatch.setattr(
        "rembrandt.spaced_repetition"
        ".random.randint",
        lambda lo, hi: lo,
    )
    assert _fuzz_interval(3, 1.0) >= 1


async def test_review_fuzz_applied_to_sm2(
    monkeypatch,
):
    monkeypatch.setattr(
        "rembrandt.spaced_repetition"
        ".random.randint",
        lambda lo, hi: hi,
    )
    progress = _review_progress(
        repetitions=2, interval=6,
        easiness_factor=2.5,
    )
    updated = review(progress, quality=5)
    assert updated.interval == 16


# --- Leech Detection Tests ---


async def test_review_fail_increments_lapse_count():
    progress = _review_progress(
        repetitions=3, interval=10,
        lapse_count=0,
    )
    updated = review(progress, quality=1)
    assert updated.lapse_count == 1


async def test_lapse_count_not_reset_on_pass():
    progress = _review_progress(
        repetitions=3, interval=10,
        lapse_count=5,
    )
    updated = review(progress, quality=5)
    assert updated.lapse_count == 5


async def test_leech_threshold_suspends_card():
    config = ReviewConfig(leech_threshold=3)
    progress = _review_progress(
        repetitions=3, interval=10,
        lapse_count=2,
    )
    updated = review(
        progress, quality=1, config=config,
    )
    assert updated.lapse_count == 3
    assert updated.state == CardState.SUSPENDED


async def test_leech_detection_disabled():
    config = ReviewConfig(leech_threshold=0)
    progress = _review_progress(
        repetitions=3, interval=10,
        lapse_count=100,
    )
    updated = review(
        progress, quality=1, config=config,
    )
    assert updated.state != CardState.SUSPENDED
    assert updated.lapse_count == 101


async def test_suspended_card_skipped_in_select(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    suspended = all_concepts[0]

    await db_with_concepts.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=suspended.id,
            state=CardState.SUSPENDED,
            next_review=datetime(2020, 1, 1),
        ),
    )

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
    )
    ids = [c.id for c in concepts]
    assert suspended.id not in ids


async def test_review_suspended_card_unchanged():
    progress = UserProgress(
        user_id=1,
        concept_id=1,
        state=CardState.SUSPENDED,
        lapse_count=8,
        interval=10,
        easiness_factor=2.0,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.state == CardState.SUSPENDED
    assert updated.lapse_count == 8
    assert updated.interval == 10
    assert updated.easiness_factor == 2.0


# --- Daily Limit Tests ---


async def test_select_concepts_max_new_limits(
    db_with_concepts,
):
    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        max_new=2,
    )
    assert len(concepts) == 2


async def test_select_concepts_max_review_limits(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    for c in all_concepts[:3]:
        await db_with_concepts.upsert_progress(
            UserProgress(
                user_id=1,
                concept_id=c.id,
                state=CardState.REVIEW,
                next_review=datetime(2020, 1, 1),
            ),
        )

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        max_review=1,
    )
    due_ids = {all_concepts[i].id for i in range(3)}
    due_in_result = [
        c for c in concepts if c.id in due_ids
    ]
    assert len(due_in_result) == 1


async def test_select_concepts_in_steps_not_capped(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    for c in all_concepts[:2]:
        await db_with_concepts.upsert_progress(
            UserProgress(
                user_id=1,
                concept_id=c.id,
                state=CardState.LEARNING,
                next_review=datetime(2020, 1, 1),
            ),
        )

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        max_new=0, max_review=0,
    )
    assert len(concepts) == 2
    ids = {c.id for c in concepts}
    assert ids == {
        all_concepts[0].id,
        all_concepts[1].id,
    }


async def test_select_concepts_limits_none_unlimited(
    db_with_concepts,
):
    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        max_new=None, max_review=None,
    )
    assert len(concepts) == 5


# --- Exclude Concept IDs Tests ---


async def test_select_concepts_excludes_ids(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    exclude = {
        all_concepts[0].id, all_concepts[1].id,
    }

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        exclude_concept_ids=exclude,
    )
    returned_ids = {c.id for c in concepts}
    assert returned_ids.isdisjoint(exclude)
    assert len(concepts) == 3


async def test_select_concepts_exclude_all_empty(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    exclude = {c.id for c in all_concepts}

    concepts = await select_concepts(
        db_with_concepts, 1, count=5,
        exclude_concept_ids=exclude,
    )
    assert concepts == []
