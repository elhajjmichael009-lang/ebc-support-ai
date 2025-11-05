import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("AIDA Price Extractor (Auto-Detect Version)")

username = st.text_input("AIDA Username")
password = st.text_input("AIDA Password", type="password")
idProject = st.text_input("Project ID", "194")
date = st.text_input("Date (YYYY-MM-DD)", "2025-11-05")

run_btn = st.button("🔍 Extract Prices")

# -----------------------------
# LOGIN FUNCTION
# -----------------------------
def aida_login(username, password):
    session = requests.Session()

    login_page = "https://aida.ebookingcenter.com/tourOperator/identity/login/"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": login_page,
    }

    # STEP 1 — Get login page to extract RequestVerificationToken
    r = session.get(login_page, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    token = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token:
        return None

    token_value = token.get("value")

    # STEP 2 — Send login POST including the token
    data = {
        "__RequestVerificationToken": token_value,
        "username": username,
        "password": password
    }

    r2 = session.post(login_page, data=data, headers=headers, allow_redirects=True)

    # ✅ Successful login indicators
    if "Logout" in r2.text or "AIDA TourOperator" in r2.text:
        return session

    return None

# -----------------------------
# AUTO DETECT SERVICE (AC)
# -----------------------------
def detect_service(session, idProject):
    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicesList/"

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://aida.ebookingcenter.com/tourOperator/projects/projectDetails/services/?idProject={idProject}",
        "User-Agent": "Mozilla/5.0",
    }

    data = {"idProject": idProject, "currentTab": "0"}

    r = session.post(url, headers=headers, data=data)
    html = r.text

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    if not rows:
        return None, html

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        group = cols[2].get_text(strip=True)

        if group == "AC":
            link = cols[0].find("a")
            if link and "idService=" in link.get("href"):
                href = link.get("href")
                idService = href.split("idService=")[1].split("&")[0]
                return idService, None

    return None, html

# -----------------------------
# DETECT idScheme + priceSetId
# -----------------------------
def detect_scheme_and_priceset(session, idService):
    url = f"https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/?idService={idService}"

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    scheme_input = soup.find("input", {"name": "idScheme"})
    priceset_input = soup.find("input", {"name": "priceSetId"})

    if not scheme_input or not priceset_input:
        return None, None, r.text

    scheme = scheme_input.get("value")
    priceset = priceset_input.get("value")

    return scheme, priceset, None

# -----------------------------
# EXTRACT PRICES
# -----------------------------
def extract_prices(session, idService, idScheme, priceSetId, date):
    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/loadDatePrices/"

    data = {
        "idService": idService,
        "idScheme": idScheme,
        "priceSetId": priceSetId,
        "loadDate": date,
        "priceType": "supplierPrice",
        "serviceGroup": "AC",
    }

    r = session.post(url, data=data)
    html = r.text

    soup = BeautifulSoup(html, "html.parser")

    results = []

    # Room title rows
    room_titles = soup.find_all("div", class_="bg-primary")

    for title in room_titles:
        room_name = title.get_text(strip=True)

        # Next rows are prices
        row = title.find_parent("div").find_next_sibling("div")

        while row and "occupancy-row" in row.get("class", []):
            cols = row.find_all("div", class_="col-6")

            occupancy = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)

            results.append({
                "room": room_name,
                "occupancy": occupancy,
                "price": price
            })

            row = row.find_next_sibling("div")

    return results, html

# -----------------------------
# RUN PROCESS
# -----------------------------
if run_btn:

    st.write("🔑 Logging in…")

    session = aida_login(username, password)

    if session is None:
        st.error("❌ Login failed.")
        st.stop()

    st.success("✅ Logged in!")

    # Detect service
    st.write("🔎 Detecting idService…")

    idService, debug1 = detect_service(session, idProject)

    if idService is None:
        st.error("❌ Could not detect idService")
        st.code(debug1, language="html")
        st.stop()

    st.success(f"✅ idService = {idService}")

    # Detect scheme + priceSetId
    st.write("🔎 Detecting idScheme + priceSetId…")

    idScheme, priceSetId, debug2 = detect_scheme_and_priceset(session, idService)

    if idScheme is None:
        st.error("❌ Could not detect scheme or priceSetId")
        st.code(debug2, language="html")
        st.stop()

    st.success(f"✅ idScheme = {idScheme}")
    st.success(f"✅ priceSetId = {priceSetId}")

    # Extract prices
    st.write("📥 Extracting prices…")

    prices, debug_html = extract_prices(session, idService, idScheme, priceSetId, date)

    if not prices:
        st.error("❌ Could not extract prices.")
        st.code(debug_html, language="html")
        st.stop()

    st.success("✅ Prices extracted!")

    for p in prices:
        st.write(f"**{p['room']}** — {p['occupancy']} → **{p['price']}**")
