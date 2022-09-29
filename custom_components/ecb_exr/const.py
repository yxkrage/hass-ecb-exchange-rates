DOMAIN = "ecb_exr"
CONF_CURRENCIES = 'currencies'
CONF_CURRENCY = 'currency'

EVENT_NAME = f"{DOMAIN}_event"
EVENT_TYPE_DATA_UPDATED = "data_updated"

# Functional Parameters
BASE_CURRENCY = 'EUR'
FREQ = 'D'
DAYS_LOOK_BACK = 5
DAYS_LOOK_AHEAD = 1

# Other constants
CONST_HOUR = 'hour'
CONST_MINUTE = 'minute'
CONST_SECOND = 'second'

POLL_API_TIME_PATTERN = {
    #CONST_HOUR: 21,
    #CONST_MINUTE: 17,
    #CONST_SECOND: [0, 10, 20, 30, 40, 50]
    CONST_HOUR: 0,
    CONST_MINUTE: 0,
    CONST_SECOND: 0
}