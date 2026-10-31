---
name: sdd-spec
description: Use this skill when the user wants to go from an idea or a request to an approvable specification (spec.md with requirements, acceptance criteria and non-scope), before any plan or code; also to complete a draft spec or get it approved.
---

# Spec

Playbook §3.3 and §4 (phase 2). Precondition: project initialized (`scripts/spec_lint.py` exists). If it is missing,
point to `sdd-init`.

The process depends on the **level** of the change (playbook §2.1): S skips plan and `review.md`, L adds an ADR and the
human reading of the diff. You propose it with the criteria, the user decides. Choices and the approval are asked as
options to select (guide: search for `**/sdd-init/references/interaction.md`).

## Steps

1. **Look before you ask.** Read `AGENTS.md` and `docs/constitution.md`, the material the user pointed to and the code
   the request touches, until you can explain how the relevant parts work today. In brownfield also read
   `docs/system/map.md` and the `docs/system/<area>.md` page of the area involved; if the area has no characterization
   tests, propose `sdd-characterize` **before** writing the spec. Never ask what the project already answers.
2. **Play the request back.** In a short message, restate in your own words what the user wants, for whom and why, and
   what the change would touch; say plainly if you found a constraint, a conflict or a cheaper path.
3. **Clarify in rounds of options.** One round of up to 4 questions, each with 2-4 options (the recommended one first,
   with its reason) and a free answer; a follow-up round only for what the answers opened. A simple change usually
   needs one or two rounds. Ask first what would most change what gets built; use the user's words, not process jargon.
   Cover goal and success criterion, users, non-scope, **anti-goals** (what would make it a failure even if it works),
   constraints, error cases. Do not answer the questions yourself: a decision that belongs to the user stays open until
   they answer.
   Stop asking when the remaining doubts would not change the requirements; they go into "Open questions", each marked
   `blocking: yes` (the answer would change a REQ or an AC the plan relies on) or `blocking: no`, with `about:` and the
   REQ or AC it concerns. Only non-blocking questions may stay open in an approved spec; the tasks covering the ACs they
   name wait for the answer, which goes into the spec with a revision (`Status: in-revision`).
4. **Different outcomes for the user** (scope, behaviour, experience): put them in the round as options with their
   trade-offs. Technical alternatives belong to the plan, not here.
5. **Write** `docs/specs/<id>/spec.md` with `references/spec-template.md`. The `<id>` is today's date plus a short
   lower-case slug (`2026-10-24-export-csv`): it is the folder name and appears in the title
   (`# SPEC-2026-10-24-export-csv: Export CSV`), so two people or two branches do not pick the same ID. Rules:
   - every requirement is a verifiable sentence; every REQ has at least one AC in Given/when/then form, with an error
     case where it makes sense. Proportion: an AC earns its place if it would catch a real defect; a level-S change
     usually needs 3-6 (`spec_lint.py` warns above 6 at S and above 15 at M);
   - the **non-scope** is mandatory and concrete (what must not be done or touched); in brownfield describe only the
     delta;
   - the **anti-goals** record what the user said would make the feature a failure; `spec_lint.py` warns if they are
     missing;
   - every assumption is marked `[ASSUMPTION]`;
   - verifiable words: `spec_lint.py` warns on vague words in REQs and ACs ("fast", "appropriate", "should", "etc") and,
     if `docs/glossary.md` exists, on the synonyms it lists to avoid. Use the glossary's terms; propose new terms to
     the user rather than inventing synonyms;
   - `- Level:` S, M or L (playbook §2.1), **chosen by the user** in the round of questions: propose the lowest level
     the hard criteria allow and show S, M and L as options, the recommended first, each with the criterion that rules
     out the level below. Hard criteria (checked by `diff_scope.py`): a sensitive area of `AGENTS.md` requires L; a new
     or changed dependency requires at least M. Judgement criteria for the user: S fits a small change (about 3
     production files, the process tooling does not count) with no public interface or data format changed; L fits a
     public interface changed incompatibly or a data migration. Do not raise the level "to be safe": when in doubt, ask
     with options;
   - `Status: draft`; the approval fields stay empty.
6. **Check** with `python scripts/spec_lint.py docs/specs/<id>/spec.md` and fix until there are no errors (warnings
   must be read and reported).
7. **Summarize** to the user in a few lines: level with the reason, list of REQs, assumptions, non-scope, anti-goals,
   remaining open questions.

## STOP

Close or remove the resolved open questions (only `blocking: no` questions may stay, otherwise "- none"), then ask for
the approval as a gate with options (`Approve as <name>` for each name of `- Approvers:` in `AGENTS.md`, `Approve as
another person`, `Request changes`, `Stop here`). Only after the user selects an approval, record it with
`python scripts/approve.py spec docs/specs/<id>/spec.md --by "<selected name>" --commit`: it sets `Status: approved`,
name, date and hash, checks the result with `spec_lint.py` and commits the spec alone. If it refuses, fix what it lists
and ask again.

From now on every change to the spec body voids the approval (the hash no longer matches).

**Changing an already approved spec:** set `Status: in-revision` and add an entry in `## Revisions` with date, what
changes and why; make the changes and ask for approval again as above. The plan, which records the spec hash, lapses by
itself and must be re-approved; the tasks, which record the plan hash, must be reviewed if the plan changes.

**Moving `main`** (profile in `AGENTS.md`, guide above): at level S the design gate is the spec approval (plus a quick
check of the tasks); at M and L it closes with the plan and task approval. **solo:** after the design gate move `main`
forward yourself with `git fetch . HEAD:main`. **team:** the real approval is merging the design PR into protected
`main` (playbook §1.2): offer the options `Open the PR`, `Merge now, I approve as <name>` (only if your identity may
merge), `I will merge it myself`.

Do not approve on your own initiative and do not infer consent from silence. Do not start plan or code.
Next step: `sdd-plan` (level S: `sdd-tasks`).
