# How to cite ACs in tests

ACs restart from AC-001 in every spec, so `scripts/trace_check.py` attributes every citation to a spec. The spec ID is
the one in the title: date plus slug (`SPEC-2026-10-24-export-csv`) or, in projects created earlier, a number
(`SPEC-001`).

1. **Declared file** (recommended with date IDs): the test file names a single spec at the top
   (`# SPEC-2026-10-24-export-csv`) and then cites the ACs in short form: `AC-001`, `AC_001`, `AC001`.
2. **Qualified citation**, valid in any file: `SPEC-2026-10-24-export-csv/AC-001` in strings and comments; in function
   names `SPEC_2026_10_24_export_csv_AC_001` (the slug stays lower case, `AC` upper case). For old numeric IDs also
   `SPEC-001-AC-001`, `SPEC_001_AC_001`, `SPEC001_AC001`.
3. **Short citation in an undeclared file:** valid only if the project has a single spec. With several specs it is
   ambiguous, does not count and `trace_check.py` reports it.

Citations on lines with `TODO`, `FIXME` or `XXX` do not count: a reminder is not a test.

| Language | Example |
|---|---|
| Python (pytest) | `# SPEC-2026-10-24-export-csv` at the top, then `def test_AC_001_exports_valid_csv(): ...` |
| JavaScript / TypeScript | `it("SPEC-2026-10-24-export-csv/AC-001: exports a valid CSV", () => { ... })` |
| Java (JUnit) | `// SPEC-2026-10-24-export-csv` at the top, then `@Test void AC_001_exportsCsv() { ... }` (the ID in the method name: `@DisplayName` does not reach the Surefire JUnit report) |
| C# (xUnit) | `// SPEC-2026-10-24-export-csv` at the top, then `[Fact] public void AC_001_ExportsValidCsv() { ... }` |
| Go | `// SPEC-2026-10-24-export-csv` at the top, then `func TestAC001_ExportsCsv(t *testing.T) { ... }`; with several specs and `--junit`, use the qualified form (`Test_SPEC_2026_10_24_export_csv_AC_001`): in the report the classname is the package, not the file |
| Gherkin | `# SPEC-2026-10-24-export-csv/AC-001` above the `Scenario:` |

With `--junit` a report case is attributed to the file whose path best matches `file` or `classname`
(`tests.a.test_api` ↔ `tests/a/test_api.py`): files with the same name in different folders are not confused.

One test for several ACs is allowed (cite all the IDs). An AC may have several tests: the error cases are needed.

# What makes a test worth locking

`trace_check.py` proves that a test exists, cites the AC and passes; it cannot prove that the test would catch a wrong
implementation. Before the `Test-Lock` commit, and when the human reads the locked tests, check these points.

| Anti-pattern | Why it is a problem | Instead |
|---|---|---|
| The test checks the mock (`mock.assert_called`) and not the result | It passes with any implementation that calls the mock | Assert on the observable outcome the AC describes |
| Mocks everywhere | The test exercises the mocks, not the code | Mock only the boundaries: network, clock, randomness, external services |
| Method added to production code only for the tests | Production code grows an interface nobody else uses | Test through the public interface; move the helper into the tests |
| Weak assertion (`assert result`, `is not None`, no assertion) | It passes on wrong values | Assert the exact value or error the AC fixes |
| Assertion on internals (private fields, call order, log text) | It breaks on refactoring and misses behaviour | Assert what the user or caller can observe |
| `sleep` to wait for something asynchronous | Slow and flaky | Wait for the condition, with a timeout |
| Test that depends on the order or on shared state | It passes alone and fails in the suite (or the reverse) | Fresh state per test; no global fixtures that tests modify |
| The expected value copied from the output of the code | It enshrines the bug | Derive the expected value from the AC |

**Checklist for the human approval** (levels M and L): every AC of the task has a test that fails for the right
reason; the error cases are there; the assertions fix exact values from the ACs; mocks only at the boundaries; the
Review focus cases of the plan assigned to this task have their test.
