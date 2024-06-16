import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import BASE_CURRENCY, CONF_CURRENCIES, CONF_CURRENCY, DOMAIN
from .ExchangeRate import ExchangeRate, get_exchange_rate_obj

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CURRENCIES): cv.ensure_list(cv.string)
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config):
# def setup(hass: HomeAssistant, config):

    # def handle_get_exchange_rates(call):
    async def async_handle_get_exchange_rates(call):
        """Handle the service call."""
        tmp = call.data.get(CONF_CURRENCIES)
        if isinstance(tmp, str):
            currencies = [tmp]
        elif isinstance(tmp, list):
            currencies = tmp
        else:
            currencies = []

        _LOGGER.debug(f"Service 'get_exchange_rates' called for area '{currencies}'")

        # Get new exchange rate data from API
        for currency in currencies:
            co = get_exchange_rate_obj(hass, currency)
            if co:
                # co.update_from_api()
                await co.async_update_from_api()
            else:
                _LOGGER.error(
                    f"Exchange Rate data cannot be retrieved for price area '{currency}' " +\
                    "because it is not setup in 'configuration.yaml'. Add to " +\
                    f"'{CONF_CURRENCIES}:' under '{DOMAIN}:'."
                )


    # Setup integration
    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.info(f"No configuration for '{DOMAIN}' found")
        return True

    currencies = conf.get(CONF_CURRENCIES)

    hass.data[DOMAIN] = {
        CONF_CURRENCIES: currencies,
        CONF_CURRENCY: []
    }

    # Register service
    hass.services.async_register(DOMAIN, "get_data", async_handle_get_exchange_rates)
    #hass.services.register(DOMAIN, "get_data", handle_get_exchange_rates)

    # Create on Exchange Rate object for each currency in
    # config and add it to hass
    for currency in currencies:
        cur_obj = ExchangeRate(hass, currency, BASE_CURRENCY)
        hass.data[DOMAIN][CONF_CURRENCY].append(cur_obj)
        _LOGGER.info(f"Exchange Rate for '{currency}' setup")

    # Manually trigger the update to test
    # await cur_obj.async_update_from_api()

    return True

