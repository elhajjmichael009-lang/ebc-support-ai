import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import urllib.parse

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

BASE = "https://aida.ebookingcenter.com"

def _absolute(url):
    return url if url.startswith("http") else urllib.parse.urljoin(BASE, url)

def aida_login(username: str, password: str):
    s = requests.Session()
    common_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    # Try PRIMARY login page (the one you showed earlier)
    login_pages = [
        f"{BASE}/tourOperator/login/",
        f"{BASE}/tourOperator/identity/login/",
    ]

    last_html = ""
    for login_page in login_pages:
        # 1) GET the login page to capture cookies + hidden inputs
        r = s.get(login_page, headers={**common_headers, "Referer": login_page}, allow_redirects=True, timeout=30)
        last_html = r.text

        soup = BeautifulSoup(r.text, "html.parser")
        form = soup.find("form")
        if not form:
            # Some skins load form via JS; try next variant
            continue

        # Build POST payload from all inputs present (keeps CSRF etc.)
        payload = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            payload[name] = inp.get("value", "")

        # Overwrite username/password fields (support multiple possible names)
        # Common names seen: username / user / email ; password / passwd
        for k in list(payload.keys()):
            kn = k.lower()
            if "user" in kn or "email" in kn or kn == "username":
                payload[k] = username
            if "pass" in kn or kn == "password":
                payload[k] = password

        # Some forms need a submit value
        if "submit" not in payload:
            payload["submit"] = "Login"

        action = form.get("action") or login_page
        post_url = _absolute(action)

        headers = {
            **common_headers,
            "Origin": BASE,
            "Referer": login_page,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        r2 = s.post(post_url, data=payload, headers=headers, allow_redirects=True, timeout=30)
        last_html = r2.text

        # Heuristics for success
        text_lower = r2.text.lower()
        landed_ok = (
            "logout" in text_lower or
            "my profile" in text_lower or
            "tour operator" in text_lower or
            "dashboard" in text_lower or
            "go to reseller" in text_lower
        )

        # Also check cookies usually set after login
        has_cookie = any(c.name in ("AIDA", "AIDAtourOperator") for c in s.cookies)

        if landed_ok and has_cookie:
            return s  # ✅ success

        # Some installs redirect to dashboard after another GET
        dash = s.get(f"{BASE}/tourOperator/dashboard/", headers=common_headers, timeout=30)
        if ("logout" in dash.text.lower()) or any(c.name in ("AIDA", "AIDAtourOperator") for c in s.cookies):
            return s  # ✅ success

        # otherwise try the next login variant in the loop

    # If both variants failed, return None but keep last_html for debug at the call site
    # (In your Streamlit code, print this when login is None.)
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
