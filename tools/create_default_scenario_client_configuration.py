# Imperialism remake
# Copyright (C) 2014-16 Trilarion
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Generate the default scenario client configuration file.
"""

import os
os.chdir('..')

from lib import utils
from base import constants

config = {
    constants.ClientConfiguration.OVERVIEW_WIDTH: 300
}

# save
file = constants.SCENARIO_CLIENT_STANDARD_FILE
print(('write to {}'.format(file)))
utils.write_as_yaml(file, config)