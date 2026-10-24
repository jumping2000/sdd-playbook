# Come citare gli AC nei test

Gli AC ripartono da AC-001 in ogni spec, quindi `scripts/trace_check.py` attribuisce ogni citazione a una spec.
L'ID della spec è quello del titolo: data più slug (`SPEC-2026-10-24-export-csv`) o, nei progetti nati prima, un
numero (`SPEC-001`).

1. **File dichiarato** (consigliato con gli ID con data): il file di test nomina una sola spec in testa
   (`# SPEC-2026-10-24-export-csv`) e poi cita gli AC in forma breve: `AC-001`, `AC_001`, `AC001`.
2. **Citazione qualificata**, valida in qualsiasi file: `SPEC-2026-10-24-export-csv/AC-001` in stringhe e commenti;
   nei nomi di funzione `SPEC_2026_10_24_export_csv_AC_001` (lo slug resta in minuscolo, `AC` in maiuscolo).
   Per i vecchi ID numerici anche `SPEC-001-AC-001`, `SPEC_001_AC_001`, `SPEC001_AC001`.
3. **Citazione breve in un file non dichiarato:** vale solo se il progetto ha una sola spec. Con più spec è ambigua,
   non conta e `trace_check.py` la segnala.

Le citazioni su righe con `TODO`, `FIXME` o `XXX` non contano: un promemoria non è un test.

| Linguaggio | Esempio |
|---|---|
| Python (pytest) | `# SPEC-2026-10-24-export-csv` in testa, poi `def test_AC_001_esporta_csv_valido(): ...` |
| JavaScript / TypeScript | `it("SPEC-2026-10-24-export-csv/AC-001: esporta un CSV valido", () => { ... })` |
| Java (JUnit) | `// SPEC-2026-10-24-export-csv` in testa, poi `@Test void AC_001_esportaCsv() { ... }` (l'ID nel nome del metodo: `@DisplayName` non finisce nel report JUnit di Surefire) |
| C# (xUnit) | `// SPEC-2026-10-24-export-csv` in testa, poi `[Fact] public void AC_001_EsportaCsvValido() { ... }` |
| Go | `// SPEC-2026-10-24-export-csv` in testa, poi `func TestAC001_EsportaCsv(t *testing.T) { ... }`; con più spec e `--junit`, forma qualificata (`Test_SPEC_2026_10_24_export_csv_AC_001`): nel report il classname è il package, non il file |
| Gherkin | `# SPEC-2026-10-24-export-csv/AC-001` sopra lo `Scenario:` |

Con `--junit` il caso del report si attribuisce al file il cui percorso coincide di più con `file` o `classname` (`tests.a.test_api` ↔ `tests/a/test_api.py`): file omonimi in cartelle diverse non si confondono.

Un test per più AC è ammesso (cita tutti gli ID). Un AC può avere più test: servono i casi di errore.
