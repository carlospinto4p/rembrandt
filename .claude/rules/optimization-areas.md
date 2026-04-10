# Optimization Areas

Project-specific performance areas to watch for when
running `/optimize` or noticing issues during normal work.

## Common Signals

     limit over long-running sessions)

## What to Look For

- **Memory**: unbounded growth, large object retention, unnecessary
  copies, missing cleanup/eviction
- **CPU**: hot loops, redundant computation, expensive operations in
  tight paths, regex compiled per call
- **I/O**: missing connection reuse, redundant HTTP calls
- **Data structures**: lists used for lookups (should be sets/dicts),
  string concatenation in loops, repeated serialization
- **Pydantic**: unnecessary model copies, repeated validation,
  inefficient field access patterns
