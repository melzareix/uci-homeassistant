"""Sensor platform for UCI Kinowelt showtimes."""

from datetime import timedelta, date
import logging

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, SCAN_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)

URL = (
    "https://www.uci-kinowelt.de/kinoprogramm/{cinema_name}/{cinema_id}/list"
    "?date={date}&version=ov"
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    cinema_name = entry.data["cinema_name"]
    cinema_id = entry.data["cinema_id"]

    coordinator = UciDataCoordinator(hass, cinema_name, cinema_id)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([UciShowtimesSensor(coordinator, entry)])


class UciDataCoordinator(DataUpdateCoordinator):
    """Fetch and parse UCI showtimes."""

    def __init__(self, hass: HomeAssistant, cinema_name: str, cinema_id: str):
        super().__init__(
            hass,
            _LOGGER,
            name=f"UCI {cinema_name}",
            update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
        )
        self.cinema_name = cinema_name
        self.cinema_id = cinema_id

    async def _async_update_data(self):
        today = date.today().strftime("%Y%m%d")
        url = URL.format(cinema_name=self.cinema_name, cinema_id=self.cinema_id, date=today)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                resp.raise_for_status()
                html = await resp.text()

        return await self.hass.async_add_executor_job(self._parse, html, today)

    def _parse(self, html: str, target_date: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        title_links = soup.select("h2 a[href*='/film/']")

        ov_tags = {"ov", "omu", "omeu"}
        known_tags = {"ov", "omu", "omeu", "2d", "3d", "imax", "screenx", "isens", "isense"}
        results = []

        for title_el in title_links:
            title = title_el.get_text(strip=True)
            container = title_el.find_parent("div", class_="film-container-wrapper")
            if not container:
                continue

            badges = container.select(f'a.badge-performance[data-date="{target_date}"]')
            if not badges:
                continue

            showtimes = []
            for badge in badges:
                time = badge.get("data-time", "")
                version = badge.get("data-version", "")
                parts = [v.lower() for v in version.split("|") if v]
                if not ov_tags.intersection(parts):
                    continue
                version_parts = [v.upper() for v in parts if v in known_tags]
                showtimes.append({"time": time, "tags": version_parts})

            if showtimes:
                results.append({"title": title, "showtimes": showtimes})

        return results


class UciShowtimesSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing number of OV/OmU movies today, with full data in attributes."""

    def __init__(self, coordinator: UciDataCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"uci_{entry.data['cinema_id']}_ov_showtimes"
        self._attr_name = f"UCI {entry.data['cinema_name']} OV Showtimes"
        self._attr_icon = "mdi:movie-open"

    @property
    def native_value(self):
        if self.coordinator.data:
            return len(self.coordinator.data)
        return 0

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {"movies": []}
        return {
            "movies": self.coordinator.data,
            "date": date.today().isoformat(),
        }
