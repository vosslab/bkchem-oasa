#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Runtime dependency preflight for BKChem launcher."""

import importlib
import sys

__all__ = [
  'MIN_PYTHON',
  'Pmw_available',
  'oasa_available',
  'python_version_ok',
  'python_version',
]


MIN_PYTHON = (3, 10)
python_version = "%d.%d.%d" % sys.version_info[0:3]
python_version_ok = sys.version_info[0:2] >= MIN_PYTHON


def _module_available( module_name):
  try:
    importlib.import_module( module_name)
  except ImportError:
    return 0
  return 1


Pmw_available = _module_available( "Pmw")
oasa_available = _module_available( "oasa")
