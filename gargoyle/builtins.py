"""
gargoyle.builtins
~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from gargoyle import gargoyle
from gargoyle.conditions import ModelConditionSet, RequestConditionSet, Percent, String, Boolean, \
    ConditionSet, OnOrAfterDate, Group

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.validators import validate_ipv4_address

import socket
import struct


class UserConditionSet(ModelConditionSet):
    username = String()
    email = String()
    is_anonymous = Boolean(label='Anonymous')
    is_active = Boolean(label='Active')
    is_staff = Boolean(label='Staff')
    is_superuser = Boolean(label='Superuser')
    date_joined = OnOrAfterDate(label='Joined on or after')
    is_member_of_group = Group(label='Is member of group')

    def can_execute(self, instance):
        return isinstance(instance, (User, AnonymousUser))

    def is_active(self, instance, conditions):
        """
        value is the current value of the switch
        instance is the instance of our type
        """
        if isinstance(instance, User):
            return super(UserConditionSet, self).is_active(instance, conditions)

        # HACK: allow is_authenticated to work on AnonymousUser
        condition = conditions.get(self.get_namespace(), {}).get('is_anonymous')
        if condition is not None:
            return bool(condition)
        return None

gargoyle.register(UserConditionSet(User))


class IPAddress(String):
    def clean(self, value):
        validate_ipv4_address(value)
        return value


class IPAddressConditionSet(RequestConditionSet):
    percent = Percent()
    ip_address = IPAddress(label='IP Address')
    internal_ip = Boolean(label='Internal IPs')

    def get_namespace(self):
        return 'ip'

    def get_field_value(self, instance, field_name):
        # XXX: can we come up w/ a better API?
        # Ensure we map ``percent`` to the ``id`` column
        if field_name == 'percent':
            return self._ip_to_int(instance.META['REMOTE_ADDR'])
        elif field_name == 'ip_address':
            return instance.META['REMOTE_ADDR']
        elif field_name == 'internal_ip':
            return instance.META['REMOTE_ADDR'] in settings.INTERNAL_IPS
        return super(IPAddressConditionSet, self).get_field_value(instance, field_name)

    def _ip_to_int(self, ip):
        if '.' in ip:
            # IPv4
            return sum([int(x) for x in ip.split('.')])
        if ':' in ip:
            # IPv6
            hi, lo = struct.unpack('!QQ', socket.inet_pton(socket.AF_INET6, ip))
            return (hi << 64) | lo
        raise ValueError('Invalid IP Address %r' % ip)

    def get_group_label(self):
        return 'IP Address'

gargoyle.register(IPAddressConditionSet())


class HostConditionSet(ConditionSet):
    hostname = String()

    def get_namespace(self):
        return 'host'

    def can_execute(self, instance):
        return instance is None

    def get_field_value(self, instance, field_name):
        if field_name == 'hostname':
            return socket.gethostname()

    def get_group_label(self):
        return 'Host'

gargoyle.register(HostConditionSet())
