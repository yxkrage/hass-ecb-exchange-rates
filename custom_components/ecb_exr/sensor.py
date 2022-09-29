"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import datetime

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    PLATFORM_SCHEMA)

from homeassistant.const import CONF_TYPE, ATTR_FRIENDLY_NAME
from .ExchangeRate import ExchangeRate, get_exchange_rate_obj
from .const import (DOMAIN, CONF_CURRENCY, CONF_CURRENCIES, EVENT_NAME, 
                    EVENT_TYPE_DATA_UPDATED)

_LOGGER = logging.getLogger(__name__)


# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
#     {
#         vol.Optional(ATTR_FRIENDLY_NAME): cv.string
#     }
# )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""

    currencies = hass.data[DOMAIN][CONF_CURRENCIES]
    for currency in currencies:
        pa = get_exchange_rate_obj(hass, currency)
        sensor = EcbExrSensor(pa)
        add_entities([sensor], True)


class EcbExrSensor(SensorEntity):
    """Ecb Exchange Rate Sensor. Showing the currency exchange rate between the EUR
    and the selected currency"""
    
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, exchange_rate_obj: ExchangeRate):
        super().__init__()
        self._exchange_rate_obj = exchange_rate_obj
        _LOGGER.debug(f"Sensor '{self.name}' ({self.currency}) created")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _LOGGER.debug(f"Sensor '{self.name}' ({self.currency}) added to Hass")

        # Call 'update_callback' function every hour, on the hour
        async_track_time_change(self._hass, 
                                self.update_callback,
                                hour=0,
                                minute=0,
                                second=0)

        # Listen for event and update sensor
        self._hass.bus.async_listen(EVENT_NAME, self.handle_event)
    
    @property
    def _hass(self):
        return self._exchange_rate_obj._hass

    @property
    def name(self) -> str:
        return f"Exchange Rate {self.currency} to {self.currency_denom}"

    @property
    def currency(self) -> str:
        return self._exchange_rate_obj.currency

    @property
    def currency_denom(self) -> str:
        return self._exchange_rate_obj.currency_denom

    @property
    def _attr_unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{DOMAIN}_{self.currency.lower()}_to_{self.currency_denom.lower()}"

    @property
    def _attr_native_unit_of_measurement(self):
        return f'{self.currency}/{self.currency_denom}'

    def _update_data(self):
        if self._exchange_rate_obj._data:
            self._attr_native_value = self._exchange_rate_obj.exchange_rate
            self._attr_extra_state_attributes = {'date': self._exchange_rate_obj.date}
            _LOGGER.debug(f"Sensor '{self.name}' ({self.currency}) updated")
        else:
            # Data not available
            self._attr_native_value = None
            _LOGGER.warning(f"No data found for sensor '{self.name}' when trying to update")

    async def async_update(self) -> None:
        self._update_data()

    @callback
    async def update_callback(self, _: datetime) -> None:
        _LOGGER.debug(f"Sensor: Update requested from Callback for '{self.currency}'")
        self._update_data()
        self.async_schedule_update_ha_state()

    def handle_event(self, event):
        # Check that event is for this sensor
        if event.data.get(CONF_TYPE) == EVENT_TYPE_DATA_UPDATED and \
           event.data.get(CONF_CURRENCY) == self.currency:
            _LOGGER.debug(f"Event captured: '{EVENT_NAME}' is of type '{EVENT_TYPE_DATA_UPDATED}' and for currency '{self.currency}'")
            self._update_data()
            self.async_schedule_update_ha_state()
        else:
            _LOGGER.debug(f"Event ignored: '{EVENT_NAME}' is of type '{EVENT_TYPE_DATA_UPDATED}'")
