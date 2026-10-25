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
