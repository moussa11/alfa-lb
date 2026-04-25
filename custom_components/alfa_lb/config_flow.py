"""Config flow for Alfa Lebanon."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlfaApiError, AlfaAuthError, AlfaClient
from .const import CONF_MOBILE, CONF_PASSWORD, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MOBILE): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class AlfaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alfa Lebanon."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            mobile = user_input[CONF_MOBILE].strip()
            password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)
            client = AlfaClient(session, mobile, password)
            try:
                data = await client.async_validate()
            except AlfaAuthError:
                errors["base"] = "invalid_auth"
            except AlfaApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                unique = data.get("MobileNumberValue") or mobile
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Alfa {unique}",
                    data={CONF_MOBILE: mobile, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        mobile = entry.data[CONF_MOBILE]

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)
            client = AlfaClient(session, mobile, password)
            try:
                await client.async_validate()
            except AlfaAuthError:
                errors["base"] = "invalid_auth"
            except AlfaApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_PASSWORD: password}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"mobile": mobile},
        )
