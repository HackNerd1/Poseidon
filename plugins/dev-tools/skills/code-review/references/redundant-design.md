# Redundant Design

Use when checking whether a change (or touched module) adds structure that is **not required** for the actual job.

Load this reference for source changes that introduce modules, abstractions, wrappers, options, registries, or parallel helpers — and whenever first-principles review asks “what is added beyond necessity?”.

Apply the First Principles section in `../SKILL.md` first. This file only covers what remains after necessity: unused, duplicated, or speculative structure.

Do **not**:
- Demand generality “for later”
- Treat a single concrete implementation as incomplete without a second real use
- Relabel taste (“I would split this differently”) as redundancy without unused or duplicated structure

## Signals and Evidence

| Signal | Evidence example | Typical suggestion |
|--------|------------------|--------------------|
| Duplicate functionality | Same behavior already exists elsewhere; new path adds no distinct contract | Extend/reuse the existing path; delete the duplicate |
| Speculative abstraction | Interface / factory / generic layer with one concrete use and no second caller | Collapse to the concrete type until a second use appears |
| Parallel module | New tree for a job an existing module already owns | Move into / extend the owning module |
| Indirection without value | Wrapper that only forwards; no boundary, policy, or test seam | Inline the call |
| Dead extension surface | Options, hooks, registries, or config keys with no current reader/caller | Remove until a caller exists |
| Reimplemented helper | Local copy of an existing util / error type / adapter | Call the existing symbol |

## How to Check

1. State the change’s actual job in one sentence
2. List new public symbols, layers, and config surfaces in the diff
3. For each item, ask: is there a **current** caller/need, or an existing equivalent?
4. Search the repo for prior implementations of the same job before accepting a parallel path
5. Flag only items that fail step 3 or 4

## Finding Shape

Use the report layout in `findings-guide.md`:

- Category: `[Redundancy]` (or `[Architecture]` if the primary issue is a boundary/cycle caused by the redundant path)
- Trigger: `Redundant design`
- Issue / Why / Fix — one line each

Severity hint:
- Divergent behavior or high-fan-in shared path → Warning or Critical
- Local unused / speculative structure → Suggestion

## Related

- Module metrics and dependency census → `module-review-guide.md`
- Severity and wording → `findings-guide.md`
