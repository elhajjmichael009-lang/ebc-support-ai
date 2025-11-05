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
    # success if redirected away from login OR page shows 'logout'
    if (r.url != LOGIN) or ("logout" in r.text.lower()):
        return s
    raise RuntimeError("AIDA login failed. Check credentials / fields.")

def fetch_month_calendar(session: requests.Session, idProject: int, idService: int, serviceGroup: str = "AC") -> str:
    """
    Returns the month calendar HTML (big grid). Useful later to auto-find idScheme/priceSetId.
    The referer matters; AIDA checks it. We set it via headers.
    """
    headers = {
        "Referer": f"{BASE}/tourOperator/projects/services/servicePrices/?idProject={idProject}&idService={idService}&serviceGroup={serviceGroup}",
        "X-Requested-With": "XMLHttpRequest",
        "X-KL-ksospc-Ajax-Request": "Ajax_Request",
        "Accept": "text/html, */*; q=0.01",
    }
    r = session.get(PRICES_CAL, params={"refreshService": "1"}, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text  # HTML

def fetch_day_prices(session: requests.Session,
                     idProject: int,
                     idService: int,
                     serviceGroup: str,
                     date_iso: str,          # e.g. "2025-11-05"
                     idScheme: int,
                     priceSetId: int,
                     priceType: str = "supplierPrice") -> dict:
    """
    Calls the same endpoint your browser hits when you click a date.
    Returns a structured dict with (category -> list of (formula, price, currency)).
    """
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
        "priceType": priceType,      # "supplierPrice" or "resellerPrice" etc.
        "date": date_iso,            # "YYYY-MM-DD"
        "idScheme": str(idScheme),
        "priceSetId": str(priceSetId),
    }
    r = session.post(DAY_DETAILS, headers=headers, data=data, timeout=30)
    r.raise_for_status()
    html = r.text

    # ---- parse the popup HTML (like your screenshot) ----
    soup = BeautifulSoup(html, "html.parser")
    out = {"date": date_iso, "groups": []}

    # group headers look like "SINGLE - STANDARD ROOM", etc.
    # then multiple rows with formula and price "29 USD"
    current_group = None
    for el in soup.select("*"):
        txt = (el.get_text(strip=True) or "")
        # detect section header
        if txt and txt.isupper() and ("ROOM" in txt or "APARTMENT" in txt or "SUITE" in txt):
            current_group = {"name": txt, "items": []}
            out["groups"].append(current_group)
            continue
        # detect price lines like "1A+1C1 — 29 USD"
        if current_group and txt and ("USD" in txt or "EUR" in txt or "LBP" in txt):
            # Often price is alone in a sibling node; we try to split last token as "PRICE CURRENCY"
            parts = txt.split()
            # simple heuristic: last two tokens form price+currency
            if len(parts) >= 2:
                currency = parts[-1]
                price = parts[-2]
                formula = " ".join(parts[:-2]).strip() or "N/A"
                current_group["items"].append({"formula": formula, "price": price, "currency": currency})

    return out
