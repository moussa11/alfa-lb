"""DataUpdateCoordinator for Alfa Lebanon."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AlfaApiError, AlfaAuthError, AlfaClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AlfaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the Alfa portal."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: AlfaClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_account_data()
        except AlfaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AlfaApiError as err:
            raise UpdateFailed(f"Error fetching Alfa data: {err}") from err
