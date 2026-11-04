# Python Runtime Logging

Use this reference for Python scripts, services, workers, and test processes.

## Output contract

Use the standard `logging` module and serialize structured data with `json.dumps`. Keep the shared `[DEBUG][Module.operation]` prefix in the message and avoid passing an unstructured object representation.

```python
import json
import logging

logger = logging.getLogger(__name__)
logger.debug(
    "[DEBUG][Parser.transform] %s",
    json.dumps(
        {"before": before, "after": after},
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ),
)
```

For exceptions, include the message and relevant context while preserving the traceback with `logger.exception`:

```python
try:
    result = parse(payload)
except Exception as exc:
    logger.exception(
        "[DEBUG][Parser.parse] %s",
        json.dumps({"message": str(exc), "payload_size": len(payload)}),
    )
    raise
```

Do not log credentials, tokens, or full sensitive payloads. Remove temporary `[DEBUG]` statements after verification, following the shared logging guide.
