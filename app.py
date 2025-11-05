import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI()

st.title("🔍 AIDA Price Extractor (Manual Inputs)")

# ----------------------------
# USER INPUTS
# ----------------------------
username = st.text_input("AIDA Username")
password = st.text_input("AIDA Password", type="password")

idProject   = st.text_input("idProject", "194")
idService   = st.text_input("idService", "10621")
serviceGroup = st.text_input("serviceGroup", "AC")

date        = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")
idScheme    = st.text_input("idScheme", "55565")
priceSetId  = st.text_input("priceSetId", "8520")
priceType   = st.text_input("priceType", "supplierPrice")

# ----------------------------
# AIDA LOGIN FUNCTION
# ----------------------------
def aida_login(username, password):
    session = requests.Session()

    url = "https://aida.ebookingcenter.com/tourOperator/login/"

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    token = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token:
        return None

    token = token["value"]

    payload = {
        "__RequestVerificationToken": token,
        "username": username,
        "password": password
    }

    r2 = session.post(url, data=payload)

    if "Logout" in r2.text or "My profile" in r2.text:
        return session
    else:
        return None

# ----------------------------
# PARSE PRICE HTML
# ----------------------------
def extract_prices(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".occupancy-row")

    results = []

    for row in rows:
        occ = row.select_one(".col-6")
        price = row.select_one(".col-6.text-right")

        if occ and price:
            results.append({
                "occupancy": occ.get_text(" ", strip=True),
                "price": price.get_text(" ", strip=True),
            })

    return results

# ----------------------------
# RUN BUTTON
# ----------------------------
if st.button("📥 Fetch Prices"):
    st.write("🔑 Logging in...")

    session = aida_login(username, password)

    if not session:
        st.error("❌ Login failed.")
        st.stop()

    st.success("✅ Logged in.")

    # -------------------------
    # Fetch price page
    # -------------------------
    st.write("📄 Fetching price calendar...")

    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"

    payload = {
        "idService": idService,
        "serviceGroup": serviceGroup,
        "priceType": priceType,
        "date": date,
        "idScheme": idScheme,
        "priceSetId": priceSetId,
    }

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}"
    }

    r = session.post(url, data=payload, headers=headers)

    html = r.text

    st.write("✅ RAW HTML LOADED")
    st.code(html[:800] + "\n...\n(HTML truncated)")

    # -------------------------
    # Parse prices
    # -------------------------
    prices = extract_prices(html)

    if not prices:
        st.error("❌ No price rows found.")
        st.stop()

    st.success(f"✅ Found {len(prices)} price entries")

    for item in prices:
        st.write(f"**{item['occupancy']}** → {item['price']}")
