"""
PHASE 7 — Results Analysis
=============================
Merges TWO data sources:
  1. session_logs/*.json  — engagement data, auto-exported by the app's
     "Download session log" button (message count, session duration,
     confusion triggers, mode switches, root-cause triggers)
  2. results_template.csv — quiz scores + satisfaction survey ratings,
     entered by hand after each pilot session

...and produces the comprehension + engagement summary for your Phase 7
evaluation report, plus a chart.

HOW TO USE
----------
1. After each pilot session, put the downloaded session_<id>.json file
   into session_logs/.
2. Fill in results_template.csv with that student's quiz scores and
   survey ratings (same student_id as the JSON file).
3. Run: python analyze_results.py
4. It prints a summary to the terminal AND saves
   comprehension_improvement.png.

NOTE: this repo includes two sample files (session_S1.json,
session_S2.json) and two matching rows in results_template.csv so you
can see the full pipeline work end-to-end before your real pilot data
exists. Delete/replace them with real data when you run your actual
pilot test.
"""

import json
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "results_template.csv"
LOGS_DIR = "session_logs"


def load_session_logs(logs_dir=LOGS_DIR) -> pd.DataFrame:
    """Reads every session_*.json file and returns one row per student."""
    rows = []
    for path in glob.glob(os.path.join(logs_dir, "*.json")):
        with open(path) as f:
            log = json.load(f)
        rows.append({
            "student_id": log.get("student_id", "unspecified"),
            "messages_sent": log.get("message_count", None),
            "session_minutes": log.get("session_duration_minutes", None),
            "confusion_triggers": log.get("confusion_count", None),
            "mode_switches": log.get("mode_switch_count", None),
            "root_cause_triggers": log.get("root_cause_trigger_count", None),
            "final_understanding_level": log.get("final_understanding_level", None),
        })
    if not rows:
        raise FileNotFoundError(
            f"No session_*.json files found in {logs_dir}/. Download session "
            "logs from the app's sidebar after each pilot session and place "
            "them here first."
        )
    return pd.DataFrame(rows)


def load_quiz_survey(path=CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.dropna(subset=["pre_test_score", "post_test_score"])
    if df.empty:
        raise ValueError(
            f"No complete rows found in {path}. Fill in pre_test_score and "
            "post_test_score for your pilot students before running this."
        )
    return df


def merge_data(logs_df: pd.DataFrame, quiz_df: pd.DataFrame) -> pd.DataFrame:
    merged = quiz_df.merge(logs_df, on="student_id", how="left")
    missing_logs = merged[merged["messages_sent"].isna()]["student_id"].tolist()
    if missing_logs:
        print(f"⚠️  No session log found for: {missing_logs} "
              f"(quiz/survey data still used, engagement fields left blank)\n")
    return merged


def summarize(df: pd.DataFrame):
    df["improvement"] = df["post_test_score"] - df["pre_test_score"]

    print("=== COMPREHENSION ===")
    print(f"Students: {len(df)}")
    print(f"Average pre-test score:  {df['pre_test_score'].mean():.2f} / 5")
    print(f"Average post-test score: {df['post_test_score'].mean():.2f} / 5")
    print(f"Average improvement:     {df['improvement'].mean():+.2f}")
    print(f"Students who improved:   {(df['improvement'] > 0).sum()} / {len(df)}")

    print("\n=== ENGAGEMENT (from app session logs) ===")
    for col, label in [
        ("messages_sent", "Average messages sent"),
        ("session_minutes", "Average session length (min)"),
        ("confusion_triggers", "Average confusion triggers"),
        ("mode_switches", "Average explanation mode switches"),
        ("root_cause_triggers", "Average root-cause (Phase 5) triggers"),
    ]:
        if col in df.columns and df[col].notna().any():
            print(f"{label}: {df[col].mean():.1f}")

    print("\n=== SATISFACTION (1-5 scale) ===")
    survey_cols = [c for c in df.columns if c.startswith("q")]
    for col in survey_cols:
        if df[col].notna().any():
            print(f"{col.replace('_', ' ')}: {df[col].mean():.2f} / 5")

    return df


def plot_improvement(df: pd.DataFrame, out_path="comprehension_improvement.png"):
    plt.figure(figsize=(8, 5))
    x = df["student_id"]
    width = 0.35
    positions = range(len(x))

    plt.bar([p - width / 2 for p in positions], df["pre_test_score"], width, label="Pre-test", color="lightcoral")
    plt.bar([p + width / 2 for p in positions], df["post_test_score"], width, label="Post-test", color="mediumseagreen")

    plt.xticks(list(positions), x)
    plt.ylabel("Quiz score (out of 5)")
    plt.title("Comprehension: Pre-test vs Post-test by Student")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"\nChart saved to {out_path}")


if __name__ == "__main__":
    logs_df = load_session_logs()
    quiz_df = load_quiz_survey()
    merged = merge_data(logs_df, quiz_df)
    merged = summarize(merged)
    plot_improvement(merged)
