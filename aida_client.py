# aida_client.py
import requests
from bs4 import BeautifulSoup

BASE = "https://aida.ebookingcenter.com"
LOGIN = f"{BASE}/tourOperator/login/"
PRICES_CAL = f"{BASE}/tourOperator/projects/services/servicePrices/Ajax.pricesCalendar.php"
DAY_DETAILS = f"{BASE}/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"

def login_aida(username: str, password: str) -> requests.Session:
    s = requests.Session()
    payload = {"username": username, "password": password}
    r = s.post(LOGIN, data=payload, allow_redirects=True, timeout=30)
    # success if redirected or page has logout
    if (r.url != LOGIN) or ("logout" in r.text.lower()):
        return s
    raise RuntimeError("AIDA login failed. Check credentials / form fields.")

def fetch_month_calendar(session: requests.Session, idProject: int, idService: int, serviceGroup: str = "AC") -> str:
    headers = {
        "Referer": f"{BASE}/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}&serviceGroup={serviceGroup}",
        "X-Requested-With": "XMLHttpRequest",
        "X-KL-ksospc-Ajax-Request": "Ajax_Request",
        "Accept": "text/html, */*; q=0.01",
    }
    r = session.get(PRICES_CAL, params={"refreshService": "1"}, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def fetch_day_html(session: requests.Session,
                   idProject: int,
                   idService: int,
                   serviceGroup: str,
                   date_iso: str,          # "YYYY-MM-DD"
                   idScheme: int,
                   priceSetId: int,
                   priceType: str = "supplierPrice") -> str:
    headers = {
        "Referer": f"{BASE}/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}&serviceGroup={serviceGroup}",
        "Origin": BASE,
        "X-Requested-With": "XMLHttpRequest",
        "X-KL-ksospc-Ajax-Request": "Ajax_Request",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "text/plain, */*; q=0.01",
    }
    data = {
        "idService": str(idService),
        "serviceGroup": serviceGroup,
        "priceType": priceType,      # "supplierPrice" or "resellerPrice"
        "date": date_iso,            # "YYYY-MM-DD"
        "idScheme": str(idScheme),
        "priceSetId": str(priceSetId),
    }
    r = session.post(DAY_DETAILS, headers=headers, data=data, timeout=30)
    r.raise_for_status()
    return r.text

def parse_day_html(html: str) -> dict:
    """
    Parse the HTML like the sample you sent and return:
    {
      "scheme": "Prices With TVA",
      "groups": [
        {"name": "Single - Standard Room", "items":[{"formula":"1*A","price":"29","currency":"USD"}, ...]},
        ...
      ]
    }
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out = {"scheme": None, "groups": []}

    # pricing scheme
    scheme_span = soup.find("span", class_="bold")
    if scheme_span:
        out["scheme"] = scheme_span.get_text(strip=True)

    # main container
    container = soup.find("div", class_="container-fluid")
    if not container:
        return out

    current = None

    # ✅ FIXED: BeautifulSoup does NOT support the '>' combinator
    # so we manually iterate through direct children
    for row in container.find_all("div", recursive=False):

        # 1️⃣ Header rows (bg-primary)
        header = row.find("div", class_="col")
        if header and "bg-primary" in header.get("class", []):
            title = header.get_text(strip=True)
            current = {"name": title, "items": []}
            out["groups"].append(current)
            continue

        # 2️⃣ Occupancy rows
        if "occupancy-row" in row.get("class", []):
            if current is None:
                current = {"name": "Room", "items": []}
                out["groups"].append(current)

            left = row.find("div", class_="col-6")
            rights = row.find_all("div", class_="col-6")

            formula_text = ""
            price_text = ""

            if left:
                formula_text = left.get_text(" ", strip=True)
                formula_text = " ".join(formula_text.replace("\xa0", " ").split())

            if rights:
                price_text = rights[-1].get_text(" ", strip=True)
                price_text = " ".join(price_text.split())

            # Extract price + currency
            price, currency = None, None
            if price_text:
                parts = price_text.split()
                if len(parts) >= 2:
                    currency = parts[-1]
                    price = parts[-2]

            if formula_text and price and currency:
                current["items"].append({
                    "formula": formula_text,
                    "price": price,
                    "currency": currency
                })

    return out
