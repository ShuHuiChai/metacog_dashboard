"""
Shared utilities for the Metacognition Dashboard app.

Holds:
- Constants (levels, phases, colors)
- Sample data generation / loading (swap out `load_data()` for your real data source)
- The LLM call that turns a metacognition tag into a suggested next step
"""

import os
import json
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file if present

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHASES = ["Planning", "Monitoring", "Reflection"]

# Maps the three underlying metacognition tag columns to display phase names.
# "Evaluation" in the raw data is shown as "Reflection" in the UI, matching
# the mock-ups.
PHASE_TO_COLUMN = {
    "Planning": "planning_level",
    "Monitoring": "monitoring_level",
    "Reflection": "reflection_level",
}

LEVELS = ["Not Observed", "Emerging", "Proficient", "Accomplished"]

LEVEL_COLORS = {
    "Not Observed": "#9E9E9E",
    "Emerging": "#A9C6E8",
    "Proficient": "#5B8FD6",
    "Accomplished": "#1F4FA3",
}

LEVEL_DESCRIPTIONS_TEACHERS = {
    "Not Observed": "No evidence available",
    "Emerging": "Students are not yet thinking about how they learn",
    "Proficient": "Students are starting to notice their own thinking",
    "Accomplished": "Students are deliberately using strategies to guide their learning",
}
LEVEL_DESCRIPTIONS_STUDENTS = {
    "Not Observed": "No evidence available",
    "Emerging": "You are not yet thinking about how you learn",
    "Proficient": "You are starting to notice your own thinking",
    "Accomplished": "You are deliberately using strategies to guide your learning",
}

BEHAVIOURAL_INDICATORS_TEACHERS = {
    "Planning": "Students plan and organise their thinking strategies before a task",
    "Monitoring": (
        "Students check and persist to clarify their understanding when they "
        "are unclear during a task. "
        "Students notice and evaluate their thinking "
        "strategies to monitor their learning"
    ),
    "Reflection": (
        "Students suspend judgement, reassess conclusions, consider "
        "alternatives and draw on relevant cognitive strategies to refine "
        "their thoughts, attitudes, behaviour and actions"
    ),
}

BEHAVIOURAL_INDICATORS_STUDENTS = {
    "Planning": "You plan and organise your thinking strategies before a task",
    "Monitoring": (
        "You check and persist to clarify your understanding when you "
        "are unclear during a task. "
        "You notice and evaluate your thinking "
        "strategies to monitor your learning"
    ),
    "Reflection": (
        "You suspend judgement, reassess conclusions, consider "
        "alternatives and draw on relevant cognitive strategies to refine "
        "your thoughts, attitudes, behaviour and actions"
    ),
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "dashboard_set_evidence.csv")

CUSTOM_CSS = """
<style>
.st-key-current_level_container {
    background-color: #EAEFFB;     /* Custom background color */
    border: 2px solid #335BA3;     /* Border thickness, style, and color */
    border-radius: 15px;           /* Rounded corners */
    padding: 20px;                 /* Padding inside the container */
}
</style>
"""

PLOTLY_CONFIG = {"displayModeBar": False}

# ---------------------------------------------------------------------------
# Data loading / sample generation
# ---------------------------------------------------------------------------

@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Load the underlying metacognition dataset.

    Expected columns (this is the contract your real data source should
    match):
        assignment_id, assignment_name, subject, class_id, class_name,
        teacher_id, teacher_name, student_id, student_name, due_date,
        planning_level, monitoring_level, evaluation_level, evidence

    If data/sample_data.csv doesn't exist yet, a synthetic dataset is
    generated so the app runs out of the box. Replace this function with a
    real query (DB / API / CSV export) when you plug in production data.
    """
    if os.path.exists(DATA_PATH):
        return pd.read_csv(DATA_PATH)
    df = _generate_sample_data()
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    return df


def _generate_sample_data(seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np.random.seed(seed)

    teachers = [
        ("T1", "Ms. Tan"),
        ("T2", "Mr. Rahman"),
        ("T3", "Mrs. Lim"),
    ]
    subjects_by_teacher = {
        "T1": ["Secondary 3 Chemistry", "Secondary 3 Physics"],
        "T2": ["Secondary 3 Physics", "Secondary 4 Physics"],
        "T3": ["Secondary 3 Chemistry", "Secondary 4 Chemistry"],
    }
    classes = [
        ("C3A", "Class 3A"),
        ("C3B", "Class 3B"),
        ("C4A", "Class 4A"),
    ]

    students = [(f"S{i:02d}", f"Student {chr(64 + i)}") for i in range(1, 11)]

    rows = []
    assignment_counter = 1
    today = date(2026, 8, 1)

    for teacher_id, teacher_name in teachers:
        for subject in subjects_by_teacher[teacher_id]:
            for class_id, class_name in classes:
                for a_idx in range(1, 5):  # 4 assignments
                    assignment_id = f"A{assignment_counter:03d}"
                    assignment_counter += 1
                    assignment_name = f"Assignment {a_idx}"
                    due = today + timedelta(days=14 * (a_idx - 1))

                    # Levels tend to improve slightly over later assignments.
                    level_weights_by_phase = {
                        "planning_level": _weights_for_assignment(a_idx),
                        "monitoring_level": _weights_for_assignment(a_idx),
                        "evaluation_level": _weights_for_assignment(a_idx),
                    }

                    for student_id, student_name in students:
                        row = {
                            "assignment_id": assignment_id,
                            "assignment_name": assignment_name,
                            "subject": subject,
                            "class_id": class_id,
                            "class_name": class_name,
                            "teacher_id": teacher_id,
                            "teacher_name": teacher_name,
                            "student_id": student_id,
                            "student_name": student_name,
                            "due_date": due.isoformat(),
                        }
                        for col, weights in level_weights_by_phase.items():
                            row[col] = rng.choices(LEVELS, weights=weights, k=1)[0]
                        row["evidence"] = (
                            f"{row['student_name']} showed "
                            f"{row['planning_level'].lower()} planning behaviour "
                            f"on {assignment_name.lower()}."
                        )
                        rows.append(row)

    return pd.DataFrame(rows)


def _weights_for_assignment(a_idx: int):
    """Later assignments skew slightly towards higher levels."""
    base = np.array([4, 3, 2, 1], dtype=float)
    shift = (a_idx - 1) * 0.6
    weights = np.clip(base - shift * np.array([1, 0.3, -0.3, -1]), 0.2, None)
    return weights.tolist()


# ---------------------------------------------------------------------------
# LLM-powered suggested actions
# ---------------------------------------------------------------------------

# def _get_anthropic_client():
#     try:
#         from anthropic import Anthropic
#     except ImportError:
#         return None

#     api_key = os.environ.get("ANTHROPIC_API_KEY")
#     if not api_key and hasattr(st, "secrets"):
#         api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
#     if not api_key:
#         return None
#     return Anthropic(api_key=api_key)
def _get_openai_client():
    api_key = os.environ.get("OPENAI")
    return OpenAI(api_key=api_key) if api_key else None


@st.cache_data(show_spinner=False)
def get_suggested_action(
    phase: str,
    level: str,
    subject: str = "",
    audience: str = "teacher",
) -> str:
    """
    Ask the agent for a short, actionable suggestion tied to a metacognition
    phase + level combination, in the style of the call-out boxes in the
    mock-ups.

    audience: "teacher" -> written to the teacher, about "these students"
              "student"  -> written directly to the student, second person
    """
    client = _get_openai_client()
    print(f"Client: {client}")
    if client is None:
        return _fallback_suggestion(phase, level, audience)

    if audience == "teacher":
        prompt = (
            f"You are an assistant embedded in a teacher-facing classroom "
            f"analytics dashboard. A group of students in a {subject} class "
            f"were tagged at the '{level}' level for the metacognition phase "
            f"'{phase}'.\n\n"
            f"Behavioural indicator for this phase: "
            f"{BEHAVIOURAL_INDICATORS_TEACHERS.get(phase, '')}\n\n"
            "Write a short (2-3 sentence) suggested action for the teacher, "
            "in the same style as: 'These students are not yet thinking "
            "about how they learn. Support them by helping them make their "
            "strategy choices more deliberate (e.g., use LEA to compare "
            "possible approaches, explain why one strategy may work "
            "better).' Be specific and practical. Do not repeat the level "
            "name verbatim, and do not use markdown."
        )
    else:
        prompt = (
            f"You are an assistant embedded in a student-facing learning "
            f"dashboard. The student was tagged at the '{level}' level for "
            f"the metacognition phase '{phase}' in {subject}.\n\n"
            f"Behavioural indicator for this phase: "
            f"{BEHAVIOURAL_INDICATORS_STUDENTS.get(phase, '')}\n\n"
            "Write a short (2-3 sentence), encouraging, second-person "
            "message telling the student what they're doing well or not "
            "yet doing, and one concrete strategy to try next, in the "
            "style of: 'You're starting to use strategies to complete your "
            "learning tasks. Level up by using LEA to compare different "
            "strategies, explain why you chose one, and check whether it "
            "is suitable for the task.' Do not use markdown."
        )

    try:
        print(f"Prompt for {audience}:\n{prompt}\n")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        print(response)
        text = response.choices[0].message.content
        return (text or "").strip() or _fallback_suggestion(phase, level, audience)
        # text_blocks = [b.text for b in response.content if b.type == "text"]
        # return "".join(text_blocks).strip() or _fallback_suggestion(phase, level, audience)
    except Exception as e:
        print(f"Error occurred: {e}")
        return _fallback_suggestion(phase, level, audience)


def _fallback_suggestion(phase: str, level: str, audience: str) -> str:
    """Used if no API key is configured or the API call fails."""
    if audience == "teacher":
        return (
            f"For students at '{level}' for {phase}:\n\n"
            f"Model think-alouds and provide scaffolds to these students to help "
            f"them make their thinking visible. Forcus on {phase.lower()} strategies "
            f"such as using LEA to compare possible approaches, and check whether it is suitable for the task."
        )
    return (
        f"You're currently at '{level}' for {phase}.\n\n"
        f"Try naming your strategy out loud before you start your next task."
    )


# ---------------------------------------------------------------------------
# Aggregation helpers shared by both pages
# ---------------------------------------------------------------------------

def level_counts(df: pd.DataFrame, column: str) -> dict:
    counts = df[column].value_counts()
    return {lvl: int(counts.get(lvl, 0)) for lvl in LEVELS}


def students_at_level(df: pd.DataFrame, column: str, level: str) -> list:
    return sorted(df.loc[df[column] == level, "student_name"].unique().tolist())
