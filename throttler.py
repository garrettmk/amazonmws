import time
import collections

from functools import partial
from api import AmzCall


ThrottleLimits = collections.namedtuple('ThrottleLimits', ['quota_max', 'restore_rate', 'hourly_max'])

LIMITS = {'ListMatchingProducts':           ThrottleLimits(20, 5, 720),
          'GetCompetitivePricingForAsin':   ThrottleLimits(20, 0.1, 36000),
          'GetMyFeesEstimate':              ThrottleLimits(20, 0.1, 36000)}


class Throttler:

    def __init__(self, api=None, blocking=False):
        """Initialize the Throttler object. If an api is provided, it's request function is set to the Throttler's
        request function. If blocking is set to True, sleep() will be called as-needed to keep from going over the
        quota for a particular request."""
        self._quota_level = {}
        self._last_quota_update = {}
        self._priority_max = {}
        self._blocking = blocking
        self._api = api

    def _pre_request(self, action, **kwargs):
        """Updates the quota for the specified action. If blocking=True, this method will sleep() if necessary
        before passing allowing the request to continue."""
        priority = kwargs.pop('priority', 0)

        if self._blocking:
            time.sleep(self.request_wait(action, priority))
        else:
            self._update_quota(action)

        self._quota_level[action] = self._quota_level.get(action, 0) + 1

        if self._api:
            return self._api.__getattr__(action)(**kwargs)

    def _update_quota(self, action):
        """Restore the quota as needed, based on the elapsed time since this method was last called."""
        try:
            LIMITS[action]
            self._quota_level[action]
        except KeyError:
            return

        now = time.time()
        restore_rate = LIMITS[action].restore_rate
        quota_level = self._quota_level[action]
        last_update = self._last_quota_update.get(action, now)

        self._quota_level[action] = max(quota_level - (now - last_update) // restore_rate, 0)
        self._last_quota_update[action] = now

    def request_wait(self, action, priority=0):
        """Return the number of seconds to wait before there is room in the quota for action."""
        try:
            LIMITS[action]
            self._quota_level[action]
        except KeyError:
            return 0

        self._update_quota(action)

        quota_max = sum(self._priority_max.get(action, [])[:priority + 1])
        quota_max = quota_max if quota_max else LIMITS[action].quota_max

        wait = max(self._quota_level[action] + 1 - quota_max, 0) * LIMITS[action].restore_rate
        return wait

    def set_priority_quota(self, action, priority, quota):
        """Reserve part of an action's quota for the specified priority."""
        self._priority_max[action] = self._priority_max.get(action, [])

        if priority + 1 > len(self._priority_max[action]):
            self._priority_max[action].extend([0 for i in range(priority + 1 - len(self._priority_max[action]))])

        self._priority_max[action][priority] = quota

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, api):
        if not isinstance(api, AmzCall):
            raise TypeError('Expected MWS API object, got %s' % type(api))
        self._api = api

    @property
    def blocking(self):
        return self._blocking

    @blocking.setter
    def blocking(self, value):
        self._blocking = bool(value)

    def __getattr__(self, action):
        return partial(self._pre_request, action)

