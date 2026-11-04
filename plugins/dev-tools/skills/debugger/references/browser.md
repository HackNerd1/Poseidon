# Browser Console Logging

Use this reference when adding temporary logs that will be read in a browser's DevTools Console.

## Output contract

Print each diagnostic record as one JSON string. Do not pass a raw object as a separate `console` argument: DevTools may render it as a live object and the output is harder to copy, compare, and search.

```js
console.log(`[DEBUG][Cart.load] ${JSON.stringify({
  itemCount: items.length,
  userId,
})}`);
```

Use the shared `[DEBUG][Module.operation]` prefix from `logging-guide.md`, followed by a JSON object. Keep the payload limited to values needed to trace the failure; redact tokens, cookies, passwords, and personal data.

## Console methods

```js
console.debug(`[DEBUG][Renderer.draw] ${JSON.stringify({
  canvasId: canvas.id,
  width: canvas.width,
  height: canvas.height,
})}`);

console.warn(`[DEBUG][API.fetch] ${JSON.stringify({
  url,
  status: response.status,
})}`);

console.error(`[DEBUG][API.fetch] ${JSON.stringify({
  message: error.message,
  stack: error.stack,
  url,
})}`);
```

For values that may be `undefined` or circular, use a small local serializer and still emit a single string:

```js
const toLogJson = (value) => {
  try {
    return JSON.stringify(value);
  } catch {
    return JSON.stringify({ serializationError: true });
  }
};

console.log(`[DEBUG][Store.update] ${toLogJson({ prev, next })}`);
```

Do not use `console.log("value", value)` for diagnostic records. Remove all statements containing `[DEBUG]` after verification, as described in the shared guide.
