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
import logging
import mock
import kombu

from kombu import Connection, message
from reworker import worker

from contextlib import nested

from . import TestCase, unittest

# Mocks
worker.logging = mock.MagicMock(logging)

# Config
MQ_CONF = {
    'server': '127.0.0.1',
    'port': 5672,
    'vhost': '',
    'user': 'guest',
    'password': 'guest',
}

# Default inputs
_PROCESS_KWARGS = {
    'message': mock.MagicMock(message.Message),
    'body': {
        'notify': {
            'started': {
                'irc': ['#release-engine'],
            }
        },
        'group': 'test',
        'parameters': {},
        'dynamic': {}},
}

PROCESS_KWARGS = {
    'channel': mock.MagicMock(Connection.channel),
    'basic_deliver': mock.MagicMock(),
    'properties': {'correlation_id': 1},
    'body': json.dumps({
        'notify': {
            'started': {
                'irc': ['#release-engine'],
            }
        },
        'group': 'test',
        'parameters': {},
        'dynamic': {}}),
    'output': mock.MagicMock(logging.getLogger()),
}


class DummyWorker(worker.Worker):
    """
    Worker to test with.
    """

    def process(self, channel, basic_deliver, properties, body, output):
        output.info(str(body))
        self.notify('slug', 'the message', 'started', corr_id=1)
        self.ack(basic_deliver)


class DynamicDummyWorker(worker.Worker):
    """
    Worker with dynamic inputs to test with.
    """

    def process(self, channel, basic_deliver, properties, body, output):
        output.info(str(body['dynamic']['item']))
        output.info(str(body))
        self.notify('no', 'should not fire', 'completed', corr_id=1)
        self.ack(basic_deliver)


class TestWorker(TestCase):

    def test_create_object(self):
        """
        Test creation of a worker acts as expected.
        """
        with mock.patch('reworker.worker.Connection'):
            w = worker.Worker(MQ_CONF)
            assert w._queue.name == 'worker.worker'
            assert w._config == {}
            # At this point connection should not happen
            assert w.connection.call_count == 0
            w = worker.Worker(
                MQ_CONF, config_file='test/config.json')
            assert w._config['a'] == 'test'

    def test_create_object_with_deprecated_input(self):
        """
        Test creation of a worker logs when deprecated inputs are used.
        """
        with mock.patch('reworker.worker.Connection'):
            app_logger = mock.MagicMock(logging.getLogger())
            w = worker.Worker(
                MQ_CONF, output_dir='/tmp/logs/', logger=app_logger)
            assert w._queue.name == 'worker.worker'
            assert w._config == {}
            # At this point connection should not happen
            assert w.connection.call_count == 0

            # We should get a warning noting unknown input
            assert app_logger.warn.call_count == 1

    def test_process(self):
        """
        Verify process works as expected.
        """
        with mock.patch('reworker.worker.Connection'):
            # A default use should raise NotImplementedError
            w = worker.Worker(MQ_CONF)
            self.assertRaises(NotImplementedError, w.process, **PROCESS_KWARGS)

            # An implemented process should not raise NotImplementedError
            w = DummyWorker(MQ_CONF,)
            assert w.process(**PROCESS_KWARGS) is None  # No return

    def test__process_with_dynamic_input(self):
        """
        Verify process with dynamic inputs work as expected.
        """
        # mocking the output since we are not testing it here

        with nested(
                mock.patch('reworker.worker.Connection'),
                mock.patch('reworker.worker.Output')) as (
                    _, mock_output):
            # An implemented process with proper inputs should not
            # raise NotImplementedError
            w = DynamicDummyWorker(MQ_CONF)
            w.notify = mock.MagicMock('notify')
            w.send = mock.MagicMock('send')
            assert w._process(**_PROCESS_KWARGS) is None  # No return
            assert w.notify.call_count == 2
            print w.send.call_args
            w.send.assert_called_with(
                'release.step',
                mock.ANY,
                {'status': 'failed'})

            # If the correct dynamic items are passed it should be a success
            w.send.reset_mock()
            w.notify.reset_mock()
            pa = _PROCESS_KWARGS
            body_tmp = pa['body']
            body_tmp['dynamic'] = {"item": "test"}
            pa['body'] = body_tmp
            assert w._process(**pa) is None  # No return

    def test__process(self):
        """
        Make sure the internal _process modifies inputs properly.
        """
        with mock.patch('reworker.worker.Connection'):
            # A default use should raise NotImplementedError due to w.process
            w = worker.Worker(MQ_CONF)
            self.assertRaises(
                NotImplementedError,
                w._process,
                **_PROCESS_KWARGS)

            # An implemented process should not raise
            # an exception with w._process
            w = DummyWorker(MQ_CONF)
            assert w._process(**_PROCESS_KWARGS) is None  # No return

    def test_run_forever(self):
        """
        Verify run_forever kicks off the ioloop.
        """
        with nested(
                mock.patch('reworker.worker.Connection'),
                mock.patch('reworker.worker.ConsumerMixin.run')):
            # Use the dummy worker to test
            w = DummyWorker(MQ_CONF)
            w.run_forever()
            # It should start
            assert w.run.called == 1
            # Since we mocked stuff it will fall into closing. Verify it closes
            # with the proper calls
            assert w.connection.release.called == 1

    def test_send(self):
        """
        Make sure that send executes the proper lower level calls.
        """
        with nested(
                mock.patch('reworker.worker.Connection'),
                mock.patch('reworker.worker.Producer')):
            w = DummyWorker(MQ_CONF)

            topic = 'topic'
            corr_id = '12345'
            exchange = 're'
            message = {'test': 'item'}

            w.send(topic, corr_id, message, exchange)
            assert w.producer.publish.call_count == 1

            body = w.producer.publish.call_args[0][0]
            kwargs = w.producer.publish.call_args[1]

            assert kwargs['exchange'] == exchange
            assert kwargs['routing_key'] == topic

            assert kwargs['app_id'] == "DummyWorker".lower()
            assert kwargs['correlation_id'] == corr_id
            assert body == json.dumps(message)

    def test_notify(self):
        """
        Make sure that send executes the proper lower level calls.
        """
        with nested(
                mock.patch('reworker.worker.Connection'),
                mock.patch('reworker.worker.Producer')):

            w = DummyWorker(MQ_CONF)
            w._process(**_PROCESS_KWARGS)

            assert w.producer.publish.call_count == 5
            assert 'Sent notification to' in w.app_logger.info.call_args[0][0]

    def test_notify_dev_nulls(self):
        """
        Make sure that notify dev null's things that should not be sent.
        """
        with nested(
                mock.patch('reworker.worker.Connection'),
                mock.patch('reworker.worker.Producer')):

            w = DynamicDummyWorker(MQ_CONF)

            w._process(**_PROCESS_KWARGS)

            assert w.producer.publish.call_count == 5
            assert 'No notifications to send' in (
                w.app_logger.debug.call_args[0][0])
