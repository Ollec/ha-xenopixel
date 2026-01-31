"""Config flow for Xenopixel Lightsaber integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .xenopixel_ble import SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class XenopixelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xenopixel Lightsaber."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if self._discovery_info is None:
            return self.async_abort(reason="no_devices_found")

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or "Xenopixel Saber",
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_NAME: self._discovery_info.name,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or "Unknown",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            discovery_info = self._discovered_devices.get(address)
            name = discovery_info.name if discovery_info else "Xenopixel Saber"

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: name,
                },
            )

        # Scan for Xenopixel devices
        self._discovered_devices = {}
        for discovery_info in async_discovered_service_info(self.hass):
            # Check if this device has the Xenopixel service UUID
            if SERVICE_UUID.lower() in [
                str(uuid).lower() for uuid in discovery_info.service_uuids
            ]:
                self._discovered_devices[discovery_info.address] = discovery_info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Build selection list
        devices = {
            address: f"{info.name or 'Unknown'} ({address})"
            for address, info in self._discovered_devices.items()
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(devices),
                }
            ),
            errors=errors,
        )
