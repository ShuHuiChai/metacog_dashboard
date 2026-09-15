import streamlit as st

st.set_page_config(
    page_title="Metacognition Dashboard",
    layout="wide",
)

st.title("LAWG PoC: Metacognition Dashboard")
st.write(
    "Use the sidebar (or the buttons below) to switch between the **Teacher** "
    "view and the **Student** view."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Teacher Dashboard")
    st.write(
        "See metacognition levels across a class, for every assignment and "
        "phase (Planning / Monitoring / Reflection), with AI-suggested "
        "next steps for groups of students."
    )
    st.page_link("pages/1_Teacher_Dashboard.py", label="Open Teacher Dashboard")

with col2:
    st.subheader("Student Dashboard")
    st.write(
        "See your own metacognition levels per subject and assignment, "
        "with AI-suggested next steps to level up."
    )
    st.page_link("pages/2_Student_Dashboard.py", label="Open Student Dashboard")

