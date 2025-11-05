def find_service_by_name(session: requests.Session, idProject: int, hotel_name: str):
    """
    Returns: { 'serviceId': int, 'serviceGroup': str }
    Or None if not found.
    """

    url = f"{BASE}/tourOperator/projects/services/servicesList/"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/tourOperator/projects/projectDetails/services/?idProject={idProject}",
        "User-Agent": "Mozilla/5.0"
    }

    data = {
        "idProject": idProject,
        "currentTab": "0"
    }

    r = session.post(url, headers=headers, data=data)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.find_all("tr")

    hotel_name = hotel_name.lower().strip()

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # Hotel name appears in first big <td>, inside <div>
        big_td = cols[1].get_text(" ", strip=True).lower()

        if hotel_name in big_td:
            # Extract idService from the action buttons
            link = cols[1].find("a", href=True)
            if link and "idService=" in link["href"]:
                idService = int(link["href"].split("idService=")[1].split("&")[0])
                group = cols[2].get_text(strip=True)
                return {
                    "serviceId": idService,
                    "serviceGroup": group
                }

    return None
