"""Support for freedompro."""
from datetime import timedelta
import logging

from pyfreedompro import get_list, get_states

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "cover", "light", "lock", "sensor", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Freedompro from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    api_key = entry.data[CONF_API_KEY]

    coordinator = FreedomproDataUpdateCoordinator(hass, api_key)
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class FreedomproDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Freedompro data API."""

    def __init__(self, hass, api_key):
        """Initialize."""
        self._hass = hass
        self._api_key = api_key
        self._devices = None

        update_interval = timedelta(minutes=1)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        if self._devices is None:
            result = await get_list(
                aiohttp_client.async_get_clientsession(self._hass), self._api_key
            )
            if result["state"]:
                self._devices = result["devices"]
            else:
                raise UpdateFailed()

        result = await get_states(
            aiohttp_client.async_get_clientsession(self._hass), self._api_key
        )

        for device in self._devices:
            dev = next(
                (dev for dev in result if dev["uid"] == device["uid"]),
                None,
            )
            if dev is not None and "state" in dev:
                device["state"] = dev["state"]
        return self._devices
