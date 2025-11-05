import requests
from bs4 import BeautifulSoup

BASE = "https://aida.ebookingcenter.com"

LOGIN = f"{BASE}/tourOperator/login/"
SERVICE_LIST = f"{BASE}/tourOperator/projects/services/servicesList/Ajax.servicesList.php"
DAY_DETAILS = f"{BASE}/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"


# ============================================================
# ✅ LOGIN
# ============================================================
def login_aida(username: str, password: str) -> requests.Session:
    s = requests.Session()
    payload = {"username": username, "password": password}
    r = s.post(LOGIN, data=payload, allow_redirects=True)

    if (r.url != LOGIN) or ("logout" in r.text.lower()):
        return s

    raise RuntimeError("AIDA login failed.")


# ============================================================
# ✅ FIND HOTEL BY NAME (SEARCHES ALL PAGES)
# ============================================================
def find_hotel_by_name(session, idProject, hotelName):
    page = 1
    hotelName = hotelName.lower().strip()

    while True:
        payload = {
            "resultsPerPage": 200,
            "currentPage": page,
            "idProject": idProject,
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-KL-ksospc-Ajax-Request": "Ajax_Request",
            "Referer": f"{BASE}/tourOperator/projects/projectDetails/services/?idProject={idProject}"
        }

        r = session.post(SERVICE_LIST, data=payload, headers=headers)
        if r.status_code != 200:
            return None

        data = r.json()

        items = data.get("items", [])
        if not items:
            return None  # no more pages

        for item in items:
            name = item.get("serviceName", "").lower()
            if hotelName in name:
                return {
                    "serviceId": int(item["idService"]),
                    "serviceGroup": item["serviceGroup"],
                    "hotelName": item["serviceName"]
                }

        page += 1


# ============================================================
# ✅ GET ACTIVE SCHEME + PRICESET
# ============================================================
def get_active_scheme_and_priceset(session, idProject, idService, serviceGroup):
    url = f"{BASE}/tourOperator/projects/services/servicePrices/"
    params = {
        "idProject": idProject,
        "idService": idService,
        "serviceGroup": serviceGroup,
        "refreshService": "1",
    }

    r = session.get(url, params=params)
    soup = BeautifulSoup(r.text, "html.parser")

    scheme_option = soup.find("option", selected=True)
    idScheme = int(scheme_option["value"])

    # Inside price set popup:
    ps_button = soup.find("button", {"data-url": True})
    data_url = ps_button["data-url"]

    popup_html = session.get(BASE + data_url).text
    popup = BeautifulSoup(popup_html, "html.parser")

    ps_input = popup.find("input", {"name": "priceSetId"})
    priceSetId = int(ps_input["value"])

    return idScheme, priceSetId


# ============================================================
# ✅ FETCH DAY PRICES HTML
# ============================================================
def fetch_day_html(session, idProject, idService, serviceGroup, date_iso, idScheme, priceSetId, priceType):
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-KL-ksospc-Ajax-Request": "Ajax_Request",
        "Referer": f"{BASE}/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}&serviceGroup={serviceGroup}",
    }

    data = {
        "idService": idService,
        "serviceGroup": serviceGroup,
        "priceType": priceType,
        "date": date_iso,
        "idScheme": idScheme,
        "priceSetId": priceSetId,
    }

    r = session.post(DAY_DETAILS, headers=headers, data=data)
    r.raise_for_status()
    return r.text


# ============================================================
# ✅ PARSE DAY HTML (FORMULAS + PRICES)
# ============================================================
def parse_day_html(html):
    soup = BeautifulSoup(html, "html.parser")

    out = {"scheme": None, "groups": []}

    scheme_span = soup.find("span", class_="bold")
    if scheme_span:
        out["scheme"] = scheme_span.get_text(strip=True)

    container = soup.find("div", class_="container-fluid")
    if not container:
        return out

    current_group = None

    for div in container.find_all("div", recursive=False):
        header = div.find("div", class_="col")
        if header and "bg-primary" in header.get("class", []):
            title = header.get_text(strip=True)
            current_group = {"name": title, "items": []}
            out["groups"].append(current_group)
            continue

        if "occupancy-row" in div.get("class", []):
            if current_group is None:
                current_group = {"name": "Room", "items": []}
                out["groups"].append(current_group)

            cols = div.find_all("div", class_="col-6")
            if len(cols) >= 2:
                formula = cols[0].get_text(" ", strip=True)
                price_raw = cols[1].get_text(" ", strip=True).split()

                if len(price_raw) >= 2:
                    price = price_raw[-2]
                    currency = price_raw[-1]

                    current_group["items"].append({
                        "formula": formula,
                        "price": price,
                        "currency": currency
                    })

    return out
