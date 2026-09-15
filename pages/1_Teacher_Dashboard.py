import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    PHASES,
    PHASE_TO_COLUMN,
    LEVELS,
    LEVEL_COLORS,
    LEVEL_DESCRIPTIONS_TEACHERS,
    BEHAVIOURAL_INDICATORS_TEACHERS,
    CUSTOM_CSS,
    PLOTLY_CONFIG,
    load_data,
    get_suggested_action,
)

st.set_page_config(page_title="Teacher Dashboard", layout="wide")
st.html(CUSTOM_CSS)


df = load_data()

st.title("Mock-up of dashboard for teacher view")

# ---------------------------------------------------------------------------
# Suggested-action popup
# ---------------------------------------------------------------------------

@st.dialog("Suggested action")
def show_suggestion_dialog(phase, assignment, level, students, subject, audience):
    scope_label = f"{phase} · {assignment} · {level}" if assignment else f"{phase} (current level) · {level}"
    st.markdown(f"**{scope_label}**")
    if not students:
        st.write("No students in this group for the current filters.")
        return
    with st.spinner("Getting suggested action from the agent..."):
        suggestion = get_suggested_action(
            phase=phase,
            level=level,
            subject=subject,
            audience=audience,
        )
    st.info(suggestion)
    num_col1, num_col2 = st.columns(2)
    half = (len(students) + 1) // 2
    with num_col1:
        for i, name in enumerate(students[:half], start=1):
            st.write(f"{i}. {name}")
    with num_col2:
        for i, name in enumerate(students[half:], start=half + 1):
            st.write(f"{i}. {name}")


# ---------------------------------------------------------------------------
# Filters — Teacher dropdown sits above everything else, then the standard
# Subject / Assignment / Class row from the mock-up.
# ---------------------------------------------------------------------------

teacher_options = df["teacher_id"].unique()

t_col, _ = st.columns([1, 3])
with t_col:
    selected_teacher_id = st.selectbox("Teacher", teacher_options)

teacher_df = df[df["teacher_id"] == selected_teacher_id]

st.divider()

filt1, filt2, filt3 = st.columns(3)
with filt1:
    subject = st.selectbox("Subject", sorted(teacher_df["subject"].unique()))

subject_df = teacher_df[teacher_df["subject"] == subject]
assignment_names = sorted(subject_df["assignment_name"].unique())
class_choices = sorted(subject_df["class_name"].unique())
class_choice = class_choices[0] if class_choices else None

with filt2:
    if class_choice:
        assignment_choices = ["All"] + subject_df[subject_df["class_name"] == class_choice]["assignment_name"].unique().tolist()
    else:
        assignment_choices = ["All"] + assignment_names

    assignment_choice = st.selectbox("Assignment", assignment_choices)

with filt3:
    if assignment_choice != "All":
        class_choices = sorted(subject_df[subject_df["assignment_name"] == assignment_choice]["class_name"].unique())
    else:
        class_choices = sorted(subject_df["class_name"].unique())

    class_choice = st.selectbox("Class", class_choices)

scoped_df = subject_df[subject_df["class_name"] == class_choice]

if assignment_choice != "All":
    filtered_df = scoped_df[scoped_df["assignment_name"] == assignment_choice]
else:
    filtered_df = scoped_df

assignment_order = sorted(scoped_df["assignment_name"].unique())


# ---------------------------------------------------------------------------
# Layout: main dashboard (left) + legend / behavioural indicators (right)
# ---------------------------------------------------------------------------

main_col, side_col = st.columns([3, 1.1])

if "teacher_selection" not in st.session_state:
    st.session_state.teacher_selection = None  # (phase, assignment_or_None, level)

if "chart_gen" not in st.session_state:
    st.session_state.chart_gen = 0  # incremented each time a chart is generated, to force re-render of the suggested action dialog


def _mini_stacked_bar(counts: dict, height: int = 90, show_axis: bool = False):
    """A single thin horizontal stacked bar (one row, segments = levels)."""
    mini_df = pd.DataFrame(
        {"row": [""] * len(LEVELS), "level": LEVELS, "count": [counts.get(lvl, 0) for lvl in LEVELS]}
    )
    fig = px.bar(
        mini_df,
        x="count",
        y="row",
        color="level",
        orientation="h",
        category_orders={"level": LEVELS},
        color_discrete_map=LEVEL_COLORS,
        text="count",
        custom_data=["level"],
        height=height,
    )
    fig.update_traces(
        textposition="inside",
        texttemplate="%{text}",
        textfont_size=13,
        marker_line_width=1,
        marker_line_color="white",
    )
    fig.update_layout(
        barmode="stack",
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(showticklabels=show_axis, showgrid=False),
        yaxis=dict(showticklabels=False, range=[-0.5, 0.5]),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _students_at_level(scope_df, col_name, level):
    return sorted(scope_df.loc[scope_df[col_name] == level, "student_id"].unique().tolist())


with main_col:
    with st.container(border=True):
        # -----------------------------------------------------------------
        # Current Levels — one bordered box, Planning / Monitoring /
        # Reflection side by side in the same row (matches the mock-up).
        # -----------------------------------------------------------------
        with st.container(key="current_level_container", border=True):
            st.markdown(
                f"<div style='text-align:center; font-weight:600; font-size:20px;'>Current Levels</div>",
                unsafe_allow_html=True,
            )

            current_cols = st.columns(len(PHASES))
            for i, phase in enumerate(PHASES):
                col_name = PHASE_TO_COLUMN[phase]
                counts = filtered_df[col_name].value_counts().to_dict()
                with current_cols[i]:
                    fig = _mini_stacked_bar(counts, height=50)
                    event = st.plotly_chart(
                        fig,
                        width='stretch',
                        on_select="rerun",
                        selection_mode=("points",),
                        key=f"current_chart_{phase}_{st.session_state.chart_gen}",
                        config=PLOTLY_CONFIG,
                    )
                    pts = event.get("selection", {}).get("points", []) if event else []
                    if pts:
                        level_c = pts[0]["customdata"][0]
                        students_c = _students_at_level(filtered_df, col_name, level_c)
                        st.session_state.teacher_selection = (phase, None, level_c, students_c)
                        st.session_state.chart_gen += 1
                    st.markdown(f"<div style='text-align:center;'><b>{phase}</b></div>", unsafe_allow_html=True)

        st.write("")
        st.subheader("By assignment")

        # -----------------------------------------------------------------
        # Grid — assignments run across the top (columns), Planning /
        # Monitoring / Reflection run down the side (rows).
        # -----------------------------------------------------------------
        label_width = 0.9
        col_widths = [label_width] + [1] * len(assignment_order)

        header_cols = st.columns(col_widths)
        header_cols[0].markdown("")
        for j, a_name in enumerate(assignment_order, start=1):
            header_cols[j].markdown(
                f"<div style='text-align:center; font-weight:600;'>{a_name}</div>",
                unsafe_allow_html=True,
            )

        for phase in PHASES:
            col_name = PHASE_TO_COLUMN[phase]
            row_cols = st.columns(col_widths)
            row_cols[0].markdown(
                f"<div style='display:flex; align-items:center; height:50px; font-weight:600;'>{phase}</div>",
                unsafe_allow_html=True,
            )
            for j, a_name in enumerate(assignment_order, start=1):
                cell_df = filtered_df[filtered_df["assignment_name"] == a_name]
                counts = cell_df[col_name].value_counts().to_dict()
                with row_cols[j]:
                    fig = _mini_stacked_bar(counts, height=50)
                    event = st.plotly_chart(
                        fig,
                        width='stretch',
                        on_select="rerun",
                        selection_mode=("points",),
                        key=f"cell_chart_{phase}_{a_name}_{st.session_state.chart_gen}",
                        config=PLOTLY_CONFIG,
                    )
                    pts = event.get("selection", {}).get("points", []) if event else []
                    if pts:
                        level_c = pts[0]["customdata"][0]
                        students_c = _students_at_level(cell_df, col_name, level_c)
                        st.session_state.teacher_selection = (phase, a_name, level_c, students_c)
                        st.session_state.chart_gen += 1

        # -----------------------------------------------------------------
        # Suggested action callout — populated from the most recent click
        # -----------------------------------------------------------------
        if st.session_state.teacher_selection is not None:

            phase_sel, assignment_sel, level_sel, students = st.session_state.teacher_selection
            # if assignment_sel:
            #     group_df = filtered_df[filtered_df["assignment_name"] == assignment_sel]
            #     scope_label = f"{phase_sel} · {assignment_sel} · {level_sel}"
            # else:
            #     group_df = filtered_df
            #     scope_label = f"{phase_sel} (current level) · {level_sel}"

            # col_name = PHASE_TO_COLUMN[phase_sel]
            # students = sorted(group_df.loc[group_df[col_name] == level_sel, "student_id"].unique().tolist())

            if students:
                show_suggestion_dialog(phase=phase_sel, assignment=assignment_sel, level=level_sel, students=students, subject=subject, audience="teacher")
            else:
                st.write("No students in this group for the current filters.")

            st.session_state.teacher_selection = None

with side_col:
    st.markdown("### Behavioural Indicators of Metacognition")
    for phase in PHASES:
        st.markdown(f"**{phase}**")
        st.caption(BEHAVIOURAL_INDICATORS_TEACHERS[phase])

    st.markdown("### Levels of Metacognition")
    for level in LEVELS:
        st.markdown(
            f"<div style='background-color:{LEVEL_COLORS[level]}; "
            f"color:white; padding:6px 10px; border-radius:4px; margin-bottom:4px;'>"
            f"<b>{level}</b><br><span style='font-size:0.8em;'>{LEVEL_DESCRIPTIONS_TEACHERS[level]}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
