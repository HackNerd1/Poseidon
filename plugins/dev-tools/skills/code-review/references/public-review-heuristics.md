# Public Review Heuristics

Use when repo-local architecture guidance is not enough and you need external heuristics.

These heuristics **support** judgment. They do not override repository architecture or first-principles necessity. Do not force-fit a label when evidence is thin.

## How to use

Apply the First Principles section in `../SKILL.md` first. Use a heuristic only when it explains a concrete defect or risk; discard speculative “future-proofing”.

## Reference 1: Google Engineering Practices

Summary:
- Review design quality, not only local correctness
- Prefer comments that improve long-term code health over cosmetic nitpicks
- Complexity is review-worthy when it makes the system harder to understand, change, or test — even if behavior is correct
- Approve incremental improvement; do not block solely for perfection

How to apply:
- Prioritize correctness, necessary design, and tests above style
- Separate blocking findings from non-blocking suggestions
- Flag reviewability issues when unrelated churn hides behavioral change

Sources:
- https://google.github.io/eng-practices/review/reviewer/standard.html
- https://google.github.io/eng-practices/review/reviewer/looking-for.html

## Reference 2: Module Metrics (pointer)

Coupling, cohesion, fan-in, fan-out, and optional instability are defined operationally in `module-review-guide.md`.

Use this section only for external reading; do not duplicate a second scoring system here.

Sources:
- https://en.wikipedia.org/wiki/Coupling_%28computer_programming%29
- https://en.wikipedia.org/wiki/Cohesion_%28computer_science%29
- https://en.wikipedia.org/wiki/Efferent_coupling

## Reference 3: Architecture Erosion

Summary:
- Drift is often missed when reviewers only read changed lines
- Common patterns: cycles, duplicate functionality, layer bypasses, local shortcuts that weaken extension points, and structure added without a current need (see `redundant-design.md`)

How to apply:
- Inspect dependency direction and extension-point bypasses
- Call out duplicates instead of accepting near-copies in a second module
- Escalate cycles and weakened seams even when local code looks clean
- Ask “is this structure necessary for today’s job?” before accepting new abstractions

Sources:
- https://arxiv.org/abs/2201.01184
- https://arxiv.org/abs/2212.12168
