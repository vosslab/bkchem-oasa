"""Mode environment providing dependency injection for interaction modes.

Bundles view, scene, document, and undo_stack access behind a single
object so modes do not need repeated hasattr() guards or deep navigation
through self._view.  Properties resolve lazily on each access since the
underlying objects (scene, document) can change at runtime.
"""

# local repo modules
import bkchem_qt.canvas.scene_queries


#============================================
class ModeEnvironment:
	"""Thin facade bundling mode dependencies from the view.

	All properties resolve lazily through the view reference so that
	document replacement, scene changes, etc. are automatically reflected.

	Args:
		view: The ChemView widget that owns the modes.
	"""

	#============================================
	def __init__(self, view: object) -> None:
		"""Initialize with a view reference.

		Args:
			view: The ChemView widget.
		"""
		self._view = view

	# ------------------------------------------------------------------
	# Core accessors
	# ------------------------------------------------------------------

	#============================================
	@property
	def view(self) -> object:
		"""Return the ChemView widget."""
		return self._view

	#============================================
	@property
	def scene(self) -> object:
		"""Return the current QGraphicsScene or None."""
		return self._view.scene()

	#============================================
	@property
	def document(self) -> object:
		"""Return the current Document or None."""
		if hasattr(self._view, "document"):
			return self._view.document
		return None

	#============================================
	@property
	def undo_stack(self) -> object:
		"""Return the document's QUndoStack or None."""
		return bkchem_qt.canvas.scene_queries.find_undo_stack(self._view)

	#============================================
	@property
	def window(self) -> object:
		"""Return the parent main window or None."""
		return self._view.window()

	# ------------------------------------------------------------------
	# Query helpers (delegate to scene_queries)
	# ------------------------------------------------------------------

	#============================================
	def find_molecule_for_atom(self, atom_model: object) -> object:
		"""Find the MoleculeModel containing an atom.

		Args:
			atom_model: The AtomModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		return bkchem_qt.canvas.scene_queries.find_molecule_for_atom(
			self._view, atom_model
		)

	#============================================
	def find_molecule_for_bond(self, bond_model: object) -> object:
		"""Find the MoleculeModel containing a bond.

		Args:
			bond_model: The BondModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		return bkchem_qt.canvas.scene_queries.find_molecule_for_bond(
			self._view, bond_model
		)

	#============================================
	def find_connected_bond_items(self, atom_model: object) -> list:
		"""Find all BondItems connected to an atom.

		Args:
			atom_model: The AtomModel whose bonds to find.

		Returns:
			List of (BondModel, BondItem) tuples.
		"""
		return bkchem_qt.canvas.scene_queries.find_connected_bond_items(
			self.scene, atom_model
		)
