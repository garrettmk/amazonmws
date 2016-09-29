#
# An interface for building requests to Amazon's MWS API
#
# Based on python-amazon-mws: https://github.com/czpython/python-amazon-mws/
#

import hmac
import requests
import urllib

from base64 import b64encode
from functools import partial
from hashlib import sha256, md5
from time import strftime, gmtime


ENDPOINTS_MWS = {'NA': 'mws.amazonservices.com',
                 'EU': 'mws-eu.amazonservices.com',
                 'IN': 'mws.amazonservices.in',
                 'CN': 'mws.amazonservices.com.cn',
                 'JP': 'mws.amazonservices.jp'}

ENDPOINTS_PA = {'BR': 'webservices.amazon.com.br',
                'CN': 'webservices.amazon.cn',
                'CA': 'webservices.amazon.ca',
                'DE': 'webservices.amazon.de',
                'ES': 'webservices.amazon.es',
                'FR': 'webservices.amazon.fr',
                'IN': 'webservices.amazon.in',
                'IT': 'webservices.amazon.it',
                'JP': 'webservices.amazon.co.jp',
                'MX': 'webservices.amazon.com.mx',
                'UK': 'webservices.amazon.co.uk',
                'US': 'webservices.amazon.com'}

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


class AmzCall:
    """ Base class for the MWS API.

    Handles building requests to send to Amazon."""

    URI = '/'
    VERSION = '2009-01-01'
    ACCOUNT_TYPE = 'SellerId'
    ACTION_TYPE = 'Action'
    USER_AGENT = 'amazonmws/0.0.1 (Language=Python)'

    def __init__(self, access_key, secret_key, account_id, region='NA', auth_token='', default_market='US',
                 uri='', version='', account_type='', user_agent='', make_request=None):
        self._access_key = access_key
        self._secret_key = secret_key
        self._account_id = account_id
        self._region = region
        self._default_market = default_market
        self._auth_token = auth_token
        self._uri = uri or self.URI
        self._version = version or self.VERSION
        self._account_type = account_type or self.ACCOUNT_TYPE
        self._user_agent = user_agent or self.USER_AGENT
        self.set_request_function(make_request)

        try:
            self._domain = ENDPOINTS_MWS[region]
        except KeyError:
            msg = 'Invalid region: {}. Recognized values are {}.'.format(region, ', '.join(ENDPOINTS_MWS.keys()))
            raise MWSError(msg)

    def build_request_url(self, method, action, **kwargs):
        """Return a properly formatted and signed request URL based on the given parameters."""

        params = {'AWSAccessKeyId': self._access_key,
                  self.ACTION_TYPE: action,
                  self.ACCOUNT_TYPE: self._account_id,
                  'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'Timestamp': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
                  'Version': self._version}

        if self._auth_token:
            params['MWSAuthToken'] = self._auth_token

        for k, v in kwargs.items():
            if k.endswith('List') or k.startswith('List'):
                params.update(self.enumerate_param(k, v))
            elif v:
                params.update({k:v})

        # Create the string to sign
        pairs = ['{}={}'.format(key, urllib.parse.quote(str(params[key]), safe='-_.~', encoding='utf-8')) for key in sorted(params)]
        request_desc = '&'.join(pairs)

        sig_data = '{verb}\n{dom}\n{uri}\n{req}'.format(verb=method, dom=self._domain.lower(), uri=self._uri, req=request_desc)

        # Create the signature
        signature = b64encode(hmac.new(self._secret_key.encode(), sig_data.encode(), sha256).digest())
        signature = urllib.parse.quote(signature.decode(), safe='')

        # Create the URL
        url = 'https://{dom}{uri}?{req}&Signature={sig}'.format(dom=self._domain, uri=self._uri, req=request_desc, sig=signature)

        return url

    def __getattr__(self, name):
        return partial(self._do_api_call, name)

    def _do_api_call(self, operation, **kwargs):
        extra_headers = {}

        # If body is provided, include an MD5 signature in the header
        body = kwargs.pop('body', None)
        if body:
            md = b64encode(md5(body.encode()).digest()).strip(b'\n')
            extra_headers = {'Content-MD5': md, 'Content-Type': 'text/xml'}

        headers = self.build_headers(**extra_headers)
        url = self.build_request_url('POST', operation, **kwargs)

        return self._make_request('POST', url, data=body, headers=headers)

    def build_headers(self, **kwargs):
        """Return a dictionary with header information."""
        headers = {'User-Agent': self._user_agent}
        headers.update(kwargs)
        return headers

    def market_id(self, market=''):
        """Return the Amazon Market ID for the given market."""
        try:
            return MARKETIDS[market or self._default_market]
        except KeyError:
            msg = 'Invalid market: {}. Recognized values are {}.'.format(market, ', '.join(MARKETIDS.keys()))
            raise MWSError(msg)

    def enumerate_param(self, root, values):
        if root == 'MarketplaceId':
            ptype = 'Id'
        else:
            ptype = root.replace('List', '')        # Ex: ASINList -> ASIN

        params = {}

        for num, val in enumerate(values, start=1):
            base = '{}.{}.{}'.format(root, ptype, num)
            if isinstance(val, dict):
                params.update({'{}.{}'.format(base, k):v for k,v in val.items()})
            else:
                params.update({base:val})

        return params

    def set_request_function(self, func=None):
        """Set the function that receives the URL and header information. Defaults to requests.request()."""
        self._make_request = func or requests.request


class Feeds(AmzCall):
    """Interface to the Feeds section of the MWS API."""
    URI = '/'
    VERSION = '2009-01-01'


class Finances(AmzCall):
    """Interface to the Finances section of the API."""
    URI = '/Finances/2015-05-01'
    VERSION = '2015-05-01'


class Products(AmzCall):
    """Interface to the Products section of the MWS API."""
    URI = '/Products/2011-10-01'
    VERSION = '2011-10-01'


class FulfillmentInboundShipment(AmzCall):
    """Interface to the Fulfillment Inbound Shipment section of the API."""
    URI = '/FulfillmentInboundShipment/2010-10-01'
    VERSION = '2010-10-01'


class FulfillmentInventory(AmzCall):
    """Interface to the Fulfillment Inventory section of the API."""
    URI = '/FulfillmentInventory/2010-10-01'
    VERSION = '2010-10-01'


class FulfillmentOutboundShipment(AmzCall):
    """Interface to the Fulfillment Outbound Shipment section of the API."""
    URI = '/FulfillmentOutboundShipment/2010-10-01'
    VERSION = '2010-10-01'


class MerchantFulfillment(AmzCall):
    """Interface to the Merchant Fulfillment section of the API."""
    URI = '/MerchantFulfillment/2015-06-01'
    VERSION = '2015-06-01'


class Orders(AmzCall):
    """Interface to the Orders section of the API."""
    URI = '/Orders/2013-09-01'
    VERSION = '2013-09-01'


class Products(AmzCall):
    """Interface to the Products section of the API."""
    URI = '/Products/2011-10-01'
    VERSION = '2011-10-01'


class Recommendations(AmzCall):
    """Interface to the Recommendations section of the API."""
    URI = '/Recommendations/2013-04-01'
    VERSION = '2013-04-01'


class Reports(AmzCall):
    """Interface to the Reports section of the API."""
    URI = '/'
    VERSION ='2009-01-01'


class Sellers(AmzCall):
    """Interface to the Sellers section of the API."""
    URI = '/Sellers'
    VERSION = '2011-07-01'


class Subscriptions(AmzCall):
    """Interface to the Subscriptions section of the API."""
    URI = '/Subscriptions/2013-07-01'
    VERSION = '2013-07-01'


class ProductAdvertising(AmzCall):
    """Interface to the Product Advertising API."""
    URI = '/onca/xml'
    VERSION = ''
    ACCOUNT_TYPE = 'AssociateTag'
    ACTION_TYPE = 'Operation'

    def __init__(self, access_key, secret_key, account_id, **kwargs):
        region = kwargs.pop('region', 'US')
        super(ProductAdvertising, self).__init__(access_key, secret_key, account_id, **kwargs)

        try:
            self._domain = ENDPOINTS_PA[region]
        except KeyError:
            msg = 'Invalid region: {}. Recognized values are {}.'.format(region, ', '.join(ENDPOINTS_PA.keys()))
            raise MWSError(msg)

    def _api_call(self, operation, **kwargs):
        kwargs['Service'] = 'AWSECommerceService'
        headers = self.build_headers()
        url = self.build_request_url('GET', operation, **kwargs)

        return self._make_request('GET', url, headers=headers)