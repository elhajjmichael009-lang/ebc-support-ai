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
def find_hotel_by_name(session, idProject, hotel_name, max_pages=50):
    """
    Search through all pages in Services List to find a hotel by name.

    Returns:
    - idService
    - serviceGroup
    - matched_hotel_name
    """
    url = f"{BASE}/tourOperator/projects/services/servicesList/"

    headers = {
        "Referer": f"{BASE}/tourOperator/projects/projectDetails/services/?idProject={idProject}",
        "X-Requested-With": "XMLHttpRequest",
        "X-KL-ksospc-Ajax-Request": "Ajax_Request",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
    }

    for page in range(1, max_pages + 1):
        data = {
            "resultsPerPage": "10",
            "currentPage": str(page),
            "idProject": str(idProject)
        }

        r = session.post(url, headers=headers, data=data, timeout=20)
        html = r.text

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            name_text = cols[1].get_text(" ", strip=True)
            if hotel_name.lower() in name_text.lower():
                # extract idService from buttons
                btn = cols[1].find("button", {"data-url": True})
                if not btn:
                    continue

                data_url = btn["data-url"]
                # extract idService (example: ...?idService=11400)
                if "idService=" in data_url:
                    idService = data_url.split("idService=")[1].split("&")[0]
                    serviceGroup = "AC"  # always AC in your project

                    return int(idService), serviceGroup, name_text

        # no rows found? stop early
        if not rows:
            break

    return None, None, None




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
