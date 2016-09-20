#
# An interface for building requests to Amazon's MWS API
#
# Based on python-amazon-mws: https://github.com/czpython/python-amazon-mws/
#

import urllib
import hmac
import requests

from time import strftime, gmtime
from base64 import b64encode
from hashlib import sha256, md5


ENDPOINTS = {'NA': 'mws.amazonservices.com',
             'EU': 'mws-eu.amazonservices.com',
             'IN': 'mws.amazonservices.in',
             'CN': 'mws.amazonservices.com.cn',
             'JP': 'mws.amazonservices.jp'}

MARKETIDS = {'CA': 'A2EUQ1WTGCTBG2',
             'MX': 'A1AM78C64UM0Y8',
             'US': 'ATVPDKIKX0DER',
             'DE': 'A1PA6795UKMFR9',
             'ES': 'A1RKKUPIHCS9HS',
             'FR': 'A13V1IB3VIYZZH',
             'IT': 'APJ6JRA9NG5V4',
             'UK': 'A1F83G8C2ARO7P',
             'IN': 'A21TJRUUN4KGV',
             'JP': 'A21TJRUUN4KGV',
             'CN': 'AAHKV2X7AFYLW'}

class MWSError(Exception):
    pass


class MWSCall:
    """ Base class for the MWS API.

    Handles building requests to send to Amazon."""

    URI = '/'
    VERSION = '2009-01-01'
    ACCOUNT_TYPE = 'SellerId'
    USER_AGENT = 'amazonmws/0.0.1 (Language=Python)'
    DEFAULT_MARKET = 'US'

    def __init__(self, access_key, secret_key, account_id, region='NA', auth_token='', action='',
                 uri='', version='', account_type='', user_agent=''):
        self._access_key = access_key
        self._secret_key = secret_key
        self._account_id = account_id
        self._region = region
        self._auth_token = auth_token
        self._action = action
        self._uri = uri or self.URI
        self._version = version or self.VERSION
        self._account_type = account_type or self.ACCOUNT_TYPE
        self._user_agent = user_agent or self.USER_AGENT

        try:
            self._domain = ENDPOINTS[region]
        except KeyError:
            msg = 'Invalid region: {}. Recognized values are {}.'.format(region, ', '.join(ENDPOINTS.keys()))
            raise MWSError(msg)

    def build_request_url(self, method, action, **kwargs):
        """Return a properly formatted and signed request URL based on the given parameters."""

        params = {'AWSAccessKeyId': self._access_key,
                  'Action': action,
                  self._account_type: self._account_id,
                  'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'Timestamp': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
                  'Version': self._version}

        if self._auth_token:
            params['MWSAuthToken'] = self._auth_token

        for k, v in kwargs.items():
            if k.endswith('List'):
                params.update(self.enumerate_param(k, v))
            elif v:
                params.update({k:v})

        pairs = ['{}={}'.format(key, urllib.parse.quote(params[key], safe='-_.~', encoding='utf-8')) for key in sorted(params)]
        request_desc = '&'.join(pairs)

        sig_data = '{verb}\n{dom}\n{uri}\n{req}'.format(verb=method, dom=self._domain.lower(), uri=self._uri, req=request_desc)

        # Create the signature
        signature = b64encode(hmac.new(self._secret_key.encode(), sig_data.encode(), sha256).digest())
        signature = urllib.parse.quote(signature.decode(), safe='')

        # Create the URL
        url = 'https://{dom}{uri}?{req}&Signature={sig}'.format(dom=self._domain, uri=self._uri, req=request_desc, sig=signature)

        return url

    def __getattr__(self, name):
        return MWSCall(self._access_key, self._secret_key, self._account_id, region=self._region,
                       auth_token=self._auth_token, action=name, uri=self._uri, version=self._version,
                       account_type=self._account_type, user_agent=self._user_agent)

    def __call__(self, **kwargs):
        extra_headers = {}

        body = kwargs.pop('body', None)
        if body:
            md = b64encode(md5(body.encode()).digest()).strip(b'\n')
            extra_headers = {'Content-MD5': md, 'Content-Type': 'text/xml'}

        headers = self.build_headers(**extra_headers)
        url = self.build_request_url('POST', self._action, **kwargs)

        return self.make_request('POST', url, data=body, headers=headers)

    def build_headers(self, **kwargs):
        """Return a dictionary with header information."""
        headers = {'User-Agent': self._user_agent}
        headers.update(kwargs)
        return headers

    def market_id(self, market=''):
        """Return the Amazon Market ID for the given market."""
        try:
            return MARKETIDS[market or self.DEFAULT_MARKET]
        except KeyError:
            msg = 'Invalid market: {}. Recognized values are {}.'.format(market, ', '.join(MARKETIDS.keys()))
            raise MWSError(msg)

    def enumerate_param(self, root, values):
        ptype = root[:-4]        # Ex: ASINList -> ASIN
        params = {}

        for num, val in enumerate(values, start=1):
            base = '{}.{}.{}'.format(root, ptype, num)
            if isinstance(val, dict):
                params.update({'{}.{}'.format(base, k):v for k,v in val.items()})
            else:
                params.update({base:val})

        return params

    def make_request(self, method, url, data='', headers={}):
        """Return a requests response object for the the given request."""
        return requests.request(method, url, data=data, headers=headers)


class Feeds(MWSCall):
    """Interface to the Feeds section of the MWS API."""
    URI = '/'
    VERSION = '2009-01-01'

class Finances(MWSCall):
    """Interface to the Finances section of the API."""
    URI = '/Finances/2015-05-01'
    VERSION = '2015-05-01'

class Products(MWSCall):
    """Interface to the Products section of the MWS API."""
    URI = '/Products/2011-10-01'
    VERSION = '2011-10-01'

class FulfillmentInboundShipment(MWSCall):
    """Interface to the Fulfillment Inbound Shipment section of the API."""
    URI = '/FulfillmentInboundShipment/2010-10-01'
    VERSION = '2010-10-01'

class FulfillmentInventory(MWSCall):
    """Interface to the Fulfillment Inventory section of the API."""
    URI = '/FulfillmentInventory/2010-10-01'
    VERSION = '2010-10-01'

class FulfillmentOutboundShipment(MWSCall):
    """Interface to the Fulfillment Outbound Shipment section of the API."""
    URI = '/FulfillmentOutboundShipment/2010-10-01'
    VERSION = '2010-10-01'

class MerchantFulfillment(MWSCall):
    """Interface to the Merchant Fulfillment section of the API."""
    URI = '/MerchantFulfillment/2015-06-01'
    VERSION = '2015-06-01'

class Orders(MWSCall):
    """Interface to the Orders section of the API."""
    URI = '/Orders/2013-09-01'
    VERSION = '2013-09-01'

class Products(MWSCall):
    """Interface to the Products section of the API."""
    URI = '/Products/2011-10-01'
    VERSION = '2011-10-01'

class Recommendations(MWSCall):
    """Interface to the Recommendations section of the API."""
    URI = '/Recommendations/2013-04-01'
    VERSION = '2013-04-01'

class Reports(MWSCall):
    """Interface to the Reports section of the API."""
    URI = '/'
    VERSION ='2009-01-01'

class Sellers(MWSCall):
    """Interface to the Sellers section of the API."""
    URI = '/Sellers'
    VERSION = '2011-07-01'

class Subscriptions(MWSCall):
    """Interface to the Subscriptions section of the API."""
    URI = '/Subscriptions/2013-07-01'
    VERSION = '2013-07-01'
