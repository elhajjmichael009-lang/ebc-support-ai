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
# ---- AIDA Expander (Base) ----
with st.expander("🏨 AIDA Day Prices (base)"):
    st.caption("Logs in each time → fetches the same popup you see when clicking a date in AIDA.")
    aida_user = st.text_input("AIDA username")
    aida_pass = st.text_input("AIDA password", type="password")

    cols = st.columns(3)
    idProject = cols[0].number_input("idProject", value=194, step=1)
    idService = cols[1].number_input("idService", value=10621, step=1)
    serviceGroup = cols[2].text_input("serviceGroup", value="AC")

    date_iso = st.text_input("Date (YYYY-MM-DD)", value="2025-11-05")
    idScheme = st.number_input("idScheme", value=55565, step=1)
    priceSetId = st.number_input("priceSetId", value=8520, step=1)
    priceType = st.selectbox("priceType", ["supplierPrice", "resellerPrice"], index=0)

    if st.button("Fetch AIDA Day Prices"):
        if not aida_user or not aida_pass:
            st.error("Enter AIDA credentials.")
        else:
            try:
                from aida_client import login_aida, fetch_day_prices
                sess = login_aida(aida_user, aida_pass)
                data = fetch_day_prices(sess, int(idProject), int(idService), serviceGroup,
                                        date_iso, int(idScheme), int(priceSetId), priceType)
                st.success(f"Prices for {data['date']}")
                for grp in data["groups"]:
                    st.markdown(f"**{grp['name']}**")
                    if not grp["items"]:
                        st.write("No items")
                    for it in grp["items"]:
                        st.write(f"- {it['formula']} → {it['price']} {it['currency']}")
            except Exception as e:
                st.error(f"AIDA error: {e}")
