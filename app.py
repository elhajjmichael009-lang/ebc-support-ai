import streamlit as st
from openai import OpenAI
import os
import pandas as pd

from aida_client import login_aida, fetch_day_html, parse_day_html

# ---- Streamlit Page Config ----
st.set_page_config(page_title="EBC Support AI (Base + AIDA)", page_icon="🌐", layout="wide")
st.title("🌐 EBC Support AI (Base + AIDA Day Prices)")

# ---- OpenAI Setup ----
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# =========================================
# SECTION 1 — Support AI (unchanged, gpt-4o-mini)
# =========================================
with st.container():
    st.header("🤖 Support Case Analyzer")

    colA, colB = st.columns(2)
    with colA:
        booking = st.text_area("📘 Booking Information", height=140,
                               placeholder="Booking ID, Hotel, Dates, Room, Meal plan, Paid amount, Cancellation deadline...")
        supplier = st.text_area("📨 Supplier Message", height=120)
    with colB:
        customer = st.text_area("💬 Customer Message", height=120)
        policy = st.text_area("📝 Policy Text (optional)", height=120)

    if st.button("Analyze Case with AI", type="primary"):
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
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            result = response.choices[0].message.content
            st.subheader("✅ AI Result")
            st.text_area("Generated Response", result, height=500)

# =========================================
# SECTION 2 — AIDA Day Prices (login each time)
# =========================================
st.markdown("---")
st.header("🏨 AIDA Day Prices")

col1, col2, col3 = st.columns(3)
with col1:
    aida_user = st.text_input("AIDA Username")
with col2:
    aida_pass = st.text_input("AIDA Password", type="password")
with col3:
    priceType = st.selectbox("Price Type", ["supplierPrice", "resellerPrice"], index=0)

col4, col5, col6 = st.columns(3)
with col4:
    idProject = st.number_input("idProject", value=194, step=1)
with col5:
    idService = st.number_input("idService", value=10621, step=1)
with col6:
    serviceGroup = st.text_input("serviceGroup", value="AC")

col7, col8, col9 = st.columns(3)
with col7:
    date_iso = st.text_input("Date (YYYY-MM-DD)", value="2025-11-05")
with col8:
    idScheme = st.number_input("idScheme", value=55565, step=1)
with col9:
    priceSetId = st.number_input("priceSetId", value=8520, step=1)

if st.button("Fetch Day Prices", type="secondary"):
    if not aida_user or not aida_pass:
        st.error("Enter AIDA credentials.")
    else:
        try:
            sess = login_aida(aida_user, aida_pass)
            html = fetch_day_html(sess,
                                  int(idProject), int(idService), serviceGroup,
                                  date_iso, int(idScheme), int(priceSetId), priceType)

            data = parse_day_html(html)

            # Show scheme
            if data.get("scheme"):
                st.caption(f"Pricing scheme: **{data['scheme']}**")

            # Render tables per group
            if not data["groups"]:
                st.info("No price rows found for this day / scheme / price set.")
            else:
                all_rows = []
                for grp in data["groups"]:
                    st.subheader(grp["name"])
                    if not grp["items"]:
                        st.write("No items")
                        continue
                    df = pd.DataFrame(grp["items"])
                    st.table(df)
                    # collect for global CSV
                    for it in grp["items"]:
                        all_rows.append({
                            "group": grp["name"],
                            "formula": it["formula"],
                            "price": it["price"],
                            "currency": it["currency"],
                            "date": date_iso,
                            "priceType": priceType
                        })

                if all_rows:
                    big = pd.DataFrame(all_rows)
                    csv = big.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Download CSV", csv, file_name=f"aida_{idService}_{date_iso}.csv", mime="text/csv")

            # Debug toggle
            with st.expander("🔧 Raw HTML (debug)"):
                st.code(html, language="html")

        except Exception as e:
            st.error(f"AIDA error: {e}")
