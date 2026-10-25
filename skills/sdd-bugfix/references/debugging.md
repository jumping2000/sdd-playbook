# Diagnosis techniques

Use them in step 4 of `sdd-bugfix` (read-only until the cause is verified). The goal is the **root cause**: the place
where the wrong value or state is created, not the place where it shows up.

## 1. Trace back to the source

The symptom (exception, wrong output) is where the problem surfaced. Follow the bad value backwards: who passed it, who
computed it, where it was first wrong. Read the stack trace from the bottom of your own code, not from the top. Fix
where the value becomes wrong; a check added where it surfaces hides the cause and leaves the other callers exposed.

## 2. One hypothesis, one experiment

Write the hypothesis in one sentence ("the date is parsed in local time instead of UTC"). Design the smallest experiment
that can refute it (a log line, a targeted test, a value in the debugger) and change **one** variable at a time. A
refuted hypothesis is progress: write it down in the bug file, so nobody tries it again.

## 3. Bisect

- **In history:** if the behaviour worked in an earlier version, `git bisect start <bad> <good>` and
  `git bisect run <test command>` find the commit that introduced it.
- **In the input:** halve the failing input until the smallest case that still fails remains; it becomes the red test.
- **In the test suite:** a test that passes alone and fails in the suite is polluted by an earlier test (shared state,
  files, environment). Run the failing test after the first half of the preceding tests, then after the second half,
  and keep halving until one test remains: that is the polluter. Then fix the shared state, not the order.

## 4. Flaky tests

A test that fails sometimes is a bug, either in the code or in the test. Common causes: waiting with `sleep` instead of
a condition, dependency on time or time zone, random data without a fixed seed, order of a set or dictionary, shared
state between tests, network. Make the failure reproducible first (loop the test, fix the seed, fake the clock), then
apply the steps above.

## 5. When three fixes have failed

If three fix attempts failed, or every fix reveals a new problem elsewhere, the cause is probably in the design, not in
the line you are looking at. Stop (the skill's rule) and report: what you tried, what each attempt showed, and which
part of the design you suspect. That is a decision for the human.

## After the fix

The fix stays minimal. If the same wrong value could enter through other paths, propose a validation at the boundary
where the value enters the system as a **separate** change (a new bug or task), not in the fix commit.
