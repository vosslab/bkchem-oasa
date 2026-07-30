#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------

from oasa.molecule_lib import Molecule as molecule_class



class Config (object):
  """Singleton class for library wide configuration.

  ``molecule_class`` remains as a compatibility fallback for external legacy
  callers. New frontend code must inject a molecule factory or root molecule
  into stateful parsers instead of changing this process-wide setting.

  """
  inchi_binary_path = "/usr/bin/inchi-1"

  molecule_class = molecule_class

  @classmethod
  def create_molecule(self: object) -> object:
    return self.molecule_class()
