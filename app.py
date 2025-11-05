import streamlit as st
from openai import OpenAI
import os

# ---- Streamlit Page Config ----
st.set_page_config(page_title="EBC Support AI (Base)", page_icon="🌐")
st.title("🌐 EBC Support AI (Base)")

# ---- OpenAI Setup ----
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# ---- Form Inputs ----
st.subheader("📘 Booking Information")
booking = st.text_area("Paste booking details", height=140)

st.subheader("💬 Customer Message")
customer = st.text_area("Paste customer message", height=120)

st.subheader("📨 Supplier Message")
supplier = st.text_area("Paste supplier message", height=120)

st.subheader("📝 Policy Text (optional)")
policy = st.text_area("Paste policy text", height=120)

# ---- AI Analysis Button ----
if st.button("🤖 Analyze Case"):
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing (set it in Streamlit Secrets).")
    else:
        prompt = f"""
You are EBooking Center's Support AI Agent.

Tasks:
1) Give a clear case summary.
2) Recommend refund outcome: Approved / Denied / Partial (+reason).
3) Draft:
   - Customer reply (professional, respectful, clear).
   - Supplier message (what we need from them).
   - Internal note (bullet points only).

Booking:
{booking}

Customer:
{customer}

Supplier:
{supplier}

Policy:
{policy}
"""

        # ✅ NEW OpenAI API + gpt-4o-mini (no rate limit issues)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        result = response.choices[0].message.content

        # Display result
        st.subheader("✅ AI Result")
        st.text_area("Generated Response", result, height=500)
