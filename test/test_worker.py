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
import pika

from reworker import worker

from . import TestCase, unittest

# Mocks
worker.pika = mock.MagicMock(pika)
logging = mock.MagicMock(logging)
worker.logging = logging

# Config
MQ_CONF = {
    'server': '127.0.0.1',
    'port': 5672,
    'vhost': '/',
    'user': 'guest',
    'password': 'guest',
}

# Default inputs
_PROCESS_KWARGS = {
    'channel': mock.MagicMock(pika.channel.Channel),
    'basic_deliver': mock.MagicMock(),
    'properties': mock.MagicMock(pika.spec.BasicProperties,
                                 correlation_id=1,
                                 reply_to='amq.gen-test'),
    'body': json.dumps({
        'notify': {
            'started': {
                'irc': ['#release-engine'],
            }
        },
        'group': 'test',
        'parameters': {},
        'dynamic': {}}),
}

PROCESS_KWARGS = {
    'output': logging.getLogger(),
}

PROCESS_KWARGS.update(_PROCESS_KWARGS)


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

    def tearDown(self):
        """
        Reset the mock.
        """
        worker.pika.SelectConnection.reset_mock()

    def test_create_object(self):
        """
        Test creation of a worker acts as expected.
        """
        w = worker.Worker(MQ_CONF)
        assert w._queue == 'worker.worker'
        assert w._consumer_tag is None
        assert w._config == {}
        assert worker.pika.SelectConnection.call_count == 1
        # Manually execute callbacks ...
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        # A channel should be created at this point
        assert w._channel is not None

        w = worker.Worker(
            MQ_CONF, config_file='test/config.json')
        assert w._config['a'] == 'test'

    def test_create_object_with_deprecated_input(self):
        """
        Test creation of a worker logs when deprecated inputs are used.
        """
        app_logger = mock.MagicMock(logging.getLogger())
        w = worker.Worker(
            MQ_CONF, output_dir='/tmp/logs/', logger=app_logger)
        assert w._queue == 'worker.worker'
        assert w._consumer_tag is None
        assert w._config == {}
        assert worker.pika.SelectConnection.call_count == 1
        # Manually execute callbacks ...
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        # A channel should be created at this point
        assert w._channel is not None
        # We should get a warning noting unknown input
        assert app_logger.warn.call_count == 1

    def test_process(self):
        """
        Verify process works as expected.
        """
        # A default use should raise NotImplementedError
        w = worker.Worker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))
        self.assertRaises(NotImplementedError, w.process, **PROCESS_KWARGS)

        # An implemented process should not raise NotImplementedError
        w = DummyWorker(MQ_CONF,)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))
        assert w.process(**PROCESS_KWARGS) is None  # No return

    def test__process_with_dynamic_input(self):
        """
        Verify process with dynamic inputs work as expected.
        """
        # mocking the output since we are not testing it here
        with mock.patch('reworker.worker.Output') as mock_output:
            # An implemented process with proper inputs should not
            # raise NotImplementedError
            w = DynamicDummyWorker(MQ_CONF)
            w._on_open(mock.MagicMock('connection'))
            w._on_channel_open(mock.MagicMock(pika.channel.Channel))
            w.notify = mock.MagicMock('notify')
            w.send = mock.MagicMock('send')
            assert w._process(**_PROCESS_KWARGS) is None  # No return
            self.assertEqual(w.notify.call_count, 0)
            w.send.assert_called_with(
                'amq.gen-test',
                '1',
                {'status': 'failed',
                 'data': "DynamicDummyWorker failed due to missing key: 'item'. Required Keys: "},
                exchange='')

            # If the correct dynamic items are passed it should be a success
            w.send.reset_mock()
            w.notify.reset_mock()
            pa = _PROCESS_KWARGS
            body_tmp = json.loads(pa['body'])
            body_tmp['dynamic'] = {"item": "test"}
            pa['body'] = json.dumps(body_tmp)
            assert w._process(**pa) is None  # No return

    def test__process(self):
        """
        Make sure the internal _process modifies inputs properly.
        """
        # A default use should raise NotImplementedError due to w.process
        w = worker.Worker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))
        self.assertRaises(NotImplementedError, w._process, **_PROCESS_KWARGS)

        # An implemented process should not raise an exception with w._process
        w = DummyWorker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))
        assert w._process(**_PROCESS_KWARGS) is None  # No return

    def test_run_forever(self):
        """
        Verify run_forever kicks off the ioloop.
        """
        # Use the dummy worker to test
        w = DummyWorker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        w.run_forever()
        # It should start
        assert w._connection.ioloop.start.called == 1
        # Since we mocked stuff it will fall into closing. Verify it closes
        # with the proper calls
        assert w._connection.ioloop.stop.called == 1
        assert w._connection.close.called == 1

    def test_send(self):
        """
        Make sure that send executes the proper lower level calls.
        """
        w = DummyWorker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        topic = 'topic'
        corr_id = '12345'
        exchange = 're'
        message = {'test': 'item'}

        w.send(topic, corr_id, message, exchange)
        assert w._channel.basic_publish.call_count == 1
        kwargs = w._channel.basic_publish.call_args[1]
        assert kwargs['exchange'] == exchange
        assert kwargs['routing_key'] == topic
        assert kwargs['body'] == json.dumps(message)

        assert kwargs['properties'].app_id == "DummyWorker".lower()
        assert kwargs['properties'].correlation_id == corr_id

    def test_notify(self):
        """
        Make sure that send executes the proper lower level calls.
        """
        w = DummyWorker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        w._process(**_PROCESS_KWARGS)

        self.assertEqual(w._channel.basic_publish.call_count, 4)
        assert 'Sent notification to' in w.app_logger.info.call_args[0][0]

    def test_notify_dev_nulls(self):
        """
        Make sure that notify dev null's things that should not be sent.
        """
        w = DynamicDummyWorker(MQ_CONF)
        w._on_open(mock.MagicMock('connection'))
        w._on_channel_open(mock.MagicMock(pika.channel.Channel))

        w._process(**_PROCESS_KWARGS)

        self.assertEqual(w._channel.basic_publish.call_count, 4)
