# Come citare gli AC nei test

Gli AC ripartono da AC-001 in ogni spec, quindi `scripts/trace_check.py` attribuisce ogni citazione a una spec:

1. **Citazione qualificata** (preferita): `SPEC-001/AC-001`, oppure `SPEC-001-AC-001`, `SPEC_001_AC_001`,
   `SPEC001_AC001` dove i caratteri `-` e `/` non sono ammessi (nomi di funzione). Vale sempre e solo per quella spec.
2. **File dichiarato:** un file di test che nomina una sola spec (per esempio `# SPEC-001` in testa) le assegna anche
   le citazioni brevi `AC-001`, `AC_001`, `AC001`.
3. **Citazione breve in un file non dichiarato:** vale solo se il progetto ha una sola spec. Con più spec è ambigua,
   non conta e `trace_check.py` la segnala.

Le citazioni su righe con `TODO`, `FIXME` o `XXX` non contano: un promemoria non è un test.

| Linguaggio | Esempio |
|---|---|
| Python (pytest) | `def test_SPEC001_AC001_esporta_csv_valido(): ...` |
| JavaScript / TypeScript | `it("SPEC-001/AC-001: esporta un CSV valido", () => { ... })` |
| Java (JUnit) | `@DisplayName("SPEC-001/AC-001 esporta un CSV valido") @Test void spec001Ac001EsportaCsv() { ... }` |
| C# (xUnit) | `[Fact] public void SPEC001_AC001_EsportaCsvValido() { ... }` |
| Go | `func TestSPEC001_AC001_EsportaCsv(t *testing.T) { ... }` |
| Gherkin | `# SPEC-001/AC-001` sopra lo `Scenario:` |
| Qualsiasi, file dedicato a una spec | `# SPEC-001` in testa al file, poi `test_AC_001_...` |

Un test per più AC è ammesso (cita tutti gli ID). Un AC può avere più test: servono i casi di errore.
