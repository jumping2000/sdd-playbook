# Step di `verify` per stack (da provare, non da fidarsi)

Regola: ogni comando va **eseguito una volta a mano** e funzionare prima di entrare in
`STEPS` di `scripts/verify.py`. Non registrare step che il progetto non ha (es. un type-checker
non configurato). Se il progetto non ha ancora test, dillo: non inventarne uno finto.

Formato di `STEPS`: `("nome", ["comando", "arg", ...], fast?)`. Lista di argomenti, mai stringa.

| Stack | Rilevamento | Step proposti (verifica che esistano) |
|---|---|---|
| Python + uv | `pyproject.toml`, `uv.lock` | `uv run ruff format --check .` (fast), `uv run ruff check .` (fast), `uv run mypy <src>`, `uv run pytest -q` |
| Python senza uv | `pyproject.toml` / `requirements*.txt` | gli stessi con `python -m ruff ...`, `python -m mypy ...`, `python -m pytest -q` (usa `sys.executable` al posto di `python` se serve il venv corrente) |
| Node / TypeScript | `package.json` | solo gli script presenti in `package.json`: `npm run lint` (fast), `npm run typecheck`, `npm test` |
| .NET | `*.sln`, `*.csproj` | `dotnet format --verify-no-changes` (fast), `dotnet build --nologo`, `dotnet test --nologo --no-build` |
| Go | `go.mod` | `go vet ./...` (fast), `go test ./...` (attenzione: `gofmt -l` esce 0 anche con differenze, serve un wrapper) |
| Java (Maven) | `pom.xml` | `mvn -B -q verify` |
| Java (Gradle) | `build.gradle*` | `gradlew check` (su Windows il wrapper è `gradlew.bat`: risolvi con `shutil.which` o un ramo per piattaforma) |
| Altro | — | chiedi all'utente i comandi reali di format, lint, tipi, test |
