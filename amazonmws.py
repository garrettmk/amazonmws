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
from hashlib import sha256


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

THROTTLING = {'ListMatchingProducts': (20, 5, 720)}


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

    def __init__(self, access_key, secret_key, account_id, region='NA', auth_token='', user_agent='', action=''):
        self._access_key = access_key
        self._secret_key = secret_key
        self._account_id = account_id
        self._auth_token = auth_token
        self._user_agent = user_agent or self.USER_AGENT
        self._region = region
        self._action = action

        try:
            self._domain = ENDPOINTS[region]
        except KeyError:
            msg = 'Invalid region: {}. Recognized values are {}.'.format(region, ', '.join(ENDPOINTS.keys()))
            raise MWSError(msg)


    def build_request_url(self, method, Action, **kwargs):
        """Return a properly formatted and signed request URL based on the given parameters."""

        params = {'AWSAccessKeyId': self._access_key,
                  'Action': Action,
                  self.ACCOUNT_TYPE: self._account_id,
                  'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'Timestamp': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
                  'Version': self.VERSION}

        if self._auth_token:
            params['MWSAuthToken'] = self._auth_token

        params.update({k:v for k,v in kwargs.items() if v})

        pairs = ['{}={}'.format(key, urllib.parse.quote(params[key], safe='-_.~', encoding='utf-8')) for key in sorted(params)]
        request_desc = '&'.join(pairs)

        sig_data = '{verb}\n{dom}\n{uri}\n{req}'.format(verb=method, dom=self._domain.lower(), uri=self.URI, req=request_desc)

        # Create the signature
        signature = b64encode(hmac.new(self._secret_key.encode(), sig_data.encode(), sha256).digest())
        signature = urllib.parse.quote(signature.decode(), safe='')

        # Create the URL
        url = 'https://{dom}{uri}?{req}&Signature={sig}'.format(dom=self._domain, uri=self.URI, req=request_desc, sig=signature)

        return url

    def __getattr__(self, name):
        return type(self)(self._access_key, self._secret_key, self._account_id,
                          region=self._region, auth_token=self._auth_token, user_agent=self._user_agent,
                          action=name)

    def __call__(self, **kwargs):
        url = self.build_request_url('POST', self._action, **kwargs)
        headers = self.build_headers()
        return self.make_request('POST', url, data='', headers=headers)

    def build_headers(self, **kwargs):
        """Return a dictionary with header information."""
        headers = {'User-Agent': self.USER_AGENT}
        headers.update(kwargs)
        return headers

    def market_id(self, market=''):
        """Return the Amazon Market ID for the given market."""
        try:
            return MARKETIDS[market or self.DEFAULT_MARKET]
        except KeyError:
            msg = 'Invalid market: {}. Recognized values are {}.'.format(market, ', '.join(MARKETIDS.keys()))
            raise MWSError(msg)


    def make_request(self, method, url, data='', headers={}):
        """Return a requests response object for the the given request."""
        return requests.request(method, url, data=data, headers=headers)


class Products(MWSCall):

    URI = '/Products/2011-10-01'
    VERSION = '2011-10-01'

    def list_matching_products(self, query, market='', querycontextid=''):
        url = self.build_request_url('POST', Action='ListMatchingProducts',
                                     MarketplaceId=self.market_id(market),
                                     Query=query,
                                     QueryContextId=querycontextid)
        headers = self.build_headers()
        return self.make_request('POST', url, headers=headers)

    def get_service_status(self):
        url = self.build_request_url('POST', Action='GetServiceStatus')
        headers = self.build_headers()
        return self.make_request('POST', url, headers=headers)




# Just used for debugging right now
from mwskeys import *
def make_mws():
    return Products(mws_accesskey, mws_secretkey, mws_sellerid)
