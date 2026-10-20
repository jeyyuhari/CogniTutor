# CogniTutor — Phase 7: Testing & Evaluation Plan

**Milestone (Week 8, part 1 / Sep 22–26):** Pilot testing with a sample
student group; comprehension/engagement evaluation summary.

This plan is written against the actual working prototype
(`cognitutor_app.py`), pilot topic (CS50 recursion/factorial lecture),
and concept graph (Programming Basics → Data Structures) already built
in Phase 6 — not a generic template.

## 1. Participants

- **8–15 students** with some exposure to programming but who haven't
  fully mastered recursion. This range is standard for a small
  pilot/prototype evaluation.

## 2. What we're measuring, and how each one is collected

| Metric | How it's measured | Where it comes from |
|---|---|---|
| **Comprehension** | Score change, pre vs. post | `pre_post_quiz.md` — a 5-question quiz on the exact concepts in the graph (Variables, Functions, Call Stack, Base Case, Recursive Case, Full Recursion) |
| **Engagement** | Messages sent, session length, how often confusion/root-cause was triggered | **Automatic** — the app now has a "Download session log" button in the sidebar that exports this as JSON, no manual counting needed |
| **Perceived usefulness** | Self-reported | `satisfaction_survey.md` |
| **Qualitative feedback** | Open-ended notes | Same survey, Part B |

## 3. Procedure

1. **Before the session:** student takes the pre-test quiz (5–10 min).
2. **During the session (15–20 min):** student enters their ID in the
   app sidebar ("Student/participant ID"), then uses CogniTutor to work
   through recursion. Facilitator observes but doesn't help — just
   notes anything unusual.
3. **End of session:** student clicks **"Download session log"** in the
   sidebar. This saves a JSON file with their message count, session
   duration, how many times confusion was detected, how many times the
   explanation mode switched, and how many times Phase 5's root-cause
   tracing fired — all captured automatically by the app itself.
4. **After the session:** student retakes the quiz (post-test,
   questions reordered) and fills out the satisfaction survey.
5. **Collect:** put all downloaded session JSON files into
   `session_logs/`, and enter quiz scores + survey ratings into
   `results_template.csv`.

## 4. Analysis

Run `analyze_results.py` — it automatically:
- Reads every JSON file in `session_logs/` for engagement metrics
- Reads `results_template.csv` for quiz scores + survey ratings
- Merges them by `student_id`
- Prints a summary and saves a comprehension chart

## 5. What "success" looks like for this milestone

This is a prototype pilot, not a peer-reviewed study — you need:
- A quiz score comparison (pre vs. post)
- Real engagement numbers (not estimated — pulled straight from the
  app's own logs)
- A short (1-page) written summary covering: what worked, what
  confused students about the *tool itself*, any bugs observed, and
  2–3 direct quotes from the qualitative feedback

## 6. Files in this folder

- `pre_post_quiz.md` — comprehension quiz, aligned to the real concept graph
- `satisfaction_survey.md` — engagement/satisfaction survey
- `session_logs/` — put downloaded session JSON files here (2 sample
  files included so you can test the analysis script right now)
- `results_template.csv` — fill in with quiz scores + survey ratings
- `analyze_results.py` — run this after collecting data
