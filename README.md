# Metacognition Dashboard (Streamlit)

Two-page Streamlit app implementing the teacher and student dashboard mock-ups.

## Structure

```
metacog_dashboard/
├── app.py                          # Landing page / entry point
├── utils.py                        # Shared constants, data loading, LLM helper
├── pages/
│   ├── 1_Teacher_Dashboard.py      # Teacher view
│   └── 2_Student_Dashboard.py      # Student view
├── data/
│   └── sample_data.csv             # Synthetic sample data (auto-generated on first run)
└── requirements.txt
```

Streamlit automatically turns everything in `pages/` into separate pages with
navigation in the sidebar — that's how the "toggle between teacher and
student view" requirement is implemented. The numeric prefixes control the
order they appear in.

## Running it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional, enables live AI suggestions
streamlit run app.py
```

Without `ANTHROPIC_API_KEY` set, clicking a bar/segment still works — it
just shows a templated fallback suggestion instead of a Claude-generated one,
so you can demo the UI without an API key.

## Plugging in real data

Replace the body of `load_data()` in `utils.py` with a query against your
real source (database, API, exported CSV, etc.). The rest of the app only
depends on the dataframe having these columns:

| column            | meaning                                             |
|-------------------|------------------------------------------------------|
| assignment_id     | unique assignment identifier                        |
| assignment_name   | display name, e.g. "Assignment 1"                    |
| subject           | e.g. "Secondary 3 Chemistry"                          |
| class_id / class_name | class identifiers                                |
| teacher_id / teacher_name | teacher identifiers                          |
| student_id / student_name | student identifiers                          |
| due_date          | ISO date, used to order assignments / find "current" |
| planning_level    | one of Not Observed / Emerging / Proficient / Accomplished |
| monitoring_level  | same scale, for Monitoring                           |
| evaluation_level  | same scale, for Reflection                           |
| evidence          | (optional) free-text evidence snippet for the table  |

## How the "click to see suggestion" interaction works

Each stacked bar chart is a Plotly figure rendered with
`st.plotly_chart(..., on_select="rerun")`. Clicking a segment (a specific
phase/assignment/level group) triggers a rerun with the click info in the
chart's return value. The app reads which `(phase, assignment, level)` was
clicked, looks up the matching students, and calls
`utils.get_suggested_action(...)`, which sends a short prompt to Claude
(`claude-sonnet-5` via the Anthropic API) describing the phase, level, and
behavioural indicator, and asks for a 2–3 sentence suggested action — mirroring
the call-out boxes in the mock-ups. Results are cached per
(phase, level, students, subject, audience) via `st.cache_data` to avoid
repeat API calls for the same click.
