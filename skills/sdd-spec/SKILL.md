---
name: sdd-spec
description: Use this skill when the user wants to go from an idea or a request to an approvable specification (spec.md with requirements, acceptance criteria and non-scope), before any plan or code; also to complete a draft spec or get it approved.
---

# Spec

Playbook §3.3 and §4 (phase 2). Precondition: project initialized (`scripts/spec_lint.py` exists). If it is missing,
point to `sdd-init`.

The process depends on the **level** of the change (playbook §2.1): S skips plan and `review.md`, L adds an ADR and the
human reading of the diff. You propose it with the criteria, the user decides.

## Steps

1. **Look before you ask.** Read `AGENTS.md` and `docs/constitution.md`, the material the user pointed to and the code
   the request touches, until you can explain how the relevant parts work today. In brownfield also read
   `docs/system/map.md` and the `docs/system/<area>.md` page of the area involved; if the area has no characterization
   tests, propose `sdd-characterize` **before** writing the spec. Never ask what the project already answers.
2. **Play the request back.** In a short message, restate in your own words what the user wants, for whom and why, and
   what the change would touch; say plainly if you found a constraint, a conflict or a cheaper path. End with one
   question.
3. **Clarify, one question per message.** Ask the question whose answer would most change what gets built, and say why
   you ask it. Use the user's words, not process jargon. Cover the ground without reading it out as a list: goal and
   success criterion, users, non-scope, **anti-goals** (what would make it a failure even if it works), constraints,
   error cases. Do not answer the questions yourself: a decision that belongs to the user stays open until they answer.
   Stop asking when the remaining doubts would not change the requirements; they go into "Open questions".
4. **Options, when the request admits really different outcomes for the user** (scope, behaviour, experience): present
   2-3 options with their trade-offs in a message of their own and let the user choose. Technical alternatives belong
   to the plan, not here.
5. **Write** `docs/specs/<id>/spec.md` with `references/spec-template.md`. The `<id>` is today's date plus a short
   lower-case slug (`2026-10-24-export-csv`): it is the folder name and appears in the title
   (`# SPEC-2026-10-24-export-csv: Export CSV`), so two people or two branches do not pick the same ID. Rules:
   - every requirement is a verifiable sentence; every REQ has at least one AC in Given/when/then form, with an error
     case where it makes sense;
   - the **non-scope** is mandatory and concrete (what must not be done or touched); in brownfield describe only the
     delta;
   - the **anti-goals** record what the user said would make the feature a failure; `spec_lint.py` warns if they are
     missing;
   - every assumption is marked `[ASSUMPTION]`;
   - `- Level:` S, M or L with the criteria of playbook §2.1: S only if **all** true (at most 3 production files, no
     public interface or data format changed, no sensitive area of `AGENTS.md`, no dependency); L if it touches a
     sensitive area, a public interface or a data migration. When in doubt, the higher one. `diff_scope.py` will report
     a diff that exceeds the level;
   - `Status: draft`; the approval fields stay empty.
6. **Check** with `python scripts/spec_lint.py docs/specs/<id>/spec.md` and fix until there are no errors (warnings
   must be read and reported).
7. **Summarize** to the user: proposed level with the reason, list of REQs, assumptions, non-scope, anti-goals,
   remaining open questions.

## STOP

Ask for explicit approval. Only after a clear confirmation **and** the approver's name:
- fill in `Approved by / date` (name and today's date) and set `Status: approved`;
- close or remove the resolved open questions (the section must contain only "none");
- compute the hash with `python scripts/spec_lint.py <spec> --hash` and write it in `- Hash:`;
- rerun `spec_lint.py`: it must pass.

From now on every change to the spec body voids the approval (the hash no longer matches).

**Changing an already approved spec:** set `Status: in-revision` and add an entry in `## Revisions` with date, what
changes and why; make the changes and ask for approval again as above (new name, date and hash). The plan, which records
the spec hash, lapses by itself and must be re-approved; the tasks, which record the plan hash, must be reviewed if the
plan changes. The real approval is merging the design PR into `main` (playbook §1.2): spec, plan and tasks go together in
that PR, opened by the user or the agent's bot identity, never merged by the agent.

Do not approve on your own initiative and do not infer consent from silence. Do not start plan or code.
Next step: `sdd-plan` (level S: `sdd-tasks`).
