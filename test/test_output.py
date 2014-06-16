# Copyright (C) 2014 SEE AUTHORS FILE
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Unittests.
"""

import mock
import logging

from reworker import output

from . import TestCase, unittest


CORR_ID = 123456


def send(topic, corr_id, body):
    pass


class TestOutput(TestCase):
    """
    Tests for the output module.
    """

    def setUp(self):
        self.send_meth = mock.MagicMock(send)

    def tearDown(self):
        self.send_meth.reset_mock()

    def test_basic_creation(self):
        """
        Make sure the proper items on Output are set upon creation.
        """
        o = output.Output(self.send_meth, CORR_ID)
        assert o._level == logging.getLevelName('INFO')
        assert o.corr_id == CORR_ID
        assert o.send == self.send_meth

    def test_creation_with_level(self):
        """
        Make sure the proper level is set if defined on creation.
        """
        o = output.Output(self.send_meth, CORR_ID, 'DEBUG')
        assert o._level == logging.getLevelName('DEBUG')

        # If the level doesn't exist it should not modify it.
        o = output.Output(self.send_meth, CORR_ID, 'asdasdasd')
        assert o._level == logging.getLevelName('INFO')

    def test_log_with_higher_level(self):
        """
        Log should always go to the bus if the level number is >= to the
        one set.
        """
        o = output.Output(self.send_meth, CORR_ID, 'DEBUG')
        o.log('INFO', 'testing')
        self.send_meth.call_count == 1
        self.send_meth.assert_called_with(
            'output', CORR_ID, {'message': 'testing'})

        o.log('WARN', 'test')
        self.send_meth.call_count == 2
        self.send_meth.assert_called_with(
            'output', CORR_ID, {'message': 'test'})

    def test_log_with_mixed_level(self):
        """
        Log should only out to the bus if the level number is >= to the
        one set.
        """
        o = output.Output(self.send_meth, CORR_ID, 'INFO')
        o.log('DEBUG', 'testing')
        self.send_meth.call_count == 0

        o.log('INFO', 'test')
        self.send_meth.call_count == 1
        self.send_meth.assert_called_with(
            'output', CORR_ID, {'message': 'test'})

    def test_log_with_lower_level(self):
        """
        If the level is under the threshold no data should go to the bus.
        """
        o = output.Output(self.send_meth, CORR_ID, 'FATAL')
        o.log('DEBUG', 'testing')
        o.log('WARN', 'testing')
        o.log('ERROR', 'testing')
        self.send_meth.call_count == 0
