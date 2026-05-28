# Logging Supplement Guide

When existing logs are insufficient to locate the issue, add logs to the code following these conventions.

## Log Placement Principles

### Key Insertion Points

Add logs at critical nodes in the data flow:

| Node | What to Log | Example Format |
|------|------------|----------------|
| Entry / Input | Raw data summary (type, size/length, first few records) | `[load] type=..., size=..., preview=...` |
| Data Transformation | Key field values before and after transformation | `[transform] before=..., after=...` |
| State Change | State name, old value → new value | `[state] prev=..., next=...` |
| Render / Output | Output target and parameters | `[render] target=..., params=...` |
| External Call | Request summary + response summary | `[api] method=..., url=..., status=..., bodyPreview=...` |
| Exception / Error | Full error info + key context at failure point | `[error] message=..., context=...` |

### Format Convention

Regardless of language, follow a consistent format:

```
Good log: structured, tagged, contains key data needed for decisions
  Format: [Module.operation] key1=value1, key2=value2, ...

Bad log: no context, ambiguous values
```

### Log Levels

| Level | Purpose | Common Names |
|-------|---------|-------------|
| Debug / Trace | Normal flow tracing | `debug` / `trace` / `log` |
| Warning | Abnormal but recoverable | `warn` / `warning` |
| Error | Errors and exceptions | `error` / `fatal` |

### Tag Convention

Use `[Module.operation]` format to mark log source:

- `[Player.init]` — player initialization
- `[Renderer.draw]` — render draw call
- `[Parser.transform]` — data parse / transform
- `[Store.update]` — state update
- `[API.upload]` — upload API call

## Temporary Log Marking

During diagnosis, mark all temporary logs with a `[DEBUG]` prefix for easy batch cleanup later:

```
[DEBUG][Module.operation] key1=value1, ...
```

After diagnosis, search for `[DEBUG]` to locate and remove all temporary logs at once.

## Cleanup

After diagnosis is complete and the fix is verified, remove all log statements added during the session. Keep the code clean.
