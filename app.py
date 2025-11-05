import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("🔍 AIDA Price Fetcher (Simple Version)")

# --- Login ---
st.header("🔑 Login")
username = st.text_input("AIDA Username")
password = st.text_input("AIDA Password", type="password")

# --- Inputs ---
st.header("🏨 Hotel Search")

hotel_name = st.text_input("Hotel Name (for display only)")

idProject = st.text_input("idProject", "194")
idService = st.text_input("idService", "11400")
serviceGroup = st.text_input("serviceGroup", "AC")
date = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")
idScheme = st.text_input("idScheme", "55565")
priceSetId = st.text_input("priceSetId", "8520")
priceType = st.selectbox("Price Type", ["supplierPrice", "clientPrice"])

if st.button("Fetch Prices"):
    if not username or not password:
        st.error("Please enter login credentials.")
    else:
        st.write("🔑 Logging in…")

        login_url = "https://aida.ebookingcenter.com/tourOperator/login/"
        session = requests.Session()

        login_data = {
            "username": username,
            "password": password
        }

        # Send login
        session.post(login_url, data=login_data)

        # Now fetch prices
        st.write(f"📅 Fetching prices for **{hotel_name}** ({date})…")

        url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"

        payload = {
            "idService": idService,
            "serviceGroup": serviceGroup,
            "priceType": priceType,
            "date": date,
            "idScheme": idScheme,
            "priceSetId": priceSetId
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        }

        r = session.post(url, data=payload, headers=headers)
        html = r.text

        try:
            soup = BeautifulSoup(html, "html.parser")
            rows = soup.find_all("tr")

            if not rows:
                st.error("❌ No prices found for this date.")
            else:
                st.success("✅ Prices loaded successfully!")

                table_data = []
                for row in rows:
                    cols = row.find_all("td")
                    cols = [c.get_text(strip=True) for c in cols]
                    table_data.append(cols)

                st.table(table_data)

        except Exception as e:
            st.error("❌ Parsing error")
            st.code(html)
