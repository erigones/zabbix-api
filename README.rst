zabbix-api-erigones
###################

`Zabbix API <https://www.zabbix.com/documentation/2.4/manual/api>`_ Python Library.

Used by the `Ludolph Monitoring Jabber Bot <https://github.com/erigones/Ludolph>`_.

* Supported Python versions: >= 2.6 and >= 3.2
* Supported Zabbix versions: 1.8, 2.0, 2.2, 2.4

.. image:: https://badge.fury.io/py/zabbix-api-erigones.png
    :target: http://badge.fury.io/py/zabbix-api-erigones


Installation
------------

.. code:: bash

    pip install zabbix-api-erigones

Usage
-----

.. code:: python

    from zabbix_api import ZabbixAPI

    zx = ZabbixAPI(server='http://127.0.0.1')
    zx.login('username', 'password')

    # Example: list zabbix users
    zx.call('user.get', {'output': 'extend'})

    # Or use the old dot notation method
    zx.user.get({'output': 'extend'})

Links
-----

- Bug Tracker: https://github.com/erigones/zabbix-api-erigones/issues
- Twitter: https://twitter.com/erigones

