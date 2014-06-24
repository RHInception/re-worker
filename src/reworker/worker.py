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
import datetime
import pika
import pika.exceptions

from reworker.output import Output


class Worker(object):
    """
    Parent class for workers.
    """

    #: All inputs which should be passed in via body['dynamic'][ITEM]
    dynamic = ()

    def __init__(self, mq_config, config_file=None,
                 logger=None, **kwargs):
        """
        Creates an instance of a Worker.

        mq_config should house: user, password, server, port and vhost.
        config_file is an optional full path to a json config file
        logger is an optional logger. Defaults to a logger to stderr
        **kwargs is all other keyword arguments
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

        if kwargs:
            for key in kwargs.keys():
                self.app_logger.warn('Unknown key %s passed to %s.' % (
                    key, self.__class__.__name__))

        self._config = {}
        self.__notify_cfg = {}
        if config_file:
            with open(os.path.realpath(os.path.expanduser(
                    config_file)), 'r') as f_obj:
                self._config = json.load(f_obj)

        if self._config.get('queue', None):
            # This worker is setting a custom queue name. Probably to
            # differentiate from other workers with similar names.
            _queue_suffix = self._config.get('queue')
        else:
            # No special naming requested. Leave the instance suffix alone
            _queue_suffix = self.__class__.__name__.lower()

        self._queue = "worker.%s" % _queue_suffix
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

    def notify(
            self, slug, message, phase, corr_id=None,
            target=None, exchange='re'):
        """
        Shortcut for sending a notification.

        slug is the short text to use in the notification
        message is a string which will be used in the notification
        phase is the phase to identify with in the notification
        corr_id is the correlation id. Default: None
        *target is deprecated*!
        exchange is the exchange to publish on. Default: re
        """
        this_phase = self.__notify_cfg.get(phase, {})
        if target:
            self.app_logger.warn(
                'notify should no longer be passed a target. Ignoring...')

        if this_phase:
            for topic_suffix in this_phase.keys():
                notify_topic = 'notify.%s' % topic_suffix
                target = this_phase[topic_suffix]
                self.send(
                    notify_topic,
                    corr_id,
                    {
                        'slug': str(slug)[:80],
                        'message': message,
                        'phase': phase,
                        'target': target,
                    }
                )
                self.app_logger.info('Sent notification to %s for phase %s' % (
                    notify_topic, phase))
        else:
            self.app_logger.debug(
                'No notifications to send for phase %s' % phase)

    def send(self, topic, corr_id, message_struct, exchange='re'):
        """
        Shortcut for sending messages back.

        topic is the topic the message will be sent to
        corr_id is the correlation id
        message_struct is a dictionary or list which will become json and sent
        exchange is the exchange to publish on. Default: re
        """
        props = pika.spec.BasicProperties()
        props.app_id = str(self.__class__.__name__.lower())
        props.correlation_id = str(corr_id)

        self._channel.basic_publish(
            exchange=exchange,
            routing_key=topic,
            body=json.dumps(message_struct),
            properties=props)

    def reject(self, basic_deliver, requeue=False):
        """
        Reject the message with the given `basic_deliver`
        """
        self._channel.basic_reject(basic_deliver.delivery_tag,
                                   requeue=requeue)

    def _process(self, channel, basic_deliver, properties, body):
        """
        Internal processing that happens before subclass starts processing.
        """
        class_name = self.__class__.__name__
        try:
            body = json.loads(body)
            corr_id = str(properties.correlation_id)
            # Hold the notification confing for this execution
            self.__notify_cfg = body.get('notify', {})
            # Create an output logger for sending results
            output = Output(self.send, corr_id)
            output.setLevel(self._config.get('OUTPUT_LEVEL', 'DEBUG'))
            # Execute
            output.debug('Starting %s.%s - %s' % (
                class_name,
                corr_id,
                str(datetime.datetime.now())
            ))
            try:
                self.process(channel, basic_deliver, properties, body, output)
            except KeyError, ke:
                output.debug(
                    'An expected key in the message for %s for %s was '
                    'missing: %s. Required keys: %s - %s' % (
                        corr_id,
                        class_name,
                        ke,
                        ",".join(self.dynamic),
                        str(datetime.datetime.now())))
                self.send('release.step', corr_id, {'status': 'failed'})
                # Notify on result. Not required but nice to do.
                self.notify(
                    '%s Failed' % class_name,
                    '%s failed due to missing key: %s. Required Keys: %s' % (
                        class_name, ke, ",".join(self.dynamic)),
                    'failed',
                    corr_id=corr_id)
            output.debug('Finished %s.%s - %s\n\n' % (
                class_name,
                corr_id,
                str(datetime.datetime.now())))
        except ValueError, vex:
            self.app_logger.error('Could not parse msg. Rejecting. %s: %s' % (
                type(vex), vex))
            self.send('release.step', corr_id, {'status': 'failed'})
            # Notify on result. Not required but nice to do.
            self.notify(
                '%s Failed' % class_name,
                '%s failed trying to parse message' % class_name,
                'failed',
                corr_id=corr_id)
            self.reject(basic_deliver, False)
        # Force empty __notify_cfg
        self.__notify_cfg = {}

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
        except pika.exceptions.IncompatibleProtocolError:
            self.app_logger.fatal('No connection or incompatible protocol.')

        self.app_logger.debug('Stopping the IOloop.')
        self._connection.ioloop.stop()
        self.app_logger.debug('Closing the connection.')
        try:
            self._connection.close()
        except AttributeError, aex:
            self.app_logger.debug('Connection could not be closed: %s' % aex)
        self.app_logger.info('Exiting...')


def runner(WorkerCls):
    """
    Helper function for running a worker.

    WorkerCls is the Worker Class to run.
    """
    import os.path
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        'mq_config',
        metavar='MQ_CONFIG',
        type=str,
        nargs=1,
        help='The Message Queue configuration file.')

    parser.add_argument(
        '-w', '--worker-config',
        type=str,
        required=False,
        help='Optional full path to worker specific configuration file.',
        default=None)

    args = parser.parse_args()
    try:
        mq_conf = json.load(open(args.mq_config[0], 'r'))
        worker = WorkerCls(
            mq_conf,
            config_file=args.worker_config)
        worker.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception, ex:
        print "Error: %s %s" % (type(ex), ex)
        print "exiting..."
        raise SystemExit(1)
