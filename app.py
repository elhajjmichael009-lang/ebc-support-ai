import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

st.title("🏨 AIDA Day Prices (Auto Mode)")

# --- INPUTS ---
username = st.text_input("AIDA Username")
password = st.text_input("AIDA Password", type="password")
idProject = st.text_input("idProject", "194")
date = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")
priceType = st.selectbox("Price Type", ["supplierPrice", "clientPrice"])


# -----------------------------------
#  LOGIN
# -----------------------------------
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


# -----------------------------------
#  SAFE JSON LOADER (IMPORTANT FIX)
# -----------------------------------
def try_json(response):
    try:
        return response.json()
    except:
        return None


# -----------------------------------
#  AUTO-DETECT SERVICE
# -----------------------------------
def detect_service(session, idProject):
    url = f"https://aida.ebookingcenter.com/tourOperator/projects/projectDetails/services/?idProject={idProject}"
    r = session.get(url)

    data = try_json(r)
    if not data:
        return None, r.text  # return raw html as error

    for s in data:
        if s.get("serviceGroup") == "AC":
            return s["idService"], None

    return None, data


# -----------------------------------
#  AUTO-DETECT SCHEME + PRICESET
# -----------------------------------
def detect_scheme(session, idService):
    url = f"https://aida.ebookingcenter.com/tourOperator/projects/services/accSchemes/?idService={idService}"
    r = session.get(url)

    data = try_json(r)
    if not data:
        return None, None, r.text

    # find default scheme
    for scheme in data:
        if scheme.get("default") is True:
            return scheme["idScheme"], scheme["idPriceSet"], None

    # fallback
    scheme = data[0]
    return scheme["idScheme"], scheme["idPriceSet"], None


# -----------------------------------
#  FETCH PRICES
# -----------------------------------
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


# -----------------------------------
#  BUTTON ACTION
# -----------------------------------
if st.button("Fetch Day Prices"):
    with st.spinner("Logging into AIDA..."):
        session = aida_login(username, password)

    # ---- SERVICE ----
    with st.spinner("Detecting accommodation service..."):
        idService, error = detect_service(session, idProject)

    if idService is None:
        st.error("❌ Could not detect idService")
        st.code(error)
        st.stop()

    st.success(f"✅ idService = {idService}")

    # ---- SCHEME ----
    with st.spinner("Detecting scheme + priceSet..."):
        idScheme, priceSetId, error = detect_scheme(session, idService)

    if idScheme is None:
        st.error("❌ Could not detect scheme")
        st.code(error)
        st.stop()

    st.success(f"✅ idScheme = {idScheme}")
    st.success(f"✅ priceSetId = {priceSetId}")

    # ---- PRICES ----
    with st.spinner("Fetching prices..."):
        html = fetch_day_prices(session, idService, idScheme, priceSetId, priceType, date)

    st.subheader("✅ Raw HTML Response")
    st.code(html)
