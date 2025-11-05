import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from aida_client import (
    login_aida,
    find_service_by_name,
    get_active_scheme_and_priceset,
    fetch_day_html,
    parse_day_html,
)

st.set_page_config(page_title="Missing Prices Scanner", layout="wide")
st.title("🔍 Hotel Missing Prices Scanner (AIDA)")


# =============================================================
# INPUTS
# =============================================================
aida_user = st.text_input("AIDA Username")
aida_pass = st.text_input("AIDA Password", type="password")

hotel_name = st.text_input("Hotel Name (example: Britannia Suites)")
idProject = st.number_input("idProject", value=194)

days_to_scan = st.number_input("Days to check ahead", value=30)
priceType = st.selectbox("Price Type", ["supplierPrice", "resellerPrice"])

if st.button("Scan Missing Prices ✅", type="primary"):

    if not aida_user or not aida_pass:
        st.error("Enter AIDA credentials.")
        st.stop()

    if not hotel_name.strip():
        st.error("Enter a hotel name.")
        st.stop()

    try:
        # LOGIN
        st.write("🔑 Logging in…")
        sess = login_aida(aida_user, aida_pass)

        # FIND HOTEL
        st.write("🏨 Searching hotel…")

        info = find_service_by_name(sess, idProject, hotel_name)
        if not info:
            st.error("❌ Hotel not found in AIDA.")
            st.stop()

        idService = info["serviceId"]
        serviceGroup = info["serviceGroup"]

        st.success(f"✅ Found: {hotel_name} → serviceId={idService}, group={serviceGroup}")

        # SCHEME + PRICESET
        st.write("📝 Detecting active scheme + priceSet…")

        idScheme, priceSetId = get_active_scheme_and_priceset(
            sess, idProject, idService, serviceGroup
        )

        st.success(f"✅ idScheme={idScheme}, priceSetId={priceSetId}")

        # SCAN NEXT X DAYS
        missing = []
        today = datetime.now()

        st.write(f"📅 Scanning next {days_to_scan} days…")

        for i in range(int(days_to_scan)):
            date_iso = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            html = fetch_day_html(
                sess, idService, serviceGroup, date_iso, idScheme, priceSetId, priceType
            )
            data = parse_day_html(html)

            if not data["groups"]:
                missing.append(date_iso)

        # RESULTS
        st.subheader("📌 Missing Prices Results")

        if not missing:
            st.success("✅ No missing prices found. All days are priced correctly.")
        else:
            st.error(f"❌ Missing prices for {len(missing)} days.")
            st.table(pd.DataFrame({"Missing Dates": missing}))

    except Exception as e:
        st.error(f"🔥 ERROR: {e}")
