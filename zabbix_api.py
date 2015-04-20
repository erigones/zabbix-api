# -*- coding: utf-8 -*-
"""
This is a port of the ruby zabbix api found here:
http://trac.red-tux.net/browser/ruby/api/zbx_api.rb

LGPL 2.1   http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html

Zabbix API Python Library.
Original Ruby Library is Copyright (C) 2009 Andrew Nelson nelsonab(at)red-tux(dot)net
Python Library is Copyright (C) 2009 Brett Lentz brett.lentz(at)gmail(dot)com
                  Copyright (C) 2013-2015 Erigones, s. r. o. erigones(at)erigones(dot)com
                  Copyright (C) 2014-2015 https://github.com/gescheit/scripts

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

NOTES: The API requires Zabbix 1.8 or later.
"""

from logging import getLogger, DEBUG, INFO, WARNING, ERROR
from collections import deque
from datetime import datetime
from hashlib import md5
from base64 import b64encode
from time import time
import re

try:
    # noinspection PyPackageRequirements
    import simplejson as json
except ImportError:
    import json

try:
    import urllib2
except ImportError:
    # noinspection PyUnresolvedReferences,PyPep8Naming
    import urllib.request as urllib2  # python3

__all__ = ('ZabbixAPI', 'ZabbixAPIException', 'ZabbixAPIError')
__version__ = '1.0.1'

PARENT_LOGGER = __name__
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
TRIGGER_SEVERITY = (
    'not_classified',
    'information',
    'warning',
    'average',
    'high',
    'disaster',
)
RE_HIDE_AUTH = (
    (re.compile(r'("auth": )".*?"'), r'\1"***"'),
    (re.compile(r'("password": )".*?"'), r'\1"***"'),
)


def hide_auth(msg):
    """Remove sensitive information from msg."""
    for pattern, repl in RE_HIDE_AUTH:
        msg = pattern.sub(repl, msg)

    return msg


class ZabbixAPIException(Exception):
    """
    Generic zabbix API exception. Used for HTTP connection/transport errors.
    """
    def __init__(self, msg):
        super(ZabbixAPIException, self).__init__(hide_auth(msg))  # Remove sensitive information


class ZabbixAPIError(ZabbixAPIException):
    """
    Structured zabbix API error. Used for Zabbix API errors.
    The error attribute is always a dict with "code", "message" and "data" keys.

    Code list:
         -32602 - Invalid params (eg already exists)
         -32500 - no permissions
    """
    _error_template = {'code': -1, 'message': '', 'data': None}

    def __init__(self, **error_kwargs):
        self.error = dict(self._error_template, **error_kwargs)
        msg = '%(message)s %(data)s [%(code)s]' % self.error
        super(ZabbixAPIError, self).__init__(msg)


class ZabbixAPI(object):
    """
    Login and access any Zabbix API method.
    """
    __username = None
    __password = None
    __auth = None
    _http_handler = None
    _http_headers = None
    _api_url = None
    id = 0
    last_login = None

    QUERY_EXTEND = 'extend'
    QUERY_COUNT = 'count'

    SORT_ASC = 'ASC'
    SORT_DESC = 'DESC'

    def __init__(self, server='http://localhost/zabbix', user=None, passwd=None, log_level=WARNING, timeout=10,
                 relogin_interval=60, r_query_len=10):
        """
        Create an API object. We're going to use proto://server/path to find the JSON-RPC api.

        :param str server: Server URL to connect to
        :param str user: Optional HTTP auth username
        :param str passwd: Optional HTTP auth password
        :param int log_level: Logging level
        :param int timeout: Timeout for HTTP requests to api (in seconds)
        :param int r_query_len: Max length of query history
        :param int relogin_interval: Minimum time (in seconds) after which an automatic re-login is performed; \
         Can be set to None to disable automatic re-logins
        """
        self.logger = getLogger(PARENT_LOGGER)
        self.set_log_level(log_level)
        self.server = server
        self.httpuser = user
        self.httppasswd = passwd
        self.timeout = timeout
        self.relogin_interval = relogin_interval
        self.r_query = deque(maxlen=r_query_len)
        self.init()

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.server)

    def __getattr__(self, name):
        """Access any API method via dot notation [DEPRECATED -> use call()]"""
        if name.startswith('_'):
            raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

        api_method = ZabbixAPISubClass(self, name)
        setattr(self, name, api_method)

        return api_method

    def init(self):
        """Prepare the HTTP handler, URL, and HTTP headers for all subsequent requests"""
        self.debug('Initializing %r', self)
        proto = self.server.split('://')[0]

        if proto == 'https':
            self._http_handler = urllib2.HTTPSHandler(debuglevel=0)
        elif proto == 'http':
            self._http_handler = urllib2.HTTPHandler(debuglevel=0)
        else:
            raise ValueError('Invalid protocol %s' % proto)

        self._api_url = self.server + '/api_jsonrpc.php'
        self._http_headers = {
            'Content-Type': 'application/json-rpc',
            'User-Agent': 'python/zabbix_api',
        }

        if self.httpuser:
            self.debug('HTTP authentication enabled')
            auth = self.httpuser + ':' + self.httppasswd
            self._http_headers['Authorization'] = 'Basic ' + b64encode(auth.encode('utf-8')).decode('ascii')

    @staticmethod
    def get_severity(prio):
        """Return severity string from severity id"""
        try:
            return TRIGGER_SEVERITY[int(prio)]
        except IndexError:
            return 'unknown'

    @classmethod
    def get_datetime(cls, timestamp):
        """Return python datetime object from unix timestamp"""
        return datetime.fromtimestamp(int(timestamp))

    @staticmethod
    def convert_datetime(dt, dt_format=DATETIME_FORMAT):
        """Convert python datetime to human readable date and time string"""
        return dt.strftime(dt_format)

    @classmethod
    def timestamp_to_datetime(cls, dt, dt_format=DATETIME_FORMAT):
        """Convert unix timestamp to human readable date/time string"""
        return cls.convert_datetime(cls.get_datetime(dt), dt_format=dt_format)

    @staticmethod
    def get_age(dt):
        """Calculate delta between current time and datetime and return a human readable form of the delta object"""
        delta = datetime.now() - dt
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        if days:
            return '%dd %dh %dm' % (days, hours, minutes)
        else:
            return '%dh %dm %ds' % (hours, minutes, seconds)

    def recent_query(self):
        """Return recent API query object"""
        return list(self.r_query)

    def set_log_level(self, level):
        self.debug('Set logging level to %d', level)
        self.logger.setLevel(level)

    def log(self, level, msg, *args):
        return self.logger.log(level, msg, *args)

    def debug(self, msg, *args):
        return self.log(DEBUG, msg, *args)

    def json_obj(self, method, params=None, auth=True):
        """Return JSON object expected by the Zabbix API"""
        if params is None:
            params = {}

        obj = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'auth': self.__auth if auth else None,
            'id': self.id,
        }

        return json.dumps(obj)

    def do_request(self, json_obj):
        """Perform one HTTP request to Zabbix API"""
        self.debug('Request: url="%s" headers=%s', self._api_url, self._http_headers)
        self.debug('Request: body=%s', json_obj)
        self.r_query.append(json_obj)

        request = urllib2.Request(url=self._api_url, data=json_obj.encode('utf-8'), headers=self._http_headers)
        opener = urllib2.build_opener(self._http_handler)
        urllib2.install_opener(opener)

        try:
            response = opener.open(request, timeout=self.timeout)
        except Exception as e:
            raise ZabbixAPIException('HTTP connection problem: %s' % e)

        self.debug('Response: code=%s', response.code)

        # NOTE: Getting a 412 response code means the headers are not in the list of allowed headers.
        if response.code != 200:
            raise ZabbixAPIException('HTTP error %s: %s' % (response.status, response.reason))

        reads = response.read()

        if len(reads) == 0:
            raise ZabbixAPIException('Received zero answer')

        try:
            jobj = json.loads(reads.decode('utf-8'))
        except ValueError as e:
            self.log(ERROR, 'Unable to decode. returned string: %s', reads)
            raise ZabbixAPIException('Unable to decode response: %s' % e)

        self.debug('Response: body=%s', jobj)
        self.id += 1

        if 'error' in jobj:  # zabbix API error
            error = jobj['error']

            if isinstance(error, dict):
                raise ZabbixAPIError(**error)

        try:
            return jobj['result']
        except KeyError:
            raise ZabbixAPIException('Missing result in API response')

    def login(self, user=None, password=None, save=True):
        """Perform a user.login API request"""
        if user and password:
            if save:
                self.__username = user
                self.__password = password
        elif self.__username and self.__password:
            user = self.__username
            password = self.__password
        else:
            raise ZabbixAPIException('No authentication information available.')

        self.last_login = time()
        # Don't print the raw password
        hashed_pw_string = 'md5(%s)' % md5(password.encode('utf-8')).hexdigest()
        self.debug('Trying to login with %r:%r', user, hashed_pw_string)
        obj = self.json_obj('user.login', params={'user': user, 'password': password}, auth=False)
        self.__auth = self.do_request(obj)

    def relogin(self):
        """Perform a re-login"""
        try:
            self.__auth = None  # reset auth before relogin
            self.login()
        except ZabbixAPIException as e:
            self.log(ERROR, 'Zabbix API relogin error (%s)', e)
            self.__auth = None  # logged_in() will always return False
            raise  # Re-raise the exception

    @property
    def logged_in(self):
        return bool(self.__auth)

    def check_auth(self):
        """Perform a re-login if not signed in or raise an exception"""
        if not self.logged_in:
            if self.relogin_interval and self.last_login and (time() - self.last_login) > self.relogin_interval:
                self.log(WARNING, 'Zabbix API not logged in. Performing Zabbix API relogin after %d seconds',
                         self.relogin_interval)
                self.relogin()  # Will raise exception in case of login error
            else:
                raise ZabbixAPIException('Not logged in.')

    def api_version(self):
        """Call apiinfo.version API method"""
        return self.do_request(self.json_obj('apiinfo.version', auth=False))

    def call(self, method, params=None):
        """Check authentication and perform actual API request and relogin if needed"""
        start_time = time()
        self.check_auth()
        self.log(INFO, '[%s-%05d] Calling Zabbix API method "%s"', start_time, self.id, method)
        self.log(DEBUG, '\twith parameters: %s', params)

        try:
            return self.do_request(self.json_obj(method, params=params))
        except ZabbixAPIException as ex:
            if self.relogin_enabled and str(ex).find('Not authorized while sending') >= 0:
                self.log(WARNING, 'Zabbix API not logged in (%s). Performing Zabbix API relogin', ex)
                self.relogin()  # Will raise exception in case of login error
                return self.do_request(self.json_obj(method, params=params))
            raise  # Re-raise the exception
        finally:
            self.log(INFO, '[%s-%05d] Zabbix API method "%s" finished in %g seconds',
                     start_time, self.id, method, (time() - start_time))


class ZabbixAPISubClass(object):
    """
    Wrapper class to ensure all calls go through the parent object.
    """
    def __init__(self, parent, prefix):
        self.prefix = prefix
        self.parent = parent
        self.parent.debug('Creating %r', self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.prefix)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

        if self.prefix == 'configuration' and name == 'import_':  # workaround for "import" method
            name = 'import'

        def method(params=None):
            return self.parent.call('%s.%s' % (self.prefix, name), params=params)
        return method