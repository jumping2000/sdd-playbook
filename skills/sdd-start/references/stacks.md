# `verify` steps per stack (to try, not to trust)

Rule: every command must be **run once by hand** and work before entering `STEPS` in `scripts/verify.py`. Do not
register steps the project does not have (e.g. a type checker that is not configured). If the project has no tests yet,
say so: do not invent a fake one.

`STEPS` format: `("name", ["command", "arg", ...], fast?)`. A list of arguments, never a string.

The test step also writes a **JUnit XML report** (`reports/junit.xml`, to be ignored by git): `trace_check.py --junit`
uses it to check that every AC has an executed and passing test, not just a cited one (mandatory at level L).

| Stack | JUnit report |
|---|---|
| Python (pytest) | `--junitxml=reports/junit.xml` |
| Node (Jest / Vitest) | `jest-junit` as reporter / `--reporter=junit --outputFile=reports/junit.xml` |
| .NET | `dotnet test --logger "junit;LogFilePath=reports/junit.xml"` (package `JunitXml.TestLogger`) |
| Go | `gotestsum --junitfile reports/junit.xml` |
| Java (Maven / Gradle) | already produced in `target/surefire-reports/` / `build/test-results/test/`: pass the folder |

| Stack | Detection | Proposed steps (check that they exist) |
|---|---|---|
| Python + uv | `pyproject.toml`, `uv.lock` | `uv run ruff format --check .` (fast), `uv run ruff check .` (fast), `uv run mypy <src>`, `uv run pytest -q` |
| Python without uv | `pyproject.toml` / `requirements*.txt` | the same with `python -m ruff ...`, `python -m mypy ...`, `python -m pytest -q` (use `sys.executable` instead of `python` if the current venv is needed) |
| Node / TypeScript | `package.json` | only the scripts present in `package.json`: `npm run lint` (fast), `npm run typecheck`, `npm test` |
| .NET | `*.sln`, `*.csproj` | `dotnet format --verify-no-changes` (fast), `dotnet build --nologo`, `dotnet test --nologo --no-build` |
| Go | `go.mod` | `go vet ./...` (fast), `go test ./...` (note: `gofmt -l` exits 0 even with differences, a wrapper is needed) |
| Java (Maven) | `pom.xml` | `mvn -B -q verify` |
| Java (Gradle) | `build.gradle*` | `gradlew check` (on Windows the wrapper is `gradlew.bat`: resolve it with `shutil.which` or a per-platform branch) |
| Other | — | ask the user for the real format, lint, type and test commands |

Dependency audit (needs the network, so in CI rather than in `--fast`): `pip-audit`, `npm audit --audit-level=high`,
`govulncheck ./...`, `dotnet list package --vulnerable` (always exits 0: wrap it), OWASP dependency-check for Java.
