# Comprehension Quiz — Recursion (CS50 pilot lecture)

Give this **before** the student uses CogniTutor (pre-test) and again
**after** (post-test). Same questions both times — shuffle the order
for the retake. Each correct answer = 1 point. Max score = 5.

These questions map directly to the concept graph nodes in the app
(`PB: Variables`, `PB: Functions`, `PB: Call Stack`,
`DS: Recursion Base Case`, `DS: Recursive Case`, `DS: Full Recursion`),
so a quiz-score improvement can be reasonably attributed to the tutor
session rather than an unrelated topic.

---

**Q1.** What is a "base case" in a recursive function?
- A) The first line of any function
- B) The condition that stops the recursion from repeating forever ✅
- C) A function that calls itself
- D) A loop that runs exactly once

**Q2.** Why does a recursive function need a call stack?
- A) To store variables permanently
- B) To keep track of each function call waiting to finish ✅
- C) To speed up the function
- D) It doesn't — call stacks are only for loops

**Q3.** In `factorial(n)`, what does the recursive case actually do?
- A) Returns 1 immediately
- B) Calls `factorial` again with a smaller value of `n` and multiplies the result ✅
- C) Loops through all numbers from 1 to n
- D) Declares a new variable each time

**Q4.** True or False: understanding functions and variables (Programming
Basics) is generally a prerequisite for understanding recursion (Data
Structures).
- True ✅ / False

**Q5.** In your own words, briefly explain what "recursive case" means
in a recursive function. (short answer — 1 point for a reasonable
explanation, 0 for blank/incorrect)

*Sample acceptable answer: "The part of the function where it calls
itself again, usually with a smaller/simpler version of the problem,
getting closer to the base case."*

---

## Scoring sheet (for the facilitator)

| Student ID | Pre-test score (/5) | Post-test score (/5) | Improvement |
|---|---|---|---|
| S1 | | | |
| S2 | | | |
| ... | | | |

Enter these into `results_template.csv`.
