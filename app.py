import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="AIDA Price Debugger", layout="wide")

st.title("🔍 AIDA Price Debugger")

st.info("Enter the values from AIDA to test the price extraction. After you click submit, the app will show the RAW HTML response.")

# -------------------------
# INPUT FIELDS
# -------------------------
st.subheader("AIDA Parameters")

username = st.text_input("AIDA username")
password = st.text_input("AIDA password", type="password")

idProject = st.text_input("idProject", "194")
idService = st.text_input("idService", "10621")
serviceGroup = st.text_input("serviceGroup", "AC")

date = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")
idScheme = st.text_input("idScheme", "55565")
priceSetId = st.text_input("priceSetId", "8520")

priceType = st.text_input("priceType", "supplierPrice")

# -------------------------
# SUBMIT BUTTON
# -------------------------
if st.button("Fetch Prices"):
    st.warning("Sending request to AIDA…")

    # AIDA URL for daily price popup
    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"

    # Request payload
    payload = {
        "idService": idService,
        "serviceGroup": serviceGroup,
        "priceType": priceType,
        "date": date,
        "idScheme": idScheme,
        "priceSetId": priceSetId
    }

    # IMPORTANT: You MUST already be logged in to AIDA in your browser.
    # So we need session cookies (browser cookies).
    st.info("⚠️ You must paste your AIDA cookies for now.")

    cookies_input = st.text_input("Paste cookie string (AIDAtourOperator + AIDA) from browser DevTools", 
                                  placeholder='AIDAtourOperator=xxxx; AIDA=yyyy')

    if cookies_input.strip() == "":
        st.error("Missing cookies. Please paste your AIDA session cookies.")
    else:
        # Convert cookie string → dict
        cookies = {}
        try:
            for part in cookies_input.split(";"):
                name, value = part.strip().split("=", 1)
                cookies[name] = value
        except:
            st.error("Cookie format incorrect. It must look like: AIDAtourOperator=xxxx; AIDA=yyyy")
            st.stop()

        # Headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://aida.ebookingcenter.com",
            "Referer": f"https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}&serviceGroup={serviceGroup}",
        }

        # -------------------------
        # SEND REQUEST
        # -------------------------
        response = requests.post(url, headers=headers, data=payload, cookies=cookies)

        st.subheader("✅ RAW HTML RESPONSE FROM AIDA")

        html = response.text

        # ✅ SHOW HTML (YOU MUST COPY THIS FOR ME)
        st.code(html, language="html")

        # Also show status code
        st.write(f"HTTP Status:", response.status_code)

        # -------------------------
        # BASIC PARSE TEST
        # -------------------------
        st.subheader("🧪 Parsing Test")

        soup = BeautifulSoup(html, "html.parser")

        # Try to find price rows
        rows = soup.find_all("div", class_="row")

        st.write("Found rows:", len(rows))
