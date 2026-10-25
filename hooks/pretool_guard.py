#!/usr/bin/env python3
"""PreToolUse hook (Claude Code), opt-in: blocks high-risk commands and reads.

Active only with SDD_GUARD=1. Reads the event JSON (tool_name, tool_input) from stdin. Exits 2 with a message on stderr
to block the call, 0 otherwise; with unreadable JSON it blocks (fail-closed). It is a minimal safety net, not a sandbox:
it does not replace the agent's native permissions, allowlists and environment isolation (playbook §1.2), and a
sufficiently convoluted command always bypasses it.
Blocked in Bash and PowerShell: forced or destructive pushes (--force, -f, --force-with-lease, +refspec, --delete,
--mirror), reset --hard, clean -f (also with git global options such as -C), recursive deletes (rm -r in any form,
git rm -r without --cached, find -delete, Remove-Item -Recurse, rd /s, del /s, shutil.rmtree), download-and-execute,
any reference to a .env file even inside a word (cat .env>x, open('.env')), except .env.example, .sample, .template and
commands on .gitignore (appending, git check-ignore). Read and Grep tools: .env files, also in upper case or with an
NTFS stream (.env::$DATA). Standard library only, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

RULES = [
    (r"\bRemove-Item\b.*\s-r(e(c(u(r(s(e)?)?)?)?)?)?\b", "recursive delete (Remove-Item -Recurse)"),
    (r"\b(rd|rmdir)\s+/s\b|\bdel\s+/[sfq]\b", "recursive delete (cmd)"),
    (r"\bshutil\s*\.\s*rmtree\b", "recursive delete (shutil.rmtree)"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b", "download and execute"),
    (r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|;&]*\|\s*(iex|Invoke-Expression)\b", "download and execute"),
]
# .env with an optional suffix (not example/sample/template) and an optional NTFS stream (.env::$DATA, .env:x)
ENV_FILE = re.compile(r"(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w-]+)*(::?\$?\w*)?$", re.I)
SEPARATORS = re.compile(r"&&|\|\||[;|&\n]")
INSIDE_WORD = re.compile(r"[<>=()'\",]")  # .env attached to redirections, calls, assignments
ON_IGNORE = re.compile(r"\.(git|docker)ignore\b|\bcheck-ignore\b", re.I)
PREFIXES = {"sudo", "xargs", "command", "exec", "nohup", "env", "time", "doas"}
GIT_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def git_subcommand(words: list[str], names: list[str]) -> tuple[str, list[str]] | None:
    """(subcommand, arguments) of git, skipping global options (-C dir, -c key=value)."""
    if "git" not in names:
        return None
    i = names.index("git") + 1
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in GIT_WITH_VALUE else 1
    return (words[i], words[i + 1:]) if i < len(words) else None


def short_flag(arguments: list[str], letter: str) -> bool:
    return any(re.fullmatch(r"-[A-Za-z]+", x) and letter in x for x in arguments)


def split_words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def segment_reason(segment: str) -> str | None:
    words = split_words(segment)
    if not words:
        return None
    names = [os.path.basename(x).lower() for x in words]
    for i, n in enumerate(names):
        if n == "rm" and (i == 0 or names[i - 1] in PREFIXES):
            options = [x for x in words[i + 1:] if x.startswith("-")]
            if "--recursive" in options or short_flag(options, "r") or short_flag(options, "R"):
                return "recursive delete (rm -r)"
    if "find" in names and ("-delete" in words or ("-exec" in words and "rm" in names)):
        return "recursive delete (find -delete)"
    git = git_subcommand(words, names)
    if git:
        sub, args = git
        if sub == "reset" and "--hard" in args:
            return "git reset --hard"
        if sub == "clean" and ("--force" in args or short_flag(args, "f")):
            return "git clean -f"
        if sub == "rm" and "--cached" not in args and ("--recursive" in args or short_flag(args, "r")):
            return "recursive delete (git rm -r)"
        if sub == "push" and (any(x in ("--force", "--mirror", "--delete") or x.startswith(("--force", "+", ":"))
                                  for x in args) or short_flag(args, "f") or short_flag(args, "d")):
            return "forced or destructive push"
    if ON_IGNORE.search(segment):
        return None
    raw = segment.split()  # shlex strips the backslashes of Windows paths
    pieces = [x for word in words + raw for x in INSIDE_WORD.split(word)]
    if any(ENV_FILE.search(x) for x in pieces):
        return "reference to a .env file"
    return None


def reason(event: dict) -> str | None:
    tool = event.get("tool_name", "")
    inp = event.get("tool_input") or {}
    if not isinstance(inp, dict):
        return "malformed event (tool_input is not an object)"
    if tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", ""))
        for pattern, name in RULES:
            if re.search(pattern, cmd, re.I):
                return name
        for segment in SEPARATORS.split(cmd):
            if (r := segment_reason(segment)):
                return r
    if tool == "Read" and ENV_FILE.search(str(inp.get("file_path", ""))):
        return "reading a .env file"
    if tool == "Grep" and any(ENV_FILE.search(str(inp.get(k, ""))) or re.search(r"\.env\*?$", str(inp.get(k, "")), re.I)
                              for k in ("path", "glob")):
        return "searching a .env file"
    return None


def main() -> int:
    if os.environ.get("SDD_GUARD") != "1":
        return 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.stderr.write("Blocked by the SDD Playbook guard: unreadable event (fail-closed).\n")
        return 2
    r = reason(event if isinstance(event, dict) else {})
    if r:
        sys.stderr.write(f"Blocked by the SDD Playbook guard: {r}. Ask the user for confirmation.\n")
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
