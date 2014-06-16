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


class Output(object):
    """
    Output class which acts similar to a logger but publishes to the bus.
    """

    def __init__(self, send_meth, corr_id, level='INFO'):
        """
        Creates an instance of Output.

        send_meth is the Worker.send method.
        corr_id is the correlation id.
        """
        self.send = send_meth
        self.corr_id = corr_id
        self._level = logging.getLevelName('INFO')  # Default to INFO
        self.setLevel(level)

    def setLevel(self, level):
        """
        Level like setter. Ignores unknown levels.
        """
        level = level.upper()
        if level in (
                'DEBUG', 'INFO', 'ERROR', 'WARN',
                'WARNING', 'CRITICAL', 'FATAL'):
            self._level = logging.getLevelName(level)

    def log(self, level, message):
        """
        'Logs' to the bus.

        level string to log at (like 'info')
        message is the textual messae
        """
        if logging.getLevelName(level) >= self._level:
            body = {
                'message': message,
            }
            self.send('output', self.corr_id, body)

    # Specific level calls
    debug = lambda s, m: s.log('DEBUG', m)
    info = lambda s, m: s.log('INFO', m)
    error = lambda s, m: s.log('ERROR', m)
    warn = lambda s, m: s.log('WARN', m)
    warning = lambda s, m: s.log('WARNING', m)
    critical = lambda s, m: s.log('CRITICAL', m)
    fatal = lambda s, m: s.log('FATAL', m)
