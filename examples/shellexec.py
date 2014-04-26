#!/usr/bin/env python
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
Simple example worker.
"""

import os

import subprocess

from reworker.worker import Worker


class ShellExec(Worker):
    """
    Simple worker which just executes a shell command.
    """

    def process(self, channel, basic_deliver, properties, body, output):
        """
        Executes a local shell command when requested. Only a hardcoded
        command is allowed in this example!
        """
        # Ack the original message
        self.ack(basic_deliver)
        corr_id = str(properties.correlation_id)
        # Notify we are starting
        self.send(properties.reply_to, corr_id, {'status': 'started'}, exchange='')

        # Start the ls
        command = ['/bin/ls', '-la']
        output.info('Command: %s' % " ".join(command))
        output.info('Location: %s' % os.getcwd())

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        # Record the results to our output stream
        for line in process.communicate():
            output.info(line[:-1])

        output.debug('return value: %s' % process.returncode)

        # Notify the final state based on the return code
        if process.returncode == 0:
            self.send(properties.reply_to, corr_id, {'status': 'completed'}, exchange='')
            # Notify on result. Not required but nice to do.
            self.notify(
                'ShellExec Executed Successfully',
                'ShellExec successfully executed %s. See logs.' % " ".join(
                    command),
                'completed',
                corr_id)

        else:
            self.send(properties.reply_to, corr_id, {'status': 'failed'}, exchange='')
            # Notify on result. Not required but nice to do.
            self.notify(
                'ShellExec Failed',
                'ShellExec failed trying to execute %s. See logs.' % " ".join(
                    command),
                'failed',
                corr_id)

        print "Handled a message"


if __name__ == '__main__':
    mq_conf = {
        'server': '127.0.0.1',
        'port': 5672,
        'vhost': '/',
        'user': 'guest',
        'password': 'guest',
    }
    worker = ShellExec(mq_conf, output_dir='/tmp/logs/')
    worker.run_forever()
