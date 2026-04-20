"""Planning applications scraper for East Dunbartonshire (Idox portal)."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

_IDOX_BASE = "https://planning.eastdunbarton.gov.uk/online-applications"
_POSTCODES_IO = "https://api.postcodes.io"
_SEARCH_DAYS = 90
DEFAULT_RADIUS_M = 500

_UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b", re.IGNORECASE)


@dataclass
class PlanningApplication:
    reference: str
    address: str
    description: str
    date_received: date | None
    status: str
    url: str
    distance_m: int | None = None


@dataclass
class PlanningData:
    applications: list[PlanningApplication] = field(default_factory=list)
    search_radius_m: int = DEFAULT_RADIUS_M


class PlanningCoordinator(DataUpdateCoordinator[PlanningData]):
    def __init__(
        self, hass: HomeAssistant, home_postcode: str, radius_m: int = DEFAULT_RADIUS_M
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="east_dunbartonshire_planning",
            update_interval=timedelta(hours=4),
        )
        self.session = async_get_clientsession(hass)
        self._home_postcode = home_postcode
        self._radius_m = radius_m
        self._home_lat: float | None = None
        self._home_lng: float | None = None

    async def _async_update_data(self) -> PlanningData:
        try:
            if self._home_lat is None:
                self._home_lat, self._home_lng = await _geocode_postcode(
                    self.session, self._home_postcode
                )
            home_lat: float = self._home_lat
            home_lng: float = self._home_lng  # type: ignore[assignment]
            return await _fetch_planning(self.session, home_lat, home_lng, self._radius_m)
        except Exception as err:
            raise UpdateFailed(f"Error fetching planning applications: {err}") from err


async def _geocode_postcode(session, postcode: str) -> tuple[float, float]:
    url = f"{_POSTCODES_IO}/postcodes/{postcode.replace(' ', '%20')}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    r = data["result"]
    return r["latitude"], r["longitude"]


async def _fetch_planning(session, home_lat: float, home_lng: float, radius_m: int) -> PlanningData:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=_SEARCH_DAYS)
    params = {
        "searchType": "Application",
        "date(applicationReceivedStart)": start_dt.strftime("%d/%m/%Y"),
        "date(applicationReceivedEnd)": end_dt.strftime("%d/%m/%Y"),
        "searchCriteria.caseStatus": "ALL",
        "action": "firstPage",
        "searchCriteria.page": "1",
    }
    async with session.get(f"{_IDOX_BASE}/advancedSearchResults.do", params=params) as resp:
        resp.raise_for_status()
        html = await resp.text()

    applications = _parse_results(html)

    # Batch-geocode unique postcodes found in application addresses
    postcodes = [_extract_postcode(app.address) for app in applications]
    unique = list({p for p in postcodes if p})
    coords_map = await _bulk_geocode(session, unique) if unique else {}

    nearby = []
    for app, pc in zip(applications, postcodes):
        if not pc or pc not in coords_map:
            continue
        lat, lng = coords_map[pc]
        dist = _haversine_m(home_lat, home_lng, lat, lng)
        if dist <= radius_m:
            app.distance_m = round(dist)
            nearby.append(app)

    nearby.sort(key=lambda a: a.date_received or date.min, reverse=True)
    return PlanningData(applications=nearby, search_radius_m=radius_m)


def _parse_results(html: str) -> list[PlanningApplication]:
    applications = []
    for block in re.findall(
        r'<li[^>]*class="[^"]*searchresult[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL
    ):
        meta_m = re.search(r'class="metaInfo"[^>]*>(.*?)</p>', block, re.DOTALL)
        addr_m = re.search(r'class="address"[^>]*>(.*?)</p>', block, re.DOTALL)
        link_m = re.search(
            r'href="([^"]*applicationDetails[^"]*)"[^>]*>(.*?)</a>', block, re.DOTALL
        )
        if not (meta_m and link_m):
            continue

        meta = re.sub(r"<[^>]+>", "", meta_m.group(1)).strip()
        description = re.sub(r"<[^>]+>", "", link_m.group(2)).strip()
        address = re.sub(r"<[^>]+>", "", addr_m.group(1)).strip() if addr_m else ""

        reference = ""
        date_received: date | None = None
        status = ""
        for part in meta.split("|"):
            part = part.strip()
            if part.startswith("Ref. No:"):
                reference = part[len("Ref. No:") :].strip()
            elif part.startswith("Received:"):
                raw = re.sub(r"^[A-Za-z]{3}\s+", "", part[len("Received:") :].strip())
                try:
                    date_received = datetime.strptime(raw, "%d %b %Y").date()
                except ValueError:
                    pass
            elif part.startswith("Status:"):
                status = part[len("Status:") :].strip()

        url = link_m.group(1).strip()
        if not url.startswith("http"):
            url = f"https://planning.eastdunbarton.gov.uk{url}"

        applications.append(
            PlanningApplication(
                reference=reference,
                address=address,
                description=description,
                date_received=date_received,
                status=status,
                url=url,
            )
        )
    return applications


async def _bulk_geocode(session, postcodes: list[str]) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    for i in range(0, len(postcodes), 100):
        batch = postcodes[i : i + 100]
        async with session.post(f"{_POSTCODES_IO}/postcodes", json={"postcodes": batch}) as resp:
            resp.raise_for_status()
            data = await resp.json()
        for item in data.get("result", []):
            if item.get("result"):
                r = item["result"]
                result[item["query"]] = (r["latitude"], r["longitude"])
    return result


def _extract_postcode(address: str) -> str | None:
    m = _UK_POSTCODE_RE.search(address)
    if not m:
        return None
    pc = m.group(1).upper().replace(" ", "")
    return f"{pc[:-3]} {pc[-3:]}"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))
