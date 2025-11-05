import streamlit as st
import requests
from bs4 import BeautifulSoup
from html import unescape

st.set_page_config(page_title="AIDA Day Prices", page_icon="🏨", layout="wide")

# ---------- Helpers ----------
def parse_services_list(html: str):
    """
    Parse the Services List page HTML (already loaded in your browser and pasted here).
    Returns a list of dicts: {idService, hotel, stars, status, raw_label}
    """
    soup = BeautifulSoup(html, "lxml")

    # each service is typically one table row <tr>…</tr>
    rows = soup.find_all("tr")
    services = []

    for tr in rows:
        # find the 'options' menu links which contain idService in URLs
        links = tr.find_all("a", href=True)
        id_service = None
        for a in links:
            href = a["href"]
            if "servicePrices/?" in href and "idService=" in href:
                # example: ...servicePrices/?idProject=194&idService=11400&serviceGroup=AC...
                try:
                    id_service = href.split("idService=", 1)[1].split("&", 1)[0]
                    break
                except Exception:
                    pass
        if not id_service:
            # try alternative button set (e.g., passengersList, capacities)
            for a in links:
                href = a["href"]
                if "idService=" in href:
                    try:
                        id_service = href.split("idService=", 1)[1].split("&", 1)[0]
                        break
                    except Exception:
                        pass
        if not id_service:
            # fallback: check data-url in buttons (popup)
            btns = tr.find_all(attrs={"data-url": True})
            for b in btns:
                u = b.get("data-url", "")
                if "idService=" in u:
                    try:
                        id_service = u.split("idService=", 1)[1].split("&", 1)[0]
                        break
                    except Exception:
                        pass
        if not id_service:
            continue

        # hotel name: from "Unit: <a>HOTEL</a>" or from first name cell
        hotel = None
        unit_li = tr.find("li", string=lambda s: isinstance(s, str) and "Unit:" in s)
        if unit_li:
            # if unit_li text is like "Unit:" then <a> follows
            a_unit = unit_li.find("a")
            if a_unit:
                hotel = a_unit.get_text(strip=True)
        if not hotel:
            # fallback: the second <td> (name cell) often contains the hotel name text
            name_td = tr.find("td")
            if name_td:
                t = name_td.get_text(" ", strip=True)
                # try to remove prefix like [DF]
                hotel = t.replace("[DF]", "").strip()
                # keep only first chunk before '—' if present
                hotel = hotel.split("  ")[0]

        # stars: count gold stars (text-warning)
        stars = len(tr.find_all("i", class_="text-warning"))
        # status:
        status = None
        on_sale_badge = tr.find(id=lambda x: x and x.startswith("serviceOnSaleStatus_"))
        if on_sale_badge:
            status = on_sale_badge.get_text(strip=True)
        if not status:
            # look for 'Status: Finalized' badge in the name cell
            finalized_badge = tr.find("div", class_="badge", string=lambda s: s and "Status:" in s)
            if finalized_badge:
                status = finalized_badge.get_text(strip=True).replace("Status:", "").strip()

        if not status:
            status = "Unknown"

        label = f"{hotel} — {stars}⭐ Hotel — ServiceID: {id_service} — {status}"
        services.append({
            "idService": id_service,
            "hotel": hotel,
            "stars": stars,
            "status": status,
            "label": label
        })

    return services


def fetch_day_details(cookies, idService, serviceGroup, priceType, date_yyyy_mm_dd, idScheme, priceSetId):
    """
    Calls the AIDA Ajax endpoint that returns the HTML popup for a given date.
    """
    url = "https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/Ajax.calendarDayDetails_AC.php"
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://aida.ebookingcenter.com",
        "Referer": f"https://aida.ebookingcenter.com/tourOperator/projects/services/servicePrices/?idService={idService}",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
    }
    data = {
        "idService": str(idService),
        "serviceGroup": serviceGroup,
        "priceType": priceType,
        "date": date_yyyy_mm_dd,
        "idScheme": str(idScheme),
        "priceSetId": str(priceSetId),
    }
    with requests.Session() as s:
        s.cookies.update(cookies)
        r = s.post(url, headers=headers, data=data, timeout=30)
        r.raise_for_status()
        return r.text


def parse_prices_popup(html: str):
    """
    Extract clean rows (Room Type / Occupancy / Price / Currency) from day popup HTML.
    """
    soup = BeautifulSoup(html, "lxml")
    out = []

    # each occupancy row looks like:
    # <div class="row py-2 occupancy-row ...">
    occ_rows = soup.select("div.occupancy-row")
    current_room_type = None

    # section headers (room type) are divs with class bg-primary
    # e.g., "SINGLE - STANDARD ROOM"
    def is_room_header(div):
        classes = div.get("class", [])
        return "bg-primary" in classes and "text-uppercase" in classes

    # walk through siblings in order: headers then occupancy rows
    container = soup.select_one("div.container-fluid")
    if not container:
        # fallback: just return raw html if structure changes
        return out

    for node in container.descendants:
        if getattr(node, "name", None) == "div" and is_room_header(node):
            current_room_type = node.get_text(strip=True).title()
        if getattr(node, "name", None) == "div" and "occupancy-row" in node.get("class", []):
            # left col: occupancy text like 1*A+1*C1
            left = node.select_one("div.col-6")
            right = node.select("div.col-6")[-1] if len(node.select("div.col-6")) >= 2 else None
            occ_txt = left.get_text(" ", strip=True) if left else ""
            price_txt = right.get_text(" ", strip=True) if right else ""

            # normalize price like "29 USD" or "45 USD"
            price_txt = " ".join(price_txt.split())
            out.append({
                "room_type": current_room_type or "",
                "occupancy": occ_txt,
                "price": price_txt
            })
    return out


def show_prices_table(rows):
    if not rows:
        st.warning("No prices parsed from popup.")
        return
    # simple table
    import pandas as pd
    df = pd.DataFrame(rows)
    df[["Price", "Currency"]] = df["price"].str.extract(r"(\d+(?:\.\d+)?)\s*([A-Za-z]+)")
    df = df.drop(columns=["price"])
    st.dataframe(df, use_container_width=True)


# ---------- UI ----------
st.markdown("## 🏨 AIDA: Pick Service by Hotel Name → Fetch Day Prices")

with st.expander("1) Paste *Services List* HTML (from AIDA)"):
    st.write("Open **Inventory → Project components → Services**. Copy the full page HTML (or `componentsList` inner HTML) and paste it here.")
    raw_services_html = st.text_area("Services List HTML", height=220, placeholder="Paste the HTML here...")

hotel_query = st.text_input("Hotel name filter (e.g., “Britannia Suites”)", "")

colA, colB = st.columns([1,1])
with colA:
    cookie_aidatour = st.text_input("Cookie: AIDAtourOperator", help="From your browser devtools > Application > Cookies")
with colB:
    cookie_aida = st.text_input("Cookie: AIDA", help="From your browser devtools > Application > Cookies")

col1, col2, col3 = st.columns([1,1,1])
with col1:
    service_group = st.selectbox("Service Group", ["AC"], index=0)
with col2:
    price_type = st.selectbox("Price Type", ["supplierPrice", "B1", "B2"], index=0)
with col3:
    date_val = st.text_input("Date (YYYY-MM-DD)", value="2025-11-05")

col4, col5 = st.columns([1,1])
with col4:
    id_scheme = st.text_input("idScheme", value="55565")
with col5:
    price_set_id = st.text_input("priceSetId", value="8520")

# Parse services
services = []
if raw_services_html.strip():
    try:
        services = parse_services_list(raw_services_html)
    except Exception as e:
        st.error(f"Parse error: {e}")

# Filter by hotel name if provided
if hotel_query.strip():
    q = hotel_query.strip().lower()
    services = [s for s in services if q in (s["hotel"] or "").lower()]

# Build dropdown
selected_service = None
if services:
    labels = [s["label"] for s in services]
    idx = st.selectbox("Choose a service", range(len(services)), format_func=lambda i: labels[i])
    selected_service = services[idx]
else:
    st.info("Paste the Services List HTML and/or type a hotel filter to see services.")

# Fetch button
st.markdown("---")
fetch_btn = st.button("🔎 Fetch Day Prices")

if fetch_btn:
    if not selected_service:
        st.error("Pick a service first.")
    elif not cookie_aidatour or not cookie_aida:
        st.error("Please paste both cookies (AIDAtourOperator and AIDA).")
    else:
        st.write(f"**Using:** {selected_service['label']}")
        cookies = {
            "AIDAtourOperator": cookie_aidatour,
            "AIDA": cookie_aida
        }
        try:
            html = fetch_day_details(
                cookies=cookies,
                idService=selected_service["idService"],
                serviceGroup=service_group,
                priceType=price_type,
                date_yyyy_mm_dd=date_val,
                idScheme=id_scheme,
                priceSetId=price_set_id
            )
            st.caption("✅ RAW HTML RESPONSE (popup) — collapsed")
            with st.expander("Show raw HTML"):
                st.code(unescape(html), language="html")

            rows = parse_prices_popup(html)
            st.success(f"Parsed {len(rows)} price rows.")
            show_prices_table(rows)
        except requests.HTTPError as he:
            st.error(f"HTTP error: {he}")
        except Exception as e:
            st.error(f"Failed: {e}")
