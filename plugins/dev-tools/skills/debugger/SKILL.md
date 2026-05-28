---
name: debug
description: Diagnostic debug workflow. Triggers when users provide logs, describe bug symptoms, report white screen / render anomalies / data mismatches, or other runtime issues. Use cases: log-based bug analysis, canvas rendering blank, data vs expected mismatch, audio/video playback issues, third-party library debugging.
arguments: [<bug description or log path>]
---

# Diagnostic Debug Workflow

## Overview

You will follow a rigorous diagnostic process to help users troubleshoot bugs. Core principle: **understand first, hypothesize second, verify third, fix last**. Do not skip information-gathering steps to guess or modify code directly.

## Workflow

### Step 1: Collect Information

First, ask the user for the following (collect at least one item before proceeding):

1. **Logs** (browser Console / terminal output)
2. **Error stack traces** (if any)
3. **Reproduction steps**: what actions were taken, expected vs actual results
4. **Environment info**: browser version, runtime version, dependency versions (if relevant)

If the user has provided a log file path, Read the full file first.

### Step 2: Assess Log Sufficiency

After reading the provided logs, determine:

- Do the logs cover the critical path? (full chain: data load → processing → output)
- Are key variable values recorded? (state values, parameters, return values)
- Is there enough context around the error point?

**If logs are insufficient**, clearly tell the user which parts are missing and ask:

> The current logs lack information about [specific stage], making it impossible to determine the root cause. Should I add logging to the code to capture [specific data]?

Only add logs after the user agrees. Follow the conventions in `references/logging-guide.md` when adding logs.

### Step 3: Locate & Analyze

Once sufficient information is gathered, analyze in this order:

1. **Trace the data flow**: step through data changes from entry point to the failure point
2. **Identify the anomaly**: find where data first deviates from expected values
3. **List possible causes** (ranked by likelihood):

```
Possible causes:

1. [Most likely cause] — Evidence: [specific evidence from logs/code]
2. [Second most likely] — Evidence: [specific evidence from logs/code]
3. [Other possibilities] — Evidence: [specific evidence from logs/code]
```

**Do not modify code in this step.** Only analyze and list causes.

### Step 4: Record the Issue (Optional)

After analysis, ask the user:

> Should I record this issue to `docs/issues/`? The record will include: symptom, root cause analysis, and fix approach.

If the user agrees, write the issue to `docs/issues/<yyyy-mm-dd>-<short-description>.md`.

### Step 5: Wait for Fix Instruction

After listing possible causes, **wait for the user to explicitly request a fix** before modifying code. Do not modify proactively.

Once the user confirms the fix direction:
1. Describe which files will be changed and the specific modifications
2. Execute the changes
3. If UI is involved, remind the user to refresh/restart to verify

### Step 6: Verify

After the fix, guide the user to verify:

1. Reproduce the original bug scenario — confirm it no longer occurs
2. Check related functionality for regressions
3. Confirm no new errors in console/terminal

### Step 7: Log Cleanup

After verification passes, ask the user:

> Verification passed. Should I clean up the debug logs added during diagnosis?

- **User chooses cleanup**: remove all debug log statements added during this session, keeping the code clean
- **User chooses keep**: end the workflow

### Step 8: Notify Completion

After the workflow ends (cleanup done or user chose to keep logs), send a desktop notification to alert the user:

Invoke the notification skill:

```
Skill: dev-tools:notify
Args: Debugger — <brief summary of what was done, e.g. "fixed null pointer in login flow", "analysis complete, 2 root causes found">
```

The summary should briefly describe the outcome — root cause found, fix applied, or issue recorded.

## Key Rules

1. **Ask before guessing**: never speculate without logs — ask for logs first
2. **Don't skip diagnostic steps**: when information is insufficient, prioritize adding logs over guessing from experience
3. **List causes only, don't modify**: Step 3 only outputs a list of possible causes — no code changes
4. **Wait for explicit instruction**: only modify code after the user says "fix" / "change" / "modify" or equivalent
5. **Minimal changes**: only modify code directly related to the issue — no opportunistic refactoring
6. **Reversible logging**: debug logs are temporary — remove them when done, leave no trace
7. **Traceable records**: when the user agrees, record issues to docs/issues/ for future reference

## Edge Cases

- **User refuses to add logs**: provide analysis based on available information, but clearly state the confidence level is limited by incomplete logs
- **Issue spans multiple modules**: analyze module by module, starting from the most likely source of error
- **Intermittent / hard to reproduce**: suggest adding persistent logging (e.g. ring buffer, file-based log buffer) to capture the next occurrence
- **Third-party library issue**: rule out own code first, then check library version and known issues

## Limitations

- Not applicable to compile-time errors (syntax errors, type errors) — these usually have clear error messages
- Not applicable to performance optimization — performance issues require profiling, not this debug workflow
- Not applicable to architecture design reviews
