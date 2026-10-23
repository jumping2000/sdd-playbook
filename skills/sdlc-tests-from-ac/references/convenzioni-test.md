# Come citare gli AC nei test

`scripts/trace_check.py` considera citato un AC se nel nome, in un commento o in una stringa del test compare
`AC-001`, `AC_001` o `AC001`. Cita sempre l'ID dell'AC, non solo il requisito.

| Linguaggio | Esempio |
|---|---|
| Python (pytest) | `def test_AC_001_esporta_csv_valido(): ...` |
| JavaScript / TypeScript | `it("AC-001: esporta un CSV valido", () => { ... })` |
| Java (JUnit) | `@DisplayName("AC-001 esporta un CSV valido") @Test void ac001_esportaCsv() { ... }` |
| C# (xUnit) | `[Fact] public void AC_001_EsportaCsvValido() { ... }` |
| Go | `func TestAC001_EsportaCsv(t *testing.T) { ... }` |
| Gherkin | `# AC-001` sopra lo `Scenario:` |

Un test per più AC è ammesso (cita tutti gli ID). Un AC può avere più test: servono i casi di errore.
