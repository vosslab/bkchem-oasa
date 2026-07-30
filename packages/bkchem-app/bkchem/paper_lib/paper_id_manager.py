"""Canvas ID registration mixin methods for BKChem paper."""

from warnings import warn


class PaperIdManagerMixin:
	"""Canvas ID-to-object registration helpers extracted from paper.py."""

	def register_id( self, id: object, object: object) -> None:
		self._id_2_object[ id] = object


	def unregister_id( self, id: object) -> None:
		try:
			del self._id_2_object[ id]
		except KeyError:
			warn( 'trying to unregister not registered id', UserWarning, 3)


	def id_to_object( self, id: object) -> object:
		try:
			return self._id_2_object[ id]
		except KeyError:
			return None


	def object_to_id( self, obj: object) -> object:
		for k, v in list(self._id_2_object.items()):
			if v == obj:
				return k
		return None


	def is_registered_object( self, o: object) -> bool:
		"""has this object a registered id?"""
		return o in list(self._id_2_object.values())


	def is_registered_id( self, id: object) -> bool:
		return id in list(self._id_2_object.keys())
