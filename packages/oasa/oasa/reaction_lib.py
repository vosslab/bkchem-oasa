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

from oasa.molecule_lib import Molecule as molecule



class Reaction(object):
  """Reaction representation.

  """
  def __init__( self, reactants: object = None, products: object = None, reagents: object = None) -> None:
    self.reactants = reactants or []
    self.products = products or []
    self.reagents = reagents or []


  def __str__(self) -> str:
    s = "\nreactants:\n"
    for i in self.reactants:
      s += "    {0}\n".format(i)
    s += "reagents:\n"
    for i in self.reagents:
      s += "    {0}\n".format(i)
    s += "products:\n"
    for i in self.products:
      s += "    {0}\n".format(i)

    return s



class ReactionComponent(object):
  """Represents one component of a reaction.

  """
  def __init__( self, mol: object = None, stoichiometry: object = 1) -> None:
    self.stoichiometry = stoichiometry
    self.molecule = mol


  @property
  def molecule(self) -> object:
    return self._molecule


  @molecule.setter
  def molecule(self, mol: object) -> None:
    assert isinstance(mol, molecule)
    self._molecule = mol


  @property
  def stoichiometry(self) -> object:
    return self._stoichiometry


  @stoichiometry.setter
  def stoichiometry(self, stoich: object) -> None:
    assert isinstance(stoich, (int, float))
    self._stoichiometry = stoich


  def __str__( self) -> str:
    return "%s * (%s)" % (self.stoichiometry, self.molecule)


reaction_component = ReactionComponent
