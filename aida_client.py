import requests
from bs4 import BeautifulSoup

BASE = "https://aida.ebookingcenter.com"
LOGIN = f"{BASE}/tourOperator/login/"
DAY_DETAILS = f"{BASE}/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"


# ============================================================
# 1) LOGIN
# ============================================================
def login_aida(username: str, password: str) -> requests.Session:
    s = requests.Session()
    payload = {"username": username, "password": password}

    r = s.post(LOGIN, data=payload, allow_redirects=True, timeout=30)

    if (r.url != LOGIN) or ("logout" in r.text.lower()):
        return s

    raise RuntimeError("AIDA login failed.")


# ============================================================
# 2) FIND HOTEL BY NAME → returns serviceId + serviceGroup
# ============================================================
def find_service_by_name(session, idProject, hotel_name):
    """
    Fully emulates AIDA DataTables AJAX used in Services List.
    Works on all pages.
    """
    hotel_name = hotel_name.lower().strip()

    url = f"{BASE}/tourOperator/projects/services/servicesList/Ajax.servicesList.php"

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE}/tourOperator/projects/projectDetails/services/?idProject={idProject}",
        "User-Agent": "Mozilla/5.0",
    }

    start = 0
    length = 50   # Fetch 50 per page (faster)
    draw = 1      

    while True:
        payload = {
            "draw": str(draw),
            "columns[0][data]": "0",
            "columns[1][data]": "1",
            "columns[2][data]": "2",
            "columns[3][data]": "3",
            "columns[4][data]": "4",
            "columns[5][data]": "5",
            "columns[6][data]": "6",

            "order[0][column]": "0",
            "order[0][dir]": "asc",

            "start": str(start),
            "length": str(length),

            "search[value]": "",
            "search[regex]": "false",

            "idProject": idProject,
            "currentTab": "0",
        }

        r = session.post(url, data=payload, headers=headers)
        r.raise_for_status()

        try:
            js = r.json()
        except:
            st.write("DEBUG:", r.text[:5000])
            return None

        data = js.get("data", [])
        if not data:
            return None

        for row in data:
            row_html = row[1]  # HTML block containing hotel name

            if hotel_name in row_html.lower():
                # Extract service ID from <button data-url="...idService=11400">
                soup = BeautifulSoup(row_html, "html.parser")
                btn = soup.find("button", {"data-url": True})
                if btn:
                    url = btn["data-url"]
                    if "idService=" in url:
                        idService = url.split("idService=")[1].split("&")[0]
                        return {
                            "serviceId": int(idService),
                            "serviceGroup": "AC"
                        }

        # Move to the next DataTables chunk
        start += length
        draw += 1

        # Stop if we fetched all rows
        if start >= js.get("recordsTotal", 0):
            return None




# ============================================================
# 3) SCHEME + PRICESET AUTO-DETECT
# ============================================================
def get_active_scheme_and_priceset(session, idProject, idService, serviceGroup):
    url = f"{BASE}/tourOperator/projects/services/servicePrices/"
    params = {
        "idProject": idProject,
        "idService": idService,
        "serviceGroup": serviceGroup,
        "refreshService": "1",
    }

    r = session.get(url, params=params, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # Active Scheme
    scheme_option = soup.find("option", selected=True)
    if not scheme_option:
        raise Exception("No active scheme found")
    idScheme = int(scheme_option["value"])

    # Button that opens priceSet popup
    btn = soup.find("button", {"data-url": True})
    if not btn:
        raise Exception("No priceSet popup button found")

    popup_url = BASE + btn["data-url"]

    popup = session.get(popup_url, timeout=30).text
    pop = BeautifulSoup(popup, "html.parser")

    ps_input = pop.find("input", {"name": "priceSetId"})
    if not ps_input:
        raise Exception("No priceSetId found")

    priceSetId = int(ps_input["value"])

    return idScheme, priceSetId


# ============================================================
# 4) FETCH PRICES FOR ONE DAY
# ============================================================
def fetch_day_html(session: requests.Session,
                   idService: int,
                   serviceGroup: str,
                   date_iso: str,
                   idScheme: int,
                   priceSetId: int,
                   priceType="supplierPrice"):
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE,
        "Referer": f"{BASE}/tourOperator/projects/services/servicePrices/",
    }

    data = {
        "idService": idService,
        "serviceGroup": serviceGroup,
        "priceType": priceType,
        "date": date_iso,
        "idScheme": idScheme,
        "priceSetId": priceSetId,
    }

    r = session.post(DAY_DETAILS, headers=headers, data=data, timeout=30)
    r.raise_for_status()
    return r.text


# ============================================================
# 5) PARSE DAY HTML → Extract Prices
# ============================================================
def parse_day_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    out = {"groups": []}

    container = soup.find("div", class_="container-fluid")
    if not container:
        return out

    current = None

    for row in container.find_all("div", recursive=False):
        # HEADERS
        header = row.find("div", class_="col")
        if header and "bg-primary" in header.get("class", []):
            title = header.get_text(strip=True)
            current = {"name": title, "items": []}
            out["groups"].append(current)
            continue

        # OCCUPANCY ROWS
        if "occupancy-row" in row.get("class", []):
            left = row.find("div", class_="col-6")
            rights = row.find_all("div", class_="col-6")

            formula = left.get_text(" ", strip=True)
            price_text = rights[-1].get_text(" ", strip=True)

            parts = price_text.split()
            if len(parts) < 2:
                continue

            price = parts[-2]
            currency = parts[-1]

            current["items"].append({
                "formula": formula,
                "price": price,
                "currency": currency,
            })

    return out
