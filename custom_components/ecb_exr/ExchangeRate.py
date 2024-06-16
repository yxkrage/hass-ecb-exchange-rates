from datetime import date, datetime, timedelta
import logging

from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change, track_time_change

from .const import (
    CONF_CURRENCY,
    CONST_HOUR,
    CONST_MINUTE,
    CONST_SECOND,
    DAYS_LOOK_AHEAD,
    DAYS_LOOK_BACK,
    DOMAIN,
    EVENT_NAME,
    EVENT_TYPE_DATA_UPDATED,
    FREQ,
    POLL_API_TIME_PATTERN,
)
from .ecb_exr import EcbException, async_get_exchange_rate

_LOGGER = logging.getLogger(__name__)


class ExchangeRate:
    _data = None
    exchange_rate = None
    date = None
    updated_at = None

    def __init__(self, hass: HomeAssistant, currency, currency_demon) -> None:
        self._hass = hass
        self.currency = currency
        self.currency_denom = currency_demon

        self._hass.async_create_task(self.async_update_from_api())

        async_track_time_change(
            hass,
            # self.update_from_api_callback,
            self.async_update_from_api_callback,
            hour=POLL_API_TIME_PATTERN.get(CONST_HOUR, None),
            minute=POLL_API_TIME_PATTERN.get(CONST_MINUTE, None),
            second=POLL_API_TIME_PATTERN.get(CONST_SECOND, None)
        )

        _LOGGER.debug(f"ExchangeRate object created for area '{self.currency}'")

    def _schedule_periodic_update(self):
        """Schedule periodic updates using track_time_change."""
        def schedule_update():
            track_time_change(
                self._hass,
                self.update_from_api_callback,
                hour=POLL_API_TIME_PATTERN.get(CONST_HOUR),
                minute=POLL_API_TIME_PATTERN.get(CONST_MINUTE),
                second=POLL_API_TIME_PATTERN.get(CONST_SECOND)
            )
        self._hass.loop.call_soon_threadsafe(schedule_update)

    # def update_from_api(self):
    async def async_update_from_api(self):
        try:
            self._data = await async_get_exchange_rate(
                self.currency,
                self.currency_denom,
                FREQ,
                date.today()-timedelta(days=DAYS_LOOK_BACK),
                date.today()+timedelta(days=DAYS_LOOK_AHEAD)
            )

            self.exchange_rate, self.date = self._get_effective_rate(self._data)
            self.updated_at = datetime.now()
            # self._hass.states.set(f"{DOMAIN}.{self.currency}", "ok")
            self._hass.states.async_set(f"{DOMAIN}.{self.currency}", "ok")
            _LOGGER.info(f"Exchange rate for {self.currency} successfully retrieved from API.")

        except EcbException as e:
            self._hass.states.set(f"{DOMAIN}.{self.currency}", "error")
            _LOGGER.error(e.message, e)

        # Fire Event to signal that data is updated
        event_data = {
            CONF_TYPE: EVENT_TYPE_DATA_UPDATED,
            CONF_CURRENCY: self.currency
        }
        self._hass.bus.async_fire(EVENT_NAME, event_data)

    def _get_effective_rate(self, data):
        rates = data.get('exchange_rates', None)
        if rates is None:
            return None

        d = None
        r = None
        for rate in rates.keys():
            tmp_d = datetime.strptime(rate, '%Y-%m-%d').date()
            if (d is None or tmp_d > d):
                d = tmp_d
                r = float(rates.get(rate))
        _LOGGER.debug(f"Determined effective rate for '{self.currency}' to be '{r}' for '{d}'")
        return (r, d)

    @callback
    # def update_from_api_callback(self, _: datetime) -> None:
    async def async_update_from_api_callback(self, _: datetime) -> None:
        _LOGGER.debug(f"Exchange Rate object: Update requested from Callback for '{self.currency}'")
        self._hass.async_create_task(self.async_update_from_api())


def get_exchange_rate_obj(hass: HomeAssistant, currency: str) -> ExchangeRate | None:
    for c in hass.data[DOMAIN][CONF_CURRENCY]:
        if c.currency == currency:
            return c
    return None
