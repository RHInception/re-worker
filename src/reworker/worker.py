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

import logging
import pika


class Worker(object):
    """
    Parent class for workers.
    """

    def __init__(self, mq_config, queue, logger=None):
        """
        Creates an instance of a Worker.

        mq_config should house: user, password, server, port and vhost.
        queue is the name of the queue to use
        logger is optional.
        """
        # NOTE: self.logger is the application level logger. This should not
        #       be used for user notification!
        self.logger = logger
        if not self.logger:
            # TODO: Make a sane default logger.
            self.logger = logging.getLogger(self.__class__.__name__)

        self._queue = queue
        self._consumer_tag = None

        creds = pika.PlainCredentials(mq_config['user'], mq_config['password'])

        # TODO: add ssl=True
        params = pika.ConnectionParameters(
            mq_config['server'],
            mq_config['port'],
            mq_config['vhost'],
            mq_config['creds'],
        )
        self.logger.info(
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
        #self.logger.debug('Attemtping to open channel...')
        self._connection.channel(self._on_channel_open)

    def _on_channel_open(self, channel):
        """
        Call back when a channel is opened.
        """
        #self.logger.info('Connection and channel open.')
        self._channel = channel
        #self.logger.debug('Attempting to start consuming...')
        self._consumer_tag = self._channel.basic_consume(
            self._process, queue=self._queue)
        #self.logger.info('Consuming on queue %s' % self._queue)

    def _process(self, channel, basic_deliver, properties, body):
        """
        Internal processing that happens before subclass starts processing.
        """
        self.process(channel, basic_deliver, properties, body)

    def ack(self, basic_deliver):
        """
        Shortcut for acking
        """
        self._channel.basic_ack(basic_deliver.delivery_tag)

    def process(self, channel, basic_deliver, properties, body):
        """
        Subclass must override this to implement their logic.
        """
        raise NotImplementedError('process must be implemented.')

    def run_forever(self):
        """
        Run forever ... or until someone makes it stop.
        """
        try:
            self.logger.debug('Starting the IOLoop.')
            self._connection.ioloop.start()
        except KeyboardInterrupt:
            self.logger.info('KeyboardInterrupt sent.')
        except Exception, ex:
            self.logger.error('Error %s: %s' % (str(ex), ex))

        self.logger.debug('Stopping the IOloop.')
        self._connection.ioloop.stop()
        self.logger.debug('Closing the connection.')
        self._connection.close()
        self.logger.info('Exiting...')
