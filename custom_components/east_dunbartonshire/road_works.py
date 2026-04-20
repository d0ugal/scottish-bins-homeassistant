"""Scottish Road Works Register (SRWR) data for East Dunbartonshire."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

_SRWR_DAILY_URL = "https://downloads.srwr.scot/export/daily/"
_ED_AUTHORITY = "East Dunbartonshire"

# Works that are expected to be present today
_ACTIVE_STATUSES = {
    "In Progress",
    "Proposed",
    "Immediate - Urgent",
    "Immediate - Emergency",
}


@dataclass
class RoadWork:
    reference: str
    street_name: str
    area: str
    promoter: str
    works_type: str
    start_date: date | None
    end_date: date | None
    status: str
    description: str


@dataclass
class RoadWorksData:
    active: list[RoadWork] = field(default_factory=list)
    upcoming: list[RoadWork] = field(default_factory=list)


class RoadWorksCoordinator(DataUpdateCoordinator[RoadWorksData]):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="east_dunbartonshire_road_works",
            update_interval=timedelta(hours=12),
        )
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> RoadWorksData:
        try:
            return await _fetch_road_works(self.session)
        except Exception as err:
            raise UpdateFailed(f"Error fetching road works: {err}") from err


async def _fetch_road_works(session) -> RoadWorksData:
    zip_url = await _find_daily_zip(session)
    async with session.get(zip_url) as resp:
        resp.raise_for_status()
        raw = await resp.read()

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        csv_name = next((n for n in zf.namelist() if n.endswith(".csv")), None)
        if not csv_name:
            raise UpdateFailed("No CSV found in SRWR daily ZIP")
        csv_bytes = zf.read(csv_name)

    rows = _parse_csv(csv_bytes.decode("utf-8-sig", errors="replace"))

    today = datetime.now().date()
    active: list[RoadWork] = []
    upcoming: list[RoadWork] = []

    for row in rows:
        if (
            row.start_date
            and row.start_date <= today
            and (row.end_date is None or row.end_date >= today)
        ):
            active.append(row)
        elif row.start_date and row.start_date > today:
            upcoming.append(row)

    active.sort(key=lambda r: r.start_date or date.min)
    upcoming.sort(key=lambda r: r.start_date or date.min)
    return RoadWorksData(active=active, upcoming=upcoming[:20])


async def _find_daily_zip(session) -> str:
    async with session.get(_SRWR_DAILY_URL) as resp:
        resp.raise_for_status()
        html = await resp.text()

    import re

    matches = re.findall(r'href="([^"]*\.zip)"', html, re.IGNORECASE)
    if not matches:
        raise UpdateFailed("No ZIP file found at SRWR daily export listing")
    url = matches[-1]
    if not url.startswith("http"):
        url = f"https://downloads.srwr.scot{url}"
    return url


def _parse_csv(text: str) -> list[RoadWork]:
    works = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        authority = _col(row, "highway_authority", "promoter_organisation", "works_authority")
        if _ED_AUTHORITY.lower() not in authority.lower():
            continue

        start = _parse_date(_col(row, "works_start_date", "date_of_works", "start_date"))
        end = _parse_date(_col(row, "works_end_date", "end_date", "date_of_completion"))
        works.append(
            RoadWork(
                reference=_col(row, "works_reference_number", "reference", "work_ref"),
                street_name=_col(row, "street_name", "road_name", "street"),
                area=_col(row, "town", "location", "area"),
                promoter=_col(row, "promoter_organisation", "works_promoter", "promoter"),
                works_type=_col(row, "activity_type", "works_type", "work_type"),
                start_date=start,
                end_date=end,
                status=_col(row, "works_status", "status"),
                description=_col(row, "works_description", "description", "proposed_works"),
            )
        )
    return works


def _col(row: dict, *keys: str) -> str:
    for key in keys:
        val = row.get(key, "").strip()
        if val:
            return val
        # case-insensitive fallback
        for k, v in row.items():
            if k.lower() == key.lower() and v.strip():
                return v.strip()
    return ""


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None
