import requests
import xml.etree.ElementTree as et
from datetime import date


REQUEST_URL = "https://sdw-wsrest.ecb.europa.eu/service/data/EXR/"
EXR_TYPE = "SP00"
EXR_SUFFIX = "A"
PARM_NAME_PERIOD_START = "startPeriod"
PARM_NAME_PERIOD_END = "endPeriod"

XML_NS_MESSAGE = "message"
XML_NS_COMMON = "common"
XML_NS_XSI = "xsi"
XML_NS_GENERIC = "generic"

NS = {
    XML_NS_MESSAGE: "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    XML_NS_COMMON: "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    XML_NS_XSI: "http://www.w3.org/2001/XMLSchema-instance",
    XML_NS_GENERIC: "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"
}

ATTRS_INCLUDE = ['freq', 'currency', 'currency_denom', 'decimals', 'title_compl', 'title']
ATTRS_EXCLUDE = []

class EcbException(Exception):
    def __init__(self, message=None):
        self.message = message
        super().__init__(self.message)


class EcbHttpException(EcbException):
    def __init__(self,
                 status_code: int,
                 message: str = None):
        self.status_code = status_code
        self.message = f"Error calling API - HTTP Response Code: '{status_code}'."
        if message is not None:
            self.message += f" Message: '{message}'."
        super().__init__(self.message)


class EcbParseException(EcbException):
    def __init__(self, message: str = "Unspecified error", original_error: Exception = None):
        self.message = f"Error parsing response: {message}"
        self.original_error = original_error
        super().__init__(self.message)


class EcbParseTagNotFoundException(EcbParseException):
    def __init__(self, tag_name: str):
        super().__init__(f"Unable to find tag '{tag_name}'")


def build_query_str(currency: str,
                    currency_denom: str,
                    freq: str,
                    date_from: date = None,
                    date_to: date = None
                    ) -> str:
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from

    return f"{freq}.{currency}.{currency_denom}.{EXR_TYPE}.{EXR_SUFFIX}?" +\
           f"{PARM_NAME_PERIOD_START}={date_from:%Y-%m-%d}&{PARM_NAME_PERIOD_END}={date_to:%Y-%m-%d}"


def call_api(query_str: str) -> requests:
    resp = requests.request("GET", f"{REQUEST_URL}{query_str}")
    return resp


def parse_response(response: requests.Response):

    def find(element: et, tag: str) -> et:
        el = element.find(tag, NS)
        if el is None:
            raise EcbParseTagNotFoundException(tag)
        return el

    def parse_generic_list(parent_tag, search_name):
        for tag_value in parent_tag.findall(f"{search_name}/{XML_NS_GENERIC}:Value", NS):
            id = tag_value.attrib.get('id').lower()
            # Check that attribute should be included
            if (id in ATTRS_INCLUDE or len(ATTRS_INCLUDE) == 0) and \
                id not in ATTRS_EXCLUDE:
                    ret_struct[id] = tag_value.attrib.get('value')

    # Check that status code is 200
    if response.status_code != 200:
        # Raise error with message from response body
        raise EcbHttpException(response.status_code, response.text)

    # Check that response contains data
    if response.text is None or response.text == '':
        # Raise error if response contains no data
        raise EcbHttpException(response.status_code, "Response contains no data")

    # Parse response XML
    ret_struct = {}
    try:
        root = et.fromstring(response.text)
    except et.ParseError as e:
        raise EcbParseException(e.msg, e)

    # Get data from XML
    tag_data_set = find(root, f"{XML_NS_MESSAGE}:DataSet")
    ret_struct['valid_from_date'] = tag_data_set.attrib.get('validFromDate')

    tag_series = find(tag_data_set, f"{XML_NS_GENERIC}:Series")

    # Get series keys
    parse_generic_list(tag_series, f"{XML_NS_GENERIC}:SeriesKey")

    # Get attribute data
    parse_generic_list(tag_series, f"{XML_NS_GENERIC}:Attributes")

    # Get exchange rates
    ret_ex_rates = {}
    for obs in tag_series.findall(f"{XML_NS_GENERIC}:Obs", NS):
        obs_dim = find(obs, f"{XML_NS_GENERIC}:ObsDimension")
        obs_val = find(obs, f"{XML_NS_GENERIC}:ObsValue")
        ret_ex_rates[obs_dim.attrib.get('value')] = float(obs_val.attrib.get('value'))

    ret_struct['exchange_rates'] = ret_ex_rates
    return ret_struct


def get_exchange_rate(currency: str,
                      currency_denom: str,
                      freq: str,
                      date_from: date = None,
                      date_to: date = None):
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from

    qs = build_query_str(currency, currency_denom, freq, date_from, date_to)
    resp = call_api(qs)
    return parse_response(resp)
