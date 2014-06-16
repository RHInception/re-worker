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

import json
import os.path
import sys
import mock

from contextlib import nested
from reworker import worker

from . import TestCase, unittest


class DummyWorker(worker.Worker):
    """
    Worker to test with.
    """

    def process(self, channel, basic_deliver, properties, body, output):
        output.info(str(body))
        self.ack(basic_deliver)


class TestWorker(TestCase):

    def test_runner_inputs(self):
        """
        The runner function should honor inputs.
        """
        with nested(
                mock.patch('reworker.worker.pika'),
                mock.patch('reworker.worker.logging')):
            sys.argv = ['', 'examples/mqconf.json']
            dummy = mock.Mock(worker.Worker)
            worker.runner(dummy)

            dummy.assert_called_once_with(
                json.load(open('examples/mqconf.json', 'r')),
                config_file=None)

            assert dummy().run_forever.call_count == 1

            # With output dir
            dummy.reset_mock()
            sys.argv = ['', 'examples/mqconf.json']
            worker.runner(dummy)

            dummy.assert_called_once_with(
                json.load(open('examples/mqconf.json', 'r')),
                config_file=None)

            assert dummy().run_forever.call_count == 1

            # With a worker config
            dummy.reset_mock()
            sys.argv = [
                '', 'examples/mqconf.json', '-w', 'examples/mqconf.json']
            worker.runner(dummy)

            dummy.assert_called_once_with(
                json.load(open('examples/mqconf.json', 'r')),
                config_file='examples/mqconf.json')

            assert dummy().run_forever.call_count == 1
