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

from reworker import utils

from . import TestCase, unittest




class TestUtil(TestCase):
    """
    Tests for the util module.
    """

    def test_step_to_notification_format(self):
        """
        Verify step format translates to notification format.
        """
        result = utils.step_to_notification_format({
            'parameters': {
                'slug': 'slug',
                'message': 'message',
                'phase': 'phase',
                'target': ['target'],
            }
        })

        assert result == {
            'slug': 'slug',
            'message': 'message',
            'phase': 'phase',
            'target': ['target'],
        }
