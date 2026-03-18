
# Spaced Repetition and the SM-2 Algorithm

## What is spaced repetition?

When you learn a new word, your memory of it fades over time — this
is the **forgetting curve**, first described by Hermann Ebbinghaus
in the 1880s. If you review the word just before you forget it, the
memory gets reinforced and lasts longer. Each successful review
pushes the next forgetting point further into the future.

**Spaced repetition** is a study technique that exploits this
effect: instead of cramming everything at once, you review each
item at increasing intervals. Words you know well are reviewed
rarely; words you struggle with come back frequently.


## The SM-2 algorithm

SM-2 (SuperMemo 2) is the algorithm Rembrandt uses to schedule
reviews. It was created by Piotr Wozniak in 1987 as part of the
SuperMemo project and remains one of the most widely used
spaced-repetition algorithms (Anki's scheduler is based on it).

SM-2 tracks three variables for every user-concept pair:

| Variable            | What it means                          | Start |
|---------------------|----------------------------------------|-------|
| **Easiness Factor** | How easy this concept is for you       |  2.5  |
| **Interval**        | Days until the next review             |  0    |
| **Repetitions**     | Consecutive successful recalls (q >= 3)|  0    |


### Easiness Factor (EF)

EF is a multiplier that controls how fast the gaps between reviews
grow. A higher EF means the algorithm trusts you with longer gaps.

- Starts at **2.5** (neutral).
- Minimum is **1.3** (never drops below this).
- A perfect recall (quality 5) raises it by 0.1.
- A wrong answer (quality 1) drops it by 0.54.

Think of it as a "confidence score" — the better you know a
concept, the higher it climbs.


### Quality scores (0–5)

After each review you rate how well you remembered. SM-2 uses a
0–5 scale:

| Score | Label       | Meaning                                 |
|-------|-------------|-----------------------------------------|
|   0   | Blackout    | No memory at all                        |
|   1   | Wrong       | Wrong answer, but it felt familiar       |
|   2   | Hard fail   | Wrong answer after significant effort   |
|   3   | Hard pass   | Correct, but required significant effort|
|   4   | Good        | Correct after some hesitation            |
|   5   | Perfect     | Instant, effortless recall               |

The key threshold is **3**: scores of 3+ count as a pass
(the interval grows), while 0-2 count as a fail (the concept
resets to square one).


## How the algorithm updates

Each review follows two steps: update the interval, then
update the EF.

### Step 1 — Update the interval

**If quality >= 3 (pass):**

| Repetitions | New interval         |
|-------------|----------------------|
| 0 (first)   | 1 day               |
| 1 (second)  | 6 days              |
| 2+          | `interval * EF` days |

Repetitions increases by 1.

**If quality < 3 (fail):**

- Interval resets to **1 day**.
- Repetitions resets to **0**.

You start over, but your EF carries your history — a concept
you once knew well keeps a higher EF than one you always
struggled with.

### Step 2 — Update the Easiness Factor

The formula adjusts EF based on how well you did:

```
EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
```

In plain terms, for each quality score:

| Quality | EF change |
|---------|-----------|
|    5    |  +0.10    |
|    4    |   0.00    |
|    3    |  −0.14    |
|    2    |  −0.32    |
|    1    |  −0.54    |
|    0    |  −0.80    |

Notice that quality 4 is the "break even" point — it neither
raises nor lowers the EF. Quality 5 is the only score that makes
future intervals grow *faster*.

After the adjustment, EF is clamped to a minimum of **1.3**.

The corresponding code lives in `src/rembrandt/spaced_repetition.py`
(`review()` function).


## Worked example

Starting state: **EF = 2.50, interval = 0, reps = 0**.

| # | Quality       |   EF | Interval | Reps | What happened                   |
|---|---------------|------|----------|------|---------------------------------|
| 1 | 5 (perfect)   | 2.60 |       1d |    1 | First pass → 1 day; EF +0.10   |
| 2 | 4 (good)      | 2.60 |       6d |    2 | Second pass → 6 days; EF +0.00 |
| 3 | 5 (perfect)   | 2.70 |      16d |    3 | 6 × 2.6 = 15.6 → 16; EF +0.10 |
| 4 | 2 (hard fail) | 2.38 |       1d |    0 | Fail → reset; EF −0.32         |
| 5 | 5 (perfect)   | 2.48 |       1d |    1 | First pass again → 1 day       |
| 6 | 5 (perfect)   | 2.58 |       6d |    2 | Second pass → 6 days           |
| 7 | 4 (good)      | 2.58 |      15d |    3 | 6 × 2.58 = 15.48 → 15         |
| 8 | 5 (perfect)   | 2.68 |      39d |    4 | 15 × 2.58 = 38.7 → 39         |

After review 3, the concept is comfortably spaced at 16 days.
Then a single failure (review 4) resets the interval back to
1 day, but the EF stays at 2.38 — not as low as a concept
you've never known.
By review 8, consistent perfect scores have pushed the interval
all the way to 39 days.


## How Rembrandt uses SM-2

The `Session` class (in `src/rembrandt/session.py`) provides a
simple interface on top of SM-2:

1. **`Session.next_exercise()`** calls `select_concepts()`
   which picks concepts that are **due for review** first
   (their `next_review` date is in the past), then fills
   remaining slots with **new concepts** the user hasn't
   seen yet.

2. **`Session.answer(text)`** evaluates the answer and maps the
   result to a quality score:
   - Correct answer → **quality 5** (perfect)
   - Wrong answer → **quality 1** (wrong)

   It then calls `review()` to update the user's progress and
   saves it to the database.

This binary mapping (5 or 1) is intentional — in an automated
exercise session there's no way to measure *how hard* the recall
was, so the algorithm uses the two extremes. Over many reviews,
the EF still converges to the right value for each concept.

For the full quality scale (0-5), you can call the `review()`
function directly.
