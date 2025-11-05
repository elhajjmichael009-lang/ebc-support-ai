import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("🏨 AIDA Day Prices (Auto Mode)")

# --- INPUTS ---
username = st.text_input("AIDA Username")
password = st.text_input("AIDA Password", type="password")

idProject = st.text_input("idProject", "194")
date = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")

priceType = st.selectbox("Price Type", ["supplierPrice", "clientPrice"])


# ------------------------
# AIDA LOGIN
# ------------------------
def aida_login(username, password):
    login_url = "https://aida.ebookingcenter.com/tourOperator/login/"
    session = requests.Session()

    payload = {
        "username": username,
        "password": password,
        "submit": "Login"
    }

    r = session.post(login_url, data=payload)
    return session


# ------------------------
# AUTO-DETECT idService
# ------------------------
def detect_service(session, idProject):
    url = f"https://aida.ebookingcenter.com/tourOperator/projects/projectDetails/services/?idProject={idProject}"
    r = session.get(url)
    data = r.json()

    for s in data:
        if s.get("serviceGroup") == "AC":  # accommodation
            return s["idService"]

    return None


# ------------------------
# AUTO-DETECT idScheme + priceSetId
# ------------------------
def detect_scheme_and_priceset(session, idService):
    url = f"https://aida.ebookingcenter.com/tourOperator/projects/services/accSchemes/?idService={idService}"
    r = session.get(url)
    data = r.json()

    for scheme in data:
        if scheme.get("default") == True:
            return scheme["idScheme"], scheme["idPriceSet"]

    # fallback
    scheme = data[0]
    return scheme["idScheme"], scheme["idPriceSet"]


# ------------------------
# FETCH DAY PRICES
# ------------------------
def fetch_day_prices(session, idService, idScheme, priceSetId, priceType, date):
    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"

    payload = {
        "idService": idService,
        "serviceGroup": "AC",
        "priceType": priceType,
        "date": date,
        "idScheme": idScheme,
        "priceSetId": priceSetId,
    }

    r = session.post(url, data=payload)
    return r.text


# ------------------------
# RUN
# ------------------------
if st.button("Fetch Day Prices"):
    with st.spinner("Logging in..."):
        session = aida_login(username, password)

    with st.spinner("Detecting Service for this Hotel..."):
        idService = detect_service(session, idProject)

    st.success(f"✅ Auto-detected idService = {idService}")

    with st.spinner("Detecting Scheme + PriceSet..."):
        idScheme, priceSetId = detect_scheme_and_priceset(session, idService)

    st.success(f"✅ Auto-detected idScheme = {idScheme}")
    st.success(f"✅ Auto-detected priceSetId = {priceSetId}")

    with st.spinner("Fetching Day Prices..."):
        html = fetch_day_prices(session, idService, idScheme, priceSetId, priceType, date)

    st.subheader("✅ Raw HTML from AIDA")
    st.code(html)
