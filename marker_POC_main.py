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

# --- Session State for Navigation & Submission ---
if "row_index" not in st.session_state:
    st.session_state.row_index = 0
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

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

# --- Load Answers ---
data = source_sheet.get_all_records()
answer_col = "AnswerText"  # Adjust if needed

# --- Consultant Name ---
consultant_name = st.text_input("Consultant Name")
if not consultant_name:
    st.warning("Please enter your name to begin reviewing answers.")
    st.stop()

# --- Display Current Answer ---
if st.session_state.row_index < len(data):
    row = data[st.session_state.row_index]
    st.subheader(f"Answer #{st.session_state.row_index + 1}")
    st.markdown("**Student Answer:**")
    st.write(row.get(answer_col, "No answer found."))

    st.markdown("**GPT Feedback:**")
    st.info(row.get("GPTFeedback", "No GPT feedback available."))

    feedback = st.text_area("Your Feedback")
    score = st.slider("Score (0–10)", 0, 10, 5)

    if not st.session_state.feedback_submitted:
        if st.button("Submit Feedback"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            feedback_sheet.append_row([
                timestamp,
                st.session_state.row_index + 1,
                consultant_name,
                row.get(answer_col, ""),
                row.get("GPTFeedback", ""),
                feedback,
                score
            ])
            st.session_state.feedback_submitted = True
            st.success("Feedback saved!")

    if st.session_state.feedback_submitted:
        if st.button("Next Answer"):
            st.session_state.row_index += 1
            st.session_state.feedback_submitted = False
            st.experimental_rerun()
else:
    st.success("All answers have been reviewed!")
