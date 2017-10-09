amazonmws
---------

Tools for communicating with Amazon's Merchant Web Services (MWS) and Product Advertising (PA) APIs. ``amazonmws`` is
designed to use ``requests``, but can be configured to use any networking API. This makes it ideal for use in both
scripts and GUI applications.

To use, first create an instance of the API you want to access, using your Amazon MWS or PA credentials:

    >>> import requests
    >>> import amazonmws as mws
    >>> api = mws.Products(your_access_id, your_secret_key, your_seller_id)
    >>> api.make_request = requests.request

Here, we have created an object to access the Products section of the MWS API. We have configured the object to use
``requests.request`` to the actual communication with Amazon. API calls can be made like so:

    >>> result = api.GetServiceStatus()
    >>> result
    <Response [200]>

The return value of an API call is the return value of the ``make_request`` function - in this case, a
``requests.Response`` object. We can view the XML response from Amazon using the result's ``text`` attribute:

    >>> from pprint import pprint
    >>> pprint(result.text)
    ('<?xml version="1.0"?>\n'
     '<GetServiceStatusResponse '
     'xmlns="http://mws.amazonservices.com/schema/Products/2011-10-01">\n'
     '  <GetServiceStatusResult>\n'
     '    <Status>GREEN</Status>\n'
     '    <Timestamp>2017-10-09T20:59:18.297Z</Timestamp>\n'
     '  </GetServiceStatusResult>\n'
     '  <ResponseMetadata>\n'
     '    <RequestId>3e8932c9-a95a-41a9-b56c-34e65672289b</RequestId>\n'
     '  </ResponseMetadata>\n'
     '</GetServiceStatusResponse>\n')

Parameters are specified using keyword arguments:

    >>> result = api.ListMatchingProducts(MarketplaceId='ATVPDKIKX0DER', Query='Turtles')

