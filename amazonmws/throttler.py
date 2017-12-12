from functools import partial
from time import time, sleep
from .api import AmzCall


########################################################################################################################


DEFAULT_LIMITS = {
    'ListMatchingProducts': {
        'quota_max': 20,
        'restore_rate': 5,
        'hourly_max': 720
    },
    'GetServiceStatus': {
        'quota_max': 2,
        'restore_rate': 300
    }
}


########################################################################################################################


class Throttler:

    def __init__(self, api=None, limits=None):
        """Initialize the Throttler object."""
        self.limits = dict(DEFAULT_LIMITS) if limits is None else limits
        self._usage = {}
        self.api = api

    def restore_quota(self, action):
        """Updates the quota for a given action, based on the elapsed time since the last request."""
        try:
            limits = self.limits[action]
            restore_rate = limits['restore_rate']
            usage = self._usage[action]
            quota_level, last_request = usage['quota_level'], usage['last_request']
        except KeyError:
            return

        elapsed = time() - last_request
        restored = elapsed // restore_rate

        self._usage[action]['quota_level'] = max(quota_level - restored, 0)

    def calculate_wait(self, action):
        """Return how long to wait, in seconds, before a given action can be performed."""
        try:
            quota_max, restore_rate = self.limits[action]['quota_max'], self.limits[action]['restore_rate']
            quota_level, last_request = self._usage[action]['quota_level'], self._usage[action]['last_request']
        except KeyError:
            return 0

        if quota_level < quota_max:
            return 0

        elapsed = time() - last_request
        return (quota_level + 1 - quota_max) * restore_rate - elapsed

    def add_to_quota(self, action):
        """Updates the usage information for the given action."""
        if action not in self.limits:
            return

        action_usage = self._usage.get(action, {})
        action_usage.update(
            quota_level=action_usage.get('quota_level', 0) + 1,
            last_request=time()
        )
        self._usage[action] = action_usage

    def api_call(self, action, **kwargs):
        """Forwards an API call to the API object (if provided), sleep()ing as necessary."""
        self.restore_quota(action)
        sleep(self.calculate_wait(action))
        self.restore_quota(action)
        self.add_to_quota(action)

        if self.api is not None:
            return getattr(self.api, action)(**kwargs)

    def __getattr__(self, name):
        """Shortcut for calling api_call() directly."""
        return partial(self.api_call, name)