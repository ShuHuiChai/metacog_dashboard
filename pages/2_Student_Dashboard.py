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
    LEVEL_DESCRIPTIONS_STUDENTS,
    BEHAVIOURAL_INDICATORS_STUDENTS,
    CUSTOM_CSS,
    PLOTLY_CONFIG,
    load_data,
    get_suggested_action,
)

st.set_page_config(page_title="Student Dashboard", page_icon="🎓", layout="wide")
st.html(CUSTOM_CSS)

df = load_data()

st.title("Mock-up of dashboard for student view (per subject)")


# ---------------------------------------------------------------------------
# Suggested-action popup
# ---------------------------------------------------------------------------

@st.dialog("Suggested next step")
def show_suggestion_dialog(phase, assignment_label, level, subject):
    scope_label = (
        f"{phase} · {assignment_label} · {level}"
        if assignment_label
        else f"{phase} (current level) · {level}"
    )
    st.markdown(f"**{scope_label}**")
    with st.spinner("Getting your suggested next step from the agent..."):
        suggestion = get_suggested_action(
            phase=phase,
            level=level,
            # student_names=(student_id,),
            subject=subject,
            audience="student",
        )
    st.info(suggestion)


# ---------------------------------------------------------------------------
# Filters — Student dropdown sits above everything else, then Subject /
# Assignment from the mock-up.
# ---------------------------------------------------------------------------

student_options = sorted(df["student_id"].drop_duplicates())

s_col, _ = st.columns([1, 3])
with s_col:
    selected_student_id = st.selectbox("Student", student_options)

student_df = df[df["student_id"] == selected_student_id]

filt1, filt2_placeholder = st.columns(2)
with filt1:
    subject = st.selectbox("Subject", sorted(student_df["subject"].unique()))
subject_df = student_df[student_df["subject"] == subject].sort_values("assignment_date")

# A student can have more than one assignment_id sharing the same
# assignment_name (e.g. same assignment offered in two classes/attempts),
# so everything below is keyed on the unique assignment_id, with a
# "Name (dd/mm/yyyy)" label built from assignment_name + assignment_date for
# display — matching the mock-up's "Assignment 1 (dd/mm/yyyy)" format.
assignment_lookup = subject_df.drop_duplicates(subset="assignment_id")
id_to_label = {
    row.assignment_id: f"{row.assignment_name} ({pd.to_datetime(row.assignment_date).strftime('%d/%m/%Y')})"
    for row in assignment_lookup.itertuples()
}
label_to_id = {v: k for k, v in id_to_label.items()}

assignment_order = (
    assignment_lookup.sort_values("assignment_date")["assignment_id"].tolist()
)
assignment_labels_ordered = [id_to_label[i] for i in assignment_order]

with filt2_placeholder:
    assignment_choice_label = st.selectbox("Assignment", ["All"] + assignment_labels_ordered)

if assignment_choice_label != "All":
    chosen_id = label_to_id[assignment_choice_label]
    filtered_df = subject_df[subject_df["assignment_id"] == chosen_id]
else:
    filtered_df = subject_df

st.divider()

main_col, divider_col, side_col = st.columns([3, 0.06, 1.1])

with divider_col:
    st.markdown(
        "<div style='border-left: 1px solid #d0d0d0; height: 100%; margin: 0 auto; width: 1px;'></div>",
        unsafe_allow_html=True,
    )

with main_col:
    # -----------------------------------------------------------------
    # Current Levels — Planning / Monitoring / Reflection badges,
    # side by side in the same row (matches the mock-up).
    # -----------------------------------------------------------------
    with st.container(border=True):
        with st.container(key="current_level_container", border=True):
            st.markdown(
                "<div style='text-align:center; font-weight:600; font-size:20px'>Current Levels</div>",
                unsafe_allow_html=True,
            )
            
            badge_cols = st.columns(len(PHASES))
            for i, phase in enumerate(PHASES):
                col_name = PHASE_TO_COLUMN[phase]
                scope = filtered_df if assignment_choice_label != "All" else subject_df
                current_level = (
                    scope.sort_values("assignment_date")[col_name].iloc[-1] if not scope.empty else "Not Observed"
                )
                with badge_cols[i]:
                    st.markdown(
                        f"<div style='background-color:{LEVEL_COLORS[current_level]}; color:white; "
                        f"text-align:center; padding:10px; border-radius:6px; font-weight:600;'>"
                        f"{current_level}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("💡 Suggested next step", key=f"badge_btn_{phase}", use_container_width=True):
                        show_suggestion_dialog(phase, None, current_level, subject)
                    st.markdown(
                        f"<div style='text-align:center; margin-top: 10px; margin-bottom: 10px;'><b>{phase}</b></div>",
                        unsafe_allow_html=True,
                    )
                    

        st.write("")
        st.subheader("Progress by assignment")
        # st.caption("Click a segment below to see a suggested next step for that assignment.")

        # -----------------------------------------------------------------
        # One bordered box per phase, assignments running left to right
        # within the box (matches the mock-up rows), keyed by assignment_id.
        # -----------------------------------------------------------------
        for phase in PHASES:
            col_name = PHASE_TO_COLUMN[phase]
            phase_df = (
                filtered_df[["assignment_id", col_name]]
                .rename(columns={col_name: "level"})
                .set_index("assignment_id")
                .reindex(assignment_order)
                .reset_index()
            )
            phase_df["level"] = phase_df["level"].fillna("Not Observed")
            phase_df["assignment_label"] = phase_df["assignment_id"].map(id_to_label)
            phase_df["height"] = 1

            with st.container(border=True):
                st.markdown(f"**{phase}**")

                fig = px.bar(
                    phase_df,
                    x="assignment_label",
                    y="height",
                    color="level",
                    category_orders={"assignment_label": assignment_labels_ordered, "level": LEVELS},
                    color_discrete_map=LEVEL_COLORS,
                    custom_data=["assignment_label", "level"],
                    height=110,
                )
                fig.update_traces(marker_line_width=1, marker_line_color="white", hoverinfo="skip", hovertemplate=None)
                fig.update_layout(
                    bargap=0,
                    showlegend=False,
                    # legend_title_text="",
                    xaxis_title=None,
                    yaxis_title=None,
                    yaxis=dict(showticklabels=False, range=[0, 1]),
                    margin=dict(l=10, r=10, t=10, b=10),
                    hovermode=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )

                event = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode=("points",),
                    key=f"student_phase_chart_{phase}",
                    config=PLOTLY_CONFIG,
                )
                pts = event.get("selection", {}).get("points", []) if event else []
                if pts:
                    assignment_label_c, level_c = pts[0]["customdata"][0], pts[0]["customdata"][1]
                    show_suggestion_dialog(phase, assignment_label_c, level_c, subject)

        st.subheader("Evidence log")
        long_rows = []
        for phase in PHASES:
            col_name = PHASE_TO_COLUMN[phase]
            for r in filtered_df.itertuples():
                long_rows.append(
                    {
                        "Phase": phase,
                        "Level": getattr(r, col_name),
                        "Assignment": id_to_label[r.assignment_id],
                        "Evidence": getattr(r, f"{phase.lower()}_evidence"),
                    }
                )
        evidence_df = pd.DataFrame(long_rows).sort_values(["Assignment"])
        # st.dataframe(evidence_df, width='stretch', hide_index=True)
        st.table(evidence_df, width='stretch', hide_index=True)

with side_col:
    st.markdown("### Behavioural Indicators of Metacognition")
    for phase in PHASES:
        st.markdown(f"**{phase}**")
        st.caption(BEHAVIOURAL_INDICATORS_STUDENTS[phase])

    st.markdown("### Levels of Metacognition")
    for level in LEVELS:
        st.markdown(
            f"<div style='background-color:{LEVEL_COLORS[level]}; "
            f"color:white; padding:6px 10px; border-radius:4px; margin-bottom:4px;'>"
            f"<b>{level}</b><br><span style='font-size:0.8em;'>{LEVEL_DESCRIPTIONS_STUDENTS[level]}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )