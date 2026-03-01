"""Document model holding molecules and providing undo support."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import bkchem_qt.models.molecule_model


#============================================
class Document(PySide6.QtCore.QObject):
	"""Top-level document that holds molecules, file state, and undo stack.

	Emits ``modified_changed`` whenever the dirty flag transitions so the
	window title can show an unsaved-changes indicator.

	Args:
		parent: Optional parent QObject.
	"""

	# emitted when the dirty flag changes
	modified_changed = PySide6.QtCore.Signal(bool)

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject = None):
		"""Initialize an empty document.

		Args:
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._molecules = []
		self._file_path = None
		self._dirty = False
		self._undo_stack = PySide6.QtGui.QUndoStack(self)

	# ------------------------------------------------------------------
	# Properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def molecules(self) -> list:
		"""Return the list of MoleculeModel instances in this document.

		Returns:
			List of MoleculeModel objects.
		"""
		return list(self._molecules)

	#============================================
	@property
	def file_path(self):
		"""Absolute path to the saved file, or None if unsaved.

		Returns:
			str or None.
		"""
		return self._file_path

	#============================================
	@file_path.setter
	def file_path(self, value):
		self._file_path = value

	#============================================
	@property
	def dirty(self) -> bool:
		"""Whether the document has unsaved changes."""
		return self._dirty

	#============================================
	@dirty.setter
	def dirty(self, value: bool):
		new_value = bool(value)
		if new_value != self._dirty:
			self._dirty = new_value
			self.modified_changed.emit(self._dirty)

	#============================================
	@property
	def undo_stack(self) -> PySide6.QtGui.QUndoStack:
		"""The QUndoStack for undo/redo operations.

		Returns:
			QUndoStack instance owned by this document.
		"""
		return self._undo_stack

	# ------------------------------------------------------------------
	# Mutation
	# ------------------------------------------------------------------

	#============================================
	def add_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel):
		"""Add a molecule to the document.

		Args:
			mol_model: MoleculeModel to add.
		"""
		self._molecules.append(mol_model)
		self.dirty = True

	#============================================
	def remove_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel):
		"""Remove a molecule from the document.

		Args:
			mol_model: MoleculeModel to remove.

		Raises:
			ValueError: If the molecule is not in the document.
		"""
		self._molecules.remove(mol_model)
		self.dirty = True

	#============================================
	def clear(self):
		"""Remove all molecules and reset the document to empty state."""
		self._molecules.clear()
		self._undo_stack.clear()
		self.dirty = False

	# ------------------------------------------------------------------
	# File info
	# ------------------------------------------------------------------

	#============================================
	def title(self) -> str:
		"""Return a display title for the document.

		Uses the filename from ``file_path`` if available, otherwise
		returns 'Untitled'.

		Returns:
			Title string.
		"""
		if self._file_path:
			basename = os.path.basename(self._file_path)
			return basename
		return "Untitled"

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		n_mols = len(self._molecules)
		title = self.title()
		return f"Document('{title}', {n_mols} molecules)"
