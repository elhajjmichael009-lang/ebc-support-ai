import streamlit as st
import openai, os

st.set_page_config(page_title="EBC Support AI (Base)", page_icon="🌐")
st.title("🌐 EBC Support AI (Base)")

# ----- OpenAI setup -----
openai.api_key = os.getenv("OPENAI_API_KEY")

st.subheader("📘 Booking Information")
booking = st.text_area("Paste booking details", height=140)

st.subheader("💬 Customer Message")
customer = st.text_area("Paste customer message", height=120)

st.subheader("📨 Supplier Message")
supplier = st.text_area("Paste supplier message", height=120)

st.subheader("📝 Policy Text (optional)")
policy = st.text_area("Paste policy text", height=120)

if st.button("🤖 Analyze Case"):
    if not openai.api_key:
        st.error("OPENAI_API_KEY is missing (set it in Streamlit Secrets).")
    else:
        prompt = f"""
You are EBooking Center's Support AI Agent.

Tasks:
1) Brief case summary.
2) Recommend: Refund Approved / Denied / Partial (+reason).
3) Draft:
   - Customer reply (professional, clear).
   - Supplier message (what we need/ask).
   - Internal note (bullet points).

Booking:
{booking}

Customer:
{customer}

Supplier:
{supplier}

Policy:
{policy}
"""
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        st.text_area("AI Result", resp.choices[0].message["content"], height=500)
