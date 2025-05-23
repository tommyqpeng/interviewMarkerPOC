import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Secrets ---
APP_PASSWORD = st.secrets["APP_PASSWORD"]

# --- Session State Setup ---
if "password_attempts" not in st.session_state:
    st.session_state.password_attempts = 0
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "password_input" not in st.session_state:
    st.session_state.password_input = ""
if "row_index" not in st.session_state:
    st.session_state.row_index = 0

# --- UI Title ---
st.title("Interview Question Marker")

# --- Password Gate ---
if st.session_state.password_attempts >= 3:
    st.error("❌ Too many incorrect attempts. Please reload the page to try again.")
    st.stop()

if not st.session_state.authenticated:
    st.session_state.password_input = st.text_input("Enter access password", type="password")
    if st.button("Submit Password"):
        if st.session_state.password_input == APP_PASSWORD:
            st.session_state.authenticated = True
        else:
            st.session_state.password_attempts += 1
            st.warning(f"Incorrect password. Attempts left: {3 - st.session_state.password_attempts}")
    if not st.session_state.authenticated:
        st.stop()

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GSHEET_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# --- Load Sheets ---
source_sheet = client.open_by_key(st.secrets["AnswerSheet_ID"]).sheet1
feedback_sheet = client.open_by_key(st.secrets["FeedbackSheet_ID"]).sheet1
answers = source_sheet.get_all_records()
feedback_records = feedback_sheet.get_all_records()

# --- Consultant Name ---
consultant_name = st.text_input("Consultant Name")
if not consultant_name:
    st.warning("Please enter your name to begin reviewing answers.")
    st.stop()

# --- Bounds Check ---
if st.session_state.row_index < 0:
    st.session_state.row_index = 0
elif st.session_state.row_index >= len(answers):
    st.success("🎉 You’ve reached the end of the answer list.")
    st.stop()

row = answers[st.session_state.row_index]

# --- Get previous feedback if exists ---
existing = [
    fb for fb in feedback_records
    if fb.get("AnswerIndex") == st.session_state.row_index + 1 and fb.get("ConsultantName") == consultant_name
]
prior_feedback = existing[-1].get("ManualFeedback", "") if existing else ""
prior_score = int(existing[-1].get("Score", 5)) if existing else 5

# --- Inputs ---
feedback = st.text_area("Your Feedback", value=prior_feedback, key="feedback_text")
score = st.slider("Score (0–10)", 0, 10, prior_score, key="score_value")

# --- Display Content ---
st.subheader(f"Answer {st.session_state.row_index + 1} of {len(answers)}")
st.markdown("**Student Answer:**")
st.write(row.get("AnswerText", "No answer found."))

# --- Save or Replace Feedback ---
def save_feedback():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    answer_index = st.session_state.row_index + 1
    headers = feedback_sheet.row_values(1)

    # Look for existing row to replace
    match_row = None
    for i, fb in enumerate(feedback_records):
        if fb.get("AnswerIndex") == answer_index and fb.get("ConsultantName") == consultant_name:
            match_row = i + 2  # +2 for 1-based index + header row
            break

    values = [
        timestamp,
        answer_index,
        consultant_name,
        row.get("AnswerText", ""),
        row.get("GPTFeedback", ""),
        feedback,
        score
    ]

    if match_row:
        feedback_sheet.update(f"A{match_row}:G{match_row}", [values])
    else:
        feedback_sheet.append_row(values)

# --- Navigation ---
col1, col2 = st.columns(2)

with col1:
    if st.button("⬅️ Previous Answer"):
        if st.session_state.row_index > 0:
            save_feedback()
            st.session_state.row_index -= 1

with col2:
    if st.button("➡️ Next Answer (Submit)"):
        save_feedback()
        st.session_state.row_index += 1
