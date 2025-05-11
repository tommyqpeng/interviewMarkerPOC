import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Secrets ---
APP_PASSWORD = st.secrets["APP_PASSWORD"]

# --- Session State for Auth ---
if "password_attempts" not in st.session_state:
    st.session_state.password_attempts = 0
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "password_input" not in st.session_state:
    st.session_state.password_input = ""

# --- Session State for Navigation ---
if "row_index" not in st.session_state:
    st.session_state.row_index = 0
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False
if "feedback_text" not in st.session_state:
    st.session_state.feedback_text = ""
if "score_value" not in st.session_state:
    st.session_state.score_value = 5

# --- UI Title ---
st.title("Interview Question Marker")

# --- Password Gate ---
if st.session_state.password_attempts >= 3:
    st.error("Too many incorrect attempts. Please reload the page to try again.")
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

# --- Source and Feedback Sheets ---
source_sheet = client.open_by_key(st.secrets["AnswerSheet_ID"]).sheet1
feedback_sheet = client.open_by_key(st.secrets["FeedbackSheet_ID"]).sheet1

# --- Load Answers and Feedback ---
answers = source_sheet.get_all_records()
feedback_records = feedback_sheet.get_all_records()

# --- Consultant Name ---
consultant_name = st.text_input("Consultant Name")
if not consultant_name:
    st.warning("Please enter your name to begin reviewing answers.")
    st.stop()

# --- Track Progress ---
reviewed_indices = {f["AnswerIndex"] for f in feedback_records if f["ConsultantName"] == consultant_name}
unreviewed = [i for i in range(len(answers)) if (i + 1) not in reviewed_indices]

# --- Handle All Reviewed ---
if not unreviewed:
    st.success("🎉 You have reviewed all available answers.")
    st.stop()

# --- Initialize index to first unreviewed if out of bounds ---
if st.session_state.row_index not in unreviewed:
    st.session_state.row_index = unreviewed[0]

row = answers[st.session_state.row_index]

# --- Display Progress and Question ---
st.subheader(f"Answer {st.session_state.row_index + 1} of {len(answers)}")
st.markdown("**Student Answer:**")
st.write(row.get("AnswerText", "No answer found."))

# --- Feedback Input Fields ---
feedback = st.text_area("Your Feedback", value=st.session_state.feedback_text, key="feedback_text")
score = st.slider("Score (0–10)", 0, 10, st.session_state.score_value, key="score_value")

# --- Submit Feedback ---
if not st.session_state.feedback_submitted:
    if st.button("Submit Feedback"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        feedback_sheet.append_row([
            timestamp,
            st.session_state.row_index + 1,
            consultant_name,
            row.get("AnswerText", ""),
            row.get("GPTFeedback", ""),  # still saved but not displayed
            feedback,
            score
        ])
        st.success("Feedback saved!")
        st.session_state.feedback_submitted = True

# --- Navigation Buttons ---
col1, col2 = st.columns(2)

with col1:
    if st.button("Previous Answer"):
        current_unreviewed_index = unreviewed.index(st.session_state.row_index)
        if current_unreviewed_index > 0:
            st.session_state.row_index = unreviewed[current_unreviewed_index - 1]
            st.session_state.feedback_text = ""
            st.session_state.score_value = 5
            st.session_state.feedback_submitted = False

with col2:
    if st.session_state.feedback_submitted:
        if st.button("Next Answer"):
            current_unreviewed_index = unreviewed.index(st.session_state.row_index)
            if current_unreviewed_index + 1 < len(unreviewed):
                st.session_state.row_index = unreviewed[current_unreviewed_index + 1]
                st.session_state.feedback_text = ""
                st.session_state.score_value = 5
                st.session_state.feedback_submitted = False
            else:
                st.success("You have completed all reviews!")
