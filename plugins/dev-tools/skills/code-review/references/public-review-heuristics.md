# Public Review Heuristics

Use this reference when repo-local architecture guidance is not sufficient and you need external review heuristics.

These heuristics support the review. They do not override repository architecture.

## Reference 1: Google Engineering Practices

Summary:
- Review for design quality, not only local correctness
- Prefer comments that improve long-term code health over cosmetic nitpicks
- Judge complexity in context: if a change makes the system harder to understand, change, or test, it is review-worthy even when behavior is correct
- Approve incremental improvement; do not block only because the code is not perfect if the patch materially improves the area

How to apply:
- Prioritize correctness, design, and tests above style
- Distinguish blocking findings from non-blocking suggestions
- Flag reviewability issues when unrelated churn hides the real behavioral change

Sources:
- https://google.github.io/eng-practices/review/reviewer/standard.html
- https://google.github.io/eng-practices/review/reviewer/looking-for.html

## Reference 2: Coupling, Cohesion, Fan-in, Fan-out

Summary:
- High cohesion means a module has one clear reason to change and a focused purpose
- High coupling means modules know too much about each other or depend on fragile ordering, shared state, or cross-layer details
- High fan-out often indicates an orchestrator or god module that is expensive to change and hard to test
- High fan-in means a change has broad blast radius and needs stronger compatibility reasoning and regression coverage
- A simple stability heuristic is `instability = fan-out / (fan-in + fan-out)`

How to apply:
- Explain architecture comments with explicit trigger signals
- Widen review scope when shared modules or public APIs change
- Treat new dependency edges and dependency hubs as first-class review signals

Sources:
- https://en.wikipedia.org/wiki/Coupling_%28computer_programming%29
- https://en.wikipedia.org/wiki/Cohesion_%28computer_science%29
- https://en.wikipedia.org/wiki/Efferent_coupling

## Reference 3: Architecture Erosion in Code Review

Summary:
- Review comments often miss architecture drift unless reviewers deliberately check for it
- Common erosion patterns include cyclic dependencies, duplicate functionality, layer bypasses, and local shortcuts that weaken intended extension points
- Architectural issues are easier to detect when reviewers inspect module relationships, not only changed lines

How to apply:
- Explicitly inspect dependency direction and extension-point bypasses
- Call out duplicates instead of accepting near-copy implementations in a second module
- Escalate findings that create cycles or weaken architectural seams, even if the local code looks clean

Sources:
- https://arxiv.org/abs/2201.01184
- https://arxiv.org/abs/2212.12168
