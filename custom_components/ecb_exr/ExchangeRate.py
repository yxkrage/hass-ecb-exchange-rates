import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import track_time_change
from homeassistant.const import CONF_TYPE

from datetime import datetime, date, timedelta
from .ecb_exr import get_exchange_rate, EcbException
from .const import (DOMAIN, CONF_CURRENCY, FREQ, DAYS_LOOK_BACK, DAYS_LOOK_AHEAD,
                    CONST_HOUR, CONST_MINUTE, CONST_SECOND, POLL_API_TIME_PATTERN,
                    EVENT_NAME, EVENT_TYPE_DATA_UPDATED)

_LOGGER = logging.getLogger(__name__)


class ExchangeRate():
    exchange_rate = None
    date = None
    _data = None

    def __init__(self, hass: HomeAssistant, currency, currency_demon) -> None:
        self._hass = hass
        self.currency = currency
        self.currency_denom = currency_demon

        self._hass.async_add_executor_job(self.update_from_api)

        track_time_change(hass, 
                          self.update_from_api_callback, 
                          hour=POLL_API_TIME_PATTERN.get(CONST_HOUR, None), 
                          minute=POLL_API_TIME_PATTERN.get(CONST_MINUTE, None), 
                          second=POLL_API_TIME_PATTERN.get(CONST_SECOND, None))
        _LOGGER.debug(f"ExchangeRate object created for area '{self.currency}'")


    def update_from_api(self):
        try:
            # self._data = await async_get_exchange_rate(self._hass, self.currency, 
            self._data = get_exchange_rate(self.currency, 
                                 self.currency_denom,
                                 FREQ,
                                 date.today()-timedelta(days=DAYS_LOOK_BACK),
                                 date.today()+timedelta(days=DAYS_LOOK_AHEAD))
        
            self.exchange_rate, self.date = self._get_effective_rate(self._data)
            self._hass.states.set(f"{DOMAIN}.{self.currency}", "ok")
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
    def update_from_api_callback(self, _: datetime) -> None:
        _LOGGER.debug(f"Exchange Rate object: Update requested from Callback for '{self.currency}'")
        self.update_from_api()
        self._hass.async_add_executor_job(self.update_from_api)


def get_exchange_rate_obj(hass, currency) -> ExchangeRate | None:
    for c in hass.data[DOMAIN][CONF_CURRENCY]:
        if c.currency == currency:
            return c
    return None
