# Node.js Runtime Logging

Use this reference for Node.js scripts, servers, workers, and other JavaScript runtimes whose logs are read from a terminal or process log.

## Output contract

Emit one line per record so logs remain searchable and safe for line-oriented collectors. Serialize the payload explicitly with `JSON.stringify` and keep the shared `[DEBUG][Module.operation]` prefix.

```js
process.stdout.write(
  `[DEBUG][Queue.consume] ${JSON.stringify({ queue, jobId })}\n`,
);
```

Use `console.warn` or `console.error` when the runtime's stderr separation is useful:

```js
console.error(`[DEBUG][API.request] ${JSON.stringify({
  method,
  url,
  status: error.response?.status,
  message: error.message,
})}`);
```

Do not log secrets or full request bodies. Prefer counts, IDs, sizes, status codes, and short previews. If a payload can be circular, use a safe serializer before interpolation. Remove temporary `[DEBUG]` statements after the fix is verified.
