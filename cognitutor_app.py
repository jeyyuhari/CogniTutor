"""
CogniTutor: Integrated Intelligent Tutoring System
Phase 6: Unified Pipeline Integration
Connects:
  - Phase 2: Socratic Dialogue Engine (Understanding Level Scaffolding)
  - Phase 3: Adaptive Multimodal Explanation Module (Confusion & Style Switching)
  - Phase 4: Cognitive Load Detection Engine (real output from the team's CS50
    recursion-lecture notebook run — loaded from cognitive_load_results.csv,
    NOT recomputed on the fly)
  - Phase 5: Cross-Course Concept Dependency Graph (Root-Cause Prerequisite Tracing)

CHANGE LOG vs. the previous draft
-----------------------------------
The previous version called compute_cognitive_load() on every chat message
the student typed — which misapplied the lecture-difficulty formula (words
per minute, sentence length, readability) to a 4-word chat message with a
fake assumed duration. That produced meaningless numbers and didn't reflect
the team's actual Phase 4 work.

This version instead LOADS the real cognitive_load_results.csv your
teammate exported from the notebook (18 real chunks of the actual CS50
recursion lecture, 4 flagged high-load) and uses THAT as the source of
truth for "what parts of the lecture were objectively hard." Each flagged
chunk is matched to a concept in the Phase 5 graph by keyword, so the app
can say "this concept was independently flagged as difficult in the source
lecture" instead of inventing a score from the student's own text.
"""

import streamlit as st
import networkx as nx
import pandas as pd
import difflib
import os
import time
import json
import datetime

# ==============================================================================
# PHASE 5: CROSS-COURSE CONCEPT DEPENDENCY GRAPH MODULE
# (unchanged — matches the team's real notebook graph exactly)
# ==============================================================================
def initialize_concept_graph():
    G = nx.DiGraph()
    course_a = ["PB: Variables", "PB: Functions", "PB: Conditionals", "PB: Call Stack"]
    course_b = ["DS: Recursion Base Case", "DS: Recursive Case", "DS: Full Recursion"]

    G.add_nodes_from(course_a, course="Programming Basics")
    G.add_nodes_from(course_b, course="Data Structures")

    dependencies = [
        ("PB: Variables", "PB: Functions"),
        ("PB: Functions", "PB: Call Stack"),
        ("PB: Conditionals", "DS: Recursion Base Case"),
        ("PB: Functions", "DS: Recursive Case"),
        ("PB: Call Stack", "DS: Full Recursion"),
        ("DS: Recursion Base Case", "DS: Full Recursion"),
        ("DS: Recursive Case", "DS: Full Recursion"),
    ]
    G.add_edges_from(dependencies)
    return G


CONCEPT_GRAPH = initialize_concept_graph()


def trace_root_causes(concept, graph=CONCEPT_GRAPH):
    """Recursively traverses predecessors to isolate cross-course gaps."""
    if concept not in graph:
        return []
    visited = set()

    def _walk(node):
        for pred in graph.predecessors(node):
            if pred not in visited:
                visited.add(pred)
                _walk(pred)

    _walk(concept)
    return [c for c in visited if c.startswith("PB:")]


# ==============================================================================
# PHASE 4: COGNITIVE LOAD DETECTOR MODULE
# FIXED: loads the team's real exported results instead of rescoring chat text
# ==============================================================================
CSV_PATH = "cognitive_load_results.csv"

# Simple keyword map used ONLY to link a real flagged lecture chunk to the
# closest concept node in the Phase 5 graph, so the two modules can talk to
# each other. This is a lightweight heuristic, not a claim of NLP precision —
# documented here for transparency if asked.
CONCEPT_KEYWORDS = {
    "PB: Variables": ["variable"],
    "PB: Functions": ["function"],
    "PB: Conditionals": ["conditional", "if statement", "branch"],
    "PB: Call Stack": ["call stack", "stack"],
    "DS: Recursion Base Case": ["base case"],
    "DS: Recursive Case": ["recursive case"],
    "DS: Full Recursion": ["recursion", "recursive function", "factorial"],
}


@st.cache_data
def load_lecture_analysis(csv_path=CSV_PATH):
    """Loads the REAL Phase 4 output. Returns None if the file isn't present yet."""
    if not os.path.exists(csv_path):
        return None
    return pd.read_csv(csv_path)


def _map_chunk_to_concept(text: str) -> str:
    text_l = text.lower()
    best_concept, best_hits = None, 0
    for concept, keywords in CONCEPT_KEYWORDS.items():
        hits = sum(text_l.count(kw) for kw in keywords)
        if hits > best_hits:
            best_hits, best_concept = hits, concept
    return best_concept or "DS: Full Recursion"


def get_high_load_concepts(df: pd.DataFrame) -> list:
    """
    Returns the REAL flagged high-cognitive-load chunks from the lecture,
    each mapped to its closest Phase 5 concept node.
    [{"start":..., "end":..., "difficulty_score":..., "concept":...}, ...]
    """
    if df is None:
        return []
    flagged = df[df["high_load"] == True]
    results = []
    for _, row in flagged.iterrows():
        results.append({
            "start": row["start"],
            "end": row["end"],
            "difficulty_score": row["difficulty_score"],
            "concept": _map_chunk_to_concept(row["text"]),
        })
    return results


def format_timestamp(seconds: float) -> str:
    m, s = int(seconds // 60), int(seconds % 60)
    return f"{m}:{s:02d}"


# ==============================================================================
# PHASE 3: ADAPTIVE MULTIMODAL EXPLANATION MODULE
# ==============================================================================
EXPLANATION_MODES = [
    "Standard Socratic",
    "Analogy Mode",
    "Simplified Breakdown Mode",
    "Visual Description Mode",
    "Example-First Mode",
]

CONFUSION_TRIGGERS = [
    "don't get it", "dont get it", "confused", "not understanding",
    "lost", "makes no sense", "explain differently", "what do you mean",
]


def _is_rephrase_of_last(user_text: str, last_user_text: str, threshold: float = 0.6) -> bool:
    """Per the Phase 3 theory doc: detect confusion via rephrased repeat questions."""
    if not last_user_text:
        return False
    ratio = difflib.SequenceMatcher(None, user_text.lower(), last_user_text.lower()).ratio()
    return threshold <= ratio < 1.0  # similar but not identical = rephrased


def detect_confusion_and_select_mode(user_text: str, current_mode_idx: int,
                                      understanding_level: int, last_user_text: str = None):
    """Detects struggle signals and rotates to untried explanation formats."""
    keyword_hit = any(trigger in user_text.lower() for trigger in CONFUSION_TRIGGERS)
    rephrase_hit = _is_rephrase_of_last(user_text, last_user_text)
    is_confused = keyword_hit or rephrase_hit or understanding_level <= 1

    if is_confused:
        next_mode_idx = (current_mode_idx + 1) if current_mode_idx < len(EXPLANATION_MODES) - 1 else 1
        return True, next_mode_idx
    return False, current_mode_idx


# ==============================================================================
# PHASE 2: SOCRATIC DIALOGUE ENGINE
# ==============================================================================
def apply_socratic_guardrails(response_text: str, target_answer_keywords: list) -> str:
    """Blocks premature leakage of direct solutions; enforces productive struggle."""
    for keyword in target_answer_keywords:
        if keyword.lower() in response_text.lower():
            return (
                "Hold on—let's not jump to the formula or final answer just yet! "
                "Look at what happens when n reaches 1 in your function call. What should it return?"
            )
    return response_text


def generate_tutor_response(user_text: str, mode: str, understanding_lvl: int,
                             root_causes: list, real_hard_moment: dict = None) -> str:
    """Generates the pedagogical response tailored to the active mode and prerequisite gap."""
    prereq_notice = ""
    if root_causes:
        prereq_notice = (f"\n\n*(Root Cause Detected: We are linking back to your Programming "
                          f"Basics prerequisites: **{', '.join(root_causes)}**)*")

    lecture_notice = ""
    if real_hard_moment:
        ts = format_timestamp(real_hard_moment["start"])
        lecture_notice = (f"\n\n*(For context: this exact part of the source lecture, around "
                           f"{ts}, was independently flagged as high cognitive load — difficulty "
                           f"score {real_hard_moment['difficulty_score']:.2f}. You're not alone in "
                           f"finding this part hard.)*")

    if mode == "Analogy Mode":
        body = (
            "Think of recursion like a stack of Russian nesting dolls. Each doll asks the smaller doll inside "
            "to open itself until you reach the tiniest, solid doll that can't be opened anymore. "
            "What would happen to your program if that tiniest solid doll was missing?"
        )
    elif mode == "Simplified Breakdown Mode":
        body = (
            "Let's break this down into three tiny steps:\n"
            "1. **Check**: Is the input at its stopping point ($n = 1$)?\n"
            "2. **Halt**: Return an immediate constant if yes.\n"
            "3. **Recurse**: Multiply and call itself if no.\n\n"
            "Which of these three steps is failing in your code trace?"
        )
    elif mode == "Visual Description Mode":
        body = (
            "Imagine your computer memory as an actual stack of trays on top of each other. "
            "Each time `factorial(n)` is called, a new tray sits on top of the call stack. "
            "When can the computer start clearing trays off the stack?"
        )
    elif mode == "Example-First Mode":
        body = (
            "Let's trace `factorial(3)` directly:\n"
            "- It computes: $3 \\times \\text{factorial}(2)$\n"
            "- Which needs: $2 \\times \\text{factorial}(1)$\n"
            "Once `factorial(1)` returns 1, what gets passed back upward?"
        )
    else:
        # Standard Socratic
        if understanding_lvl >= 4:
            body = "Good intuition. How would the call stack behavior differ if you had two recursive calls instead of one?"
        else:
            body = "That's an interesting observation. If the recursive step calls itself repeatedly, what condition tells the function when to stop?"

    return body + prereq_notice + lecture_notice


# ==============================================================================
# PHASE 6: ORCHESTRATOR & STREAMLIT UI
# ==============================================================================
st.set_page_config(page_title="CogniTutor - AI Socratic Tutor", layout="wide")
st.title("CogniTutor: Integrated AI Socratic Tutoring System")
st.caption("Phase 6: Multi-Module Orchestration Prototype (Phases 2-5 Unified)")

# ---- State Initialization ----
if "messages" not in st.session_state:
    st.session_state.messages = []
if "understanding_level" not in st.session_state:
    st.session_state.understanding_level = 2
if "mode_idx" not in st.session_state:
    st.session_state.mode_idx = 0
if "target_concept" not in st.session_state:
    st.session_state.target_concept = "DS: Full Recursion"
if "last_user_text" not in st.session_state:
    st.session_state.last_user_text = None

# ---- Phase 7 pilot-testing instrumentation ----
# These counters give Phase 7 real engagement data automatically, instead of
# a facilitator hand-counting messages/timing with a stopwatch.
if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()
if "message_count" not in st.session_state:
    st.session_state.message_count = 0
if "confusion_count" not in st.session_state:
    st.session_state.confusion_count = 0
if "mode_switch_count" not in st.session_state:
    st.session_state.mode_switch_count = 0
if "root_cause_trigger_count" not in st.session_state:
    st.session_state.root_cause_trigger_count = 0
if "student_id" not in st.session_state:
    st.session_state.student_id = ""

# ---- Load real Phase 4 data once ----
lecture_df = load_lecture_analysis()
high_load_concepts = get_high_load_concepts(lecture_df)
high_load_concept_names = {c["concept"] for c in high_load_concepts}

# ==============================================================================
# SIDEBAR
# ==============================================================================
st.sidebar.title("Module Diagnostics Panel")

st.sidebar.subheader("Pilot Session")
st.session_state.student_id = st.sidebar.text_input(
    "Student/participant ID (for Phase 7 logging)",
    value=st.session_state.student_id,
    placeholder="e.g. S1",
)

st.sidebar.subheader("Phase 5: Topic")
st.session_state.target_concept = st.sidebar.selectbox(
    "Current concept being discussed",
    options=list(CONCEPT_GRAPH.nodes()),
    index=list(CONCEPT_GRAPH.nodes()).index(st.session_state.target_concept),
)
st.sidebar.markdown(f"**Active Explanation Mode:** `{EXPLANATION_MODES[st.session_state.mode_idx]}`")
st.sidebar.metric("Understanding Level (0-5)", st.session_state.understanding_level)

st.sidebar.divider()
st.sidebar.subheader("Phase 4: Real Lecture Difficulty Data")
if lecture_df is not None:
    st.sidebar.metric("Chunks analyzed", len(lecture_df))
    st.sidebar.metric("High-load chunks flagged", len(high_load_concepts))
    for c in high_load_concepts:
        ts = format_timestamp(c["start"])
        with st.sidebar.expander(f"⚠️ {ts} (score {c['difficulty_score']:.2f}) → {c['concept']}"):
            st.write(f"Mapped concept: **{c['concept']}**")
    if os.path.exists("cognitive_load.png"):
        st.sidebar.image("cognitive_load.png", caption="Difficulty over time (from Phase 4 notebook)")
else:
    st.sidebar.warning(
        "cognitive_load_results.csv not found in this folder. Copy the real "
        "file exported from the Phase 4 notebook here to enable this panel."
    )

if os.path.exists("cross_course_concept_graph.png"):
    st.sidebar.divider()
    st.sidebar.subheader("Phase 5: Concept Graph")
    st.sidebar.image("cross_course_concept_graph.png", caption="Cross-course dependency graph (from Phase 5 notebook)")

diag_panel = st.sidebar.empty()

# ---- Phase 7: session export ----
st.sidebar.divider()
st.sidebar.subheader("Phase 7: Pilot Test Logging")
session_duration_min = round((time.time() - st.session_state.session_start) / 60, 2)
st.sidebar.caption(
    f"Messages: {st.session_state.message_count} | "
    f"Duration so far: {session_duration_min} min"
)

session_log = {
    "student_id": st.session_state.student_id or "unspecified",
    "session_start_iso": datetime.datetime.fromtimestamp(st.session_state.session_start).isoformat(),
    "session_duration_minutes": session_duration_min,
    "message_count": st.session_state.message_count,
    "confusion_count": st.session_state.confusion_count,
    "mode_switch_count": st.session_state.mode_switch_count,
    "root_cause_trigger_count": st.session_state.root_cause_trigger_count,
    "final_understanding_level": st.session_state.understanding_level,
    "final_topic": st.session_state.target_concept,
    "chat_history": st.session_state.messages,
}

st.sidebar.download_button(
    label="⬇ Download session log (for Phase 7)",
    data=json.dumps(session_log, indent=2),
    file_name=f"session_{st.session_state.student_id or 'unspecified'}.json",
    mime="application/json",
    disabled=(st.session_state.message_count == 0),
)
if st.session_state.message_count == 0:
    st.sidebar.caption("Chat with the tutor first, then download the log at the end of the session.")

# ==============================================================================
# MAIN CHAT
# ==============================================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a doubt regarding recursion or your lecture..."):
    start_time = time.time()
    st.session_state.message_count += 1
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Phase 3: confusion detection (keyword + rephrase-of-last-message)
    confused_flag, new_mode_idx = detect_confusion_and_select_mode(
        prompt, st.session_state.mode_idx, st.session_state.understanding_level,
        st.session_state.last_user_text,
    )

    # 2. Is the CURRENT topic one that was objectively hard in the real lecture? (Phase 4, real data)
    is_real_hard_moment = st.session_state.target_concept in high_load_concept_names
    matching_hard_chunk = next(
        (c for c in high_load_concepts if c["concept"] == st.session_state.target_concept), None
    )

    # 3. Phase 5: trace root causes if the student is confused OR the topic is objectively hard
    root_cause_gaps = []
    if confused_flag or is_real_hard_moment:
        root_cause_gaps = trace_root_causes(st.session_state.target_concept)

    # 4. Update understanding level + mode (+ Phase 7 instrumentation counters)
    if confused_flag:
        st.session_state.confusion_count += 1
        if new_mode_idx != st.session_state.mode_idx:
            st.session_state.mode_switch_count += 1
        st.session_state.mode_idx = new_mode_idx
        st.session_state.understanding_level = max(0, st.session_state.understanding_level - 1)
    elif any(kw in prompt.lower() for kw in ["yes", "return", "base"]):
        st.session_state.understanding_level = min(5, st.session_state.understanding_level + 1)

    if root_cause_gaps:
        st.session_state.root_cause_trigger_count += 1

    active_mode = EXPLANATION_MODES[st.session_state.mode_idx]

    # 5. Phase 2: Socratic response with guardrails
    raw_response = generate_tutor_response(
        prompt, active_mode, st.session_state.understanding_level,
        root_cause_gaps, matching_hard_chunk if is_real_hard_moment else None,
    )
    guarded_response = apply_socratic_guardrails(raw_response, ["n * factorial(n-1)", "return 1"])

    elapsed = round(time.time() - start_time, 3)
    st.session_state.last_user_text = prompt

    with st.chat_message("assistant"):
        st.markdown(guarded_response)
    st.session_state.messages.append({"role": "assistant", "content": guarded_response})

    diag_panel.json({
        "Phase 4 - Real Hard Moment": bool(is_real_hard_moment),
        "Phase 5 - Root Cause Gaps": root_cause_gaps if root_cause_gaps else "None (In Scope)",
        "Phase 3 - Mode": active_mode,
        "Latency": f"{elapsed}s",
    })
