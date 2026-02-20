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

from random import randint



class id_manager(object):
	"""Manages bidirectional mapping between string IDs and objects.

	Maintains two dictionaries for O(1) lookup in both directions:
	id_map maps ID strings to objects, and obj_map maps objects to
	their ID strings.
	"""

	#============================================
	def __init__(self):
		"""Initialize empty ID and object maps."""
		# forward index: ID string -> object
		self.id_map = {}
		# reverse index: object -> ID string
		self.obj_map = {}

	#============================================
	def register_id(self, obj: object, Id: str) -> None:
		"""Register an object with a given ID string.

		Args:
			obj: The object to register.
			Id: The ID string to associate with the object.

		Raises:
			ValueError: If the object is already registered.
		"""
		if obj in self.obj_map:
			raise ValueError("Object is already registered " + str(obj))
		self.id_map[Id] = obj
		self.obj_map[obj] = Id

	#============================================
	def unregister_id(self, Id: str, obj: object) -> None:
		"""Remove a registration by ID, verifying the object matches.

		Args:
			Id: The ID string to unregister.
			obj: The object that should correspond to the ID.

		Raises:
			ValueError: If the ID is not registered or does not match the object.
		"""
		if Id not in self.id_map:
			raise ValueError(f"Id {Id} is not registered")
		if self.id_map[Id] != obj:
			raise ValueError("Id and object do not correspond")
		del self.id_map[Id]
		del self.obj_map[obj]

	#============================================
	def get_object_with_id(self, Id: str) -> object:
		"""Return the object registered under the given ID.

		Args:
			Id: The ID string to look up.

		Returns:
			The object associated with the ID.

		Raises:
			KeyError: If the ID is not registered.
		"""
		return self.id_map[Id]

	#============================================
	def get_object_with_id_or_none(self, Id: str) -> object:
		"""Return the object registered under the given ID, or None.

		Args:
			Id: The ID string to look up.

		Returns:
			The object associated with the ID, or None if not found.
		"""
		return self.id_map.get(Id, None)

	#============================================
	def generate_id(self, prefix: str = 'id') -> str:
		"""Generate a unique ID string with the given prefix.

		Args:
			prefix: The prefix for the generated ID.

		Returns:
			A unique ID string not currently in use.
		"""
		while True:
			Id = prefix + str(randint(1, 100000))
			if Id not in self.id_map:
				return Id

	#============================================
	def generate_and_register_id(self, obj: object, prefix: str = 'id') -> str:
		"""Generate a unique ID and register it with the given object.

		Args:
			obj: The object to register.
			prefix: The prefix for the generated ID.

		Returns:
			The newly generated and registered ID string.
		"""
		Id = self.generate_id(prefix=prefix)
		self.register_id(obj, Id)
		return Id

	#============================================
	def is_registered_object(self, obj: object) -> bool:
		"""Check whether an object is currently registered.

		Args:
			obj: The object to check.

		Returns:
			True if the object is registered, False otherwise.
		"""
		return obj in self.obj_map

	#============================================
	def get_id_of_object(self, obj: object) -> str:
		"""Return the ID string for a registered object, or None.

		Args:
			obj: The object to look up.

		Returns:
			The ID string, or None if the object is not registered.
		"""
		return self.obj_map.get(obj, None)

	#============================================
	def unregister_object(self, obj: object) -> None:
		"""Remove the registration for an object.

		Args:
			obj: The object to unregister.

		Raises:
			ValueError: If the object is not registered.
		"""
		self.unregister_id(self.get_id_of_object(obj), obj)
