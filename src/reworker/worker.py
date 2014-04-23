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
The worker class.
"""

import json
import logging
import os.path

import pika
import pika.exceptions


class Worker(object):
    """
    Parent class for workers.
    """

    def __init__(self, mq_config, queue, output_dir='.', logger=None):
        """
        Creates an instance of a Worker.

        mq_config should house: user, password, server, port and vhost.
        queue is the name of the queue to use
        output_dir is the directory for process logs to be written to
        logger is an optional logger. Defaults to a logger to stderr
        """
        # NOTE: self.app_logger is the application level logger.
        #       This should not be used for user notification!
        self.app_logger = logger
        if not self.app_logger:
            self.app_logger = logging.getLogger(self.__class__.__name__)
            self.app_logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            handler.setLevel(logging.INFO)
            self.app_logger.addHandler(handler)
            self.app_logger.warn(
                'No app logger passed in. '
                'Defaulting to Streamandler with level INFO.')

        self._output_dir = os.path.realpath(output_dir)

        self._queue = queue
        self._consumer_tag = None

        creds = pika.PlainCredentials(mq_config['user'], mq_config['password'])

        # TODO: add ssl=True
        params = pika.ConnectionParameters(
            mq_config['server'],
            mq_config['port'],
            mq_config['vhost'],
            creds
        )
        self.app_logger.info(
            'Attemtping connection with amqp://%s:***@%s:%s%s' % (
                mq_config['user'], mq_config['server'],
                mq_config['port'], mq_config['vhost']))

        self._connection = pika.SelectConnection(
            parameters=params,
            on_open_callback=self._on_open)

    def _on_open(self, connection):
        """
        Call back when a connection is opened.
        """
        self.app_logger.debug('Attemtping to open channel...')
        self._connection.channel(self._on_channel_open)

    def _on_channel_open(self, channel):
        """
        Call back when a channel is opened.
        """
        self.app_logger.info('Connection and channel open.')
        self._channel = channel
        self.app_logger.debug('Attempting to start consuming...')
        self._consumer_tag = self._channel.basic_consume(
            self._process, queue=self._queue)
        self.app_logger.info('Consuming on queue %s' % self._queue)

    def ack(self, basic_deliver):
        """
        Shortcut for acking
        """
        self._channel.basic_ack(basic_deliver.delivery_tag)

    def notify(self, slug, message, phase, corr_id=None, exchange='re'):
        """
        Shortcut for sending a notification.

        slug is the short text to use in the notification
        message is a string which will be used in the notification
        phase is the phase to identify with in the notification
        corr_id is the correlation id. Default: None
        exchange is the exchange to publish on. Default: re
        """
        self.send(
            'notification',
            corr_id,
            {
                'slug': str(slug)[:80],
                'message': message,
                'phase': phase,
            }
        )

    def send(self, topic, corr_id, message_struct, exchange='re'):
        """
        Shortcut for sending messages back.

        topic is the topic the message will be sent to
        corr_id is the correlation id
        message_struct is a dictionary or list which will become json and sent
        exchange is the exchange to publish on. Default: re
        """
        props = pika.spec.BasicProperties()
        props.app_id = str(self.__class__.__name__)
        props.correlation_id = str(corr_id)

        self._channel.basic_publish(
            exchange=exchange,
            routing_key=topic,
            body=json.dumps(message_struct),
            properties=props)

    def _process(self, channel, basic_deliver, properties, body):
        """
        Internal processing that happens before subclass starts processing.
        """
        try:
            body = json.loads(body)
            corr_id = str(properties.correlation_id)
            # Create an output logger for sending results
            output = logging.getLogger(corr_id)
            output.setLevel(logging.DEBUG)
            handler = logging.FileHandler(os.path.sep.join([
                self._output_dir, corr_id + ".log"]))
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)
            output.addHandler(handler)
            # Execute
            output.debug('Starting %s.%s' % (self.__class__.__name__, corr_id))
            self.process(channel, basic_deliver, properties, body, output)
            output.debug('Finished %s.%s' % (self.__class__.__name__, corr_id))
        except ValueError, vex:
            self.app_logger.error('Could not parse msg. Rejecting. %s: %s' % (
                type(vex), vex))
            self._channel.basic_reject(
                basic_deliver.delivery_tag, requeue=False)

    def process(self, channel, basic_deliver, properties, body, output):
        """
        Subclass must override this to implement their logic.

        **Note**: Body is already loaded json.
        """
        raise NotImplementedError('process must be implemented.')

    def run_forever(self):
        """
        Run forever ... or until someone makes it stop.
        """
        try:
            self.app_logger.debug('Starting the IOLoop.')
            self._connection.ioloop.start()
        except AttributeError, aex:
            self.app_logger.fatal(
                'Can not recover from AttributeError raised during '
                'run_forver: %s' % aex)
        except KeyboardInterrupt:
            self.app_logger.info('KeyboardInterrupt sent.')
        except pika.exceptions.IncompatibleProtocolError, ipex:
            self.app_logger.fatal('No connection or incompatible protocol.')

        self.app_logger.debug('Stopping the IOloop.')
        self._connection.ioloop.stop()
        self.app_logger.debug('Closing the connection.')
        try:
            self._connection.close()
        except AttributeError, aex:
            self.app_logger.debug('Connection could not be closed: %s' % aex)
        self.app_logger.info('Exiting...')
