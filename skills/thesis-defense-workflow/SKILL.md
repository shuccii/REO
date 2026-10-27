---
name: thesis-defense-workflow
description: Prepare a graduate student for a master's thesis defense (thesis writing, final presentation and oral examination) in science or engineering, with NAIST-specific milestones and criteria when applicable - confirmed facts, backward schedule, logical writing checks, reverse-designed slides, question bank with answer patterns, timed rehearsals and day-of checklist.
---

# Thesis Defense Workflow

For institutions other than NAIST, use [institution template](references/institution-template.md) and record every rule as confirmed (with source) or unconfirmed.

## 概要(日本語)

修士論文の執筆、最終発表、口頭試問の準備を、発表日から逆算して進めるスキルです。

- NAIST の公開情報(審査基準の6項目、日程)を含みます。未確認の事項は「未確認」と書き、指導教員に確認する項目にします。
- 執筆・スライド・想定質問・研究レビューの4つの流れから、必要なものだけを使います。
- 提出や教員への連絡は行わず、合否の予測もしません。

Use when a student prepares a master's thesis, its final presentation, the oral examination, or a rehearsal for them. Default target: a science/engineering master's program. For NAIST read [NAIST milestones and criteria](references/naist.md). For doctoral defenses, apply the same tracks and add the doctoral items noted there.

This workflow prepares drafts and practice. It never submits, uploads, registers or contacts faculty, never writes the thesis in place of the student unless AI drafting mode is enabled under its preconditions, and never predicts a pass. Use [research-review-workflow](../research-review-workflow/SKILL.md) for the substantive audit of claims and for interactive rehearsal. Use [lab-policy-workflow](../lab-policy-workflow/SKILL.md) and the user's local policy files for laboratory rules; never copy private rules into shared artifacts.

## Structure

One preparation run has a fact sheet, a schedule, an issue log and four tracks. Load only the reference for the track in hand. Read the thesis once into a skeleton (Track R, Tier 0) and reuse it instead of re-reading the full text in every track.

| Part | Output | Reference |
|---|---|---|
| Facts | Fact sheet: each rule with source and date, or `unconfirmed` | [naist.md](references/naist.md) for NAIST |
| Schedule | Backward plan with gates | this file, §2 |
| Issue log | One list for all tracks: ID, source, location, severity, fix, done condition, status | this file, §3 |
| Track W: writing | Thesis outline and draft checks; optional AI drafting | [writing.md](references/writing.md), [ai-drafting.md](references/ai-drafting.md) |
| Track S: slides | Slide plan, slides, script, backup slides | [slides.md](references/slides.md) |
| Track Q: questions | Question bank, answer outlines, rehearsal records | [questions.md](references/questions.md) |
| Track R: review | Tiered checks, claim audit and mock examination | [review-checks.md](references/review-checks.md), research-review-workflow |

## 1. Fix the facts first

Collect with source and date: defense date and slot, talk and Q&A length, format and language, committee members and their public research areas, submission deadlines (application, abstract, thesis, slides), templates, the current institutional criteria, and any rubric the student can see. Read the current official page or handbook. Anything not found is `unconfirmed` and becomes a question for the advisor or office. Never fill a rule from memory, from another program or from an unsourced web article; secondary guides can suggest what to check, not what the rule is.

## 2. Backward schedule

Anchor on the confirmed dates; for NAIST use the official cycle in naist.md (interim milestone by November of year 2, application and abstract in December–January, defense in mid to late February). Typical gates, adjusted to the student's state:

| From the defense | Deliverable | Gate |
|---|---|---|
| before the interim milestone | One-sentence claim; objective → result → conclusion map; gap list | Advisor agrees on scope; later new directions only at the advisor's request |
| about 10–8 weeks | Thesis outline (headings first) and figure list; each figure traceable to data and conditions | Outline reviewed with the advisor before full drafting |
| about 8–6 weeks | Full draft by the student | Advisor review requested; self-check with writing.md first |
| application deadline | Abstract | Advisor review before submission by the student |
| about 4 weeks | Slide plan and slides v1; question bank v1 | — |
| about 3 weeks | Rehearsal 1 (timed, recorded) | Every issue has an owner and done condition |
| about 2 weeks | Slides v2, script, backup slides; rehearsal 2 with listeners outside the subtopic | Within time; major issues closed |
| about 1 week | Final thesis and slides; question drill on weak answers | Advisor approval recorded by the user |
| day before | Day-of checklist; one full timed run | Only error fixes |

## 3. Issue log and gates

Every finding from the advisor, rehearsals, self-checks and AI review goes into the issue log. Severity: critical (breaks the central claim or ethics), major (a criterion or a key question cannot be met), minor (presentation polish). Do not mark an issue done without inspecting the changed page or slide. Advisor approvals, required lab rehearsals and submissions are gates only the user can confirm.

## 4. Tracks

- **W, writing:** by default the student writes and the agent checks structure, logic and wording with writing.md. AI drafting mode ([ai-drafting.md](references/ai-drafting.md)) lets the agent draft from the student's own material only after the advisor agreed on the scope of AI use and the rules were checked; every paragraph then goes through trace → student rewrite → tiered review → explain test, and AI use is logged for disclosure.
- **S, slides:** design backward from purpose and conclusion (slides.md). Every slide maps to a thesis section and an institutional criterion.
- **Q, questions:** generate questions from the actual thesis, slides, known weak points and the committee's public research areas (questions.md); rehearse one question at a time with research-review-workflow in `defense` mode. Never invent results to strengthen an answer.
- **R, review:** review in tiers (review-checks.md). Tier 0: extract the thesis skeleton once with `scripts/thesis_skeleton.py` and reuse it across tracks. Tier 1: cheap checks on the skeleton. Tier 2: open the full text only where a check fails or the central claim depends on it, and send specific central claims to research-review-workflow. Do this once before slides v1 and once before the final version; carry findings into the issue log. The saving comes from scoping the deep read, never from skipping a check.

## 5. Rehearsals, day-of and after

Rehearsal record: date, listeners, measured time per section, questions asked, answers that failed and why, issues opened and closed. Day-of: file formats and a backup copy, display test at the venue if possible, timer, notes for the weakest answers. After the defense: log the committee's comments, plan required revisions with deadlines, archive data, code and figures as required.

## Verification and boundaries

Before declaring a phase complete, open the actual artifacts and check each deliverable against its done condition. Report: confirmed facts with sources, unconfirmed rules, open issues by severity, measured rehearsal times, and what still needs the advisor. AI feedback is practice, not faculty assessment or a degree decision.
