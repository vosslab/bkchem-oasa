"""Template mode for applying molecular templates."""

# Standard Library
import math
import numbers

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item

#============================================
class TemplateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing molecular group templates.

	Renders OASA-supplied template names and allows the user to click on the
	canvas to place a detached template at that
	position, or click on an existing atom to place a separate template at
	that atom's anchor. Attachment and fusion use a future operation.

	Args:
		view: The ChemView widget that dispatches events.
		template_names: Immutable plain names supplied by the document-session
			backend boundary.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(
			self, view: object, parent: PySide6.QtCore.QObject | None = None,
			template_names: tuple[str, ...] | None = None,
			) -> None:
		"""Initialize template mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
			template_names: Immutable plain names supplied by DocumentSession.
		"""
		super().__init__(view, parent)
		self._name = "Template"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._current_template = None
		self._template_names = self._validate_template_names(template_names)
		self._persistent_operation = None
		self._install_template_submodes()

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install the session-owned immutable persistent-operation callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Template persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return template mode interaction hint for the status bar.

		Returns:
			A short description of available template interactions.
		"""
		return "Click to place detached template | Click atom to anchor separate template"

	# ------------------------------------------------------------------
	# Template management
	# ------------------------------------------------------------------

	#============================================
	def _validate_template_names(self, template_names: object) -> tuple[str, ...]:
		"""Return the required immutable system-template selection values."""
		if not isinstance(template_names, tuple) or not template_names:
			raise ValueError("Template mode requires a non-empty immutable catalog")
		if (
			any(not isinstance(name, str) or not name for name in template_names)
			or len(set(template_names)) != len(template_names)
		):
			raise ValueError("Template mode received an invalid template catalog")
		return template_names

	#============================================
	def _install_template_submodes(self) -> None:
		"""Render the validated catalog while retaining only a selected name."""
		self.submodes = [list(self._template_names)]
		self.submodes_names = [list(self._template_names)]
		self.submode = [0]
		self.group_labels = ["Templates"]
		self.group_layouts = ["grid"]
		self._current_template = self._template_names[0]

	#============================================
	def set_template(self, name: str) -> None:
		"""Set the current template by name.

		Args:
			name: Name of the template to activate.
		"""
		if name in self._template_names:
			self._current_template = name
			self.status_message.emit(f"Template: {name}")
		else:
			self.status_message.emit("Unknown template name")

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Handle submode switch by selecting the named template.

		Args:
			submode_index: Group index (always 0 for templates).
			name: Template name selected.
		"""
		if submode_index == 0:
			self.set_template(name)

	#============================================
	@property
	def template_names(self) -> tuple[str, ...]:
		"""Return immutable available template names.

		Returns:
			List of template name strings.
		"""
		return self._template_names

	# ------------------------------------------------------------------
	# Event handlers
	# ------------------------------------------------------------------

	#============================================
	def activate(self) -> None:
		"""Called when this mode becomes active."""
		super().activate()
		if self._current_template:
			msg = f"Template mode: {self._current_template}"
		else:
			msg = "Template mode: no template selected"
		self.status_message.emit(msg)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Handle a mouse press to place a detached template.

		If clicked on an existing atom, places a separate template at that
		atom's anchor. If clicked on empty space, places a detached template
		at that position. The document session owns preparation, commit,
		history, and projection replacement.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_template is None:
			self.status_message.emit("No template selected")
			return
		item = self._item_at(scene_pos)
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			atom_model = item.atom_model
			molecule = self._env.find_molecule_for_atom(atom_model)
			molecule_id = getattr(molecule, "mol_id", None)
			atom_id = atom_model.backend_durable_id
			if not molecule_id or not atom_id:
				self.status_message.emit("Selected atom has no durable backend identity")
				return
			self._submit_template(anchor=(atom_model.x, atom_model.y))
			return
		self._submit_template(anchor=(scene_pos.x(), scene_pos.y()))

	# ------------------------------------------------------------------
	# Placement helpers
	# ------------------------------------------------------------------

	#============================================
	def _place_template(self, x: float, y: float) -> None:
		"""Submit a detached template placement at one scene-point anchor.

		This compatibility entry point is also backend-authoritative: it
		captures only finite scalar coordinates and delegates the complete
		persistent transaction to the installed document-session callback.
		"""
		self._submit_template(anchor=(x, y))

	#============================================
	def _submit_template(self, anchor: tuple[object, object]) -> None:
		"""Submit one immutable detached-template intent to the session."""
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		template_name = self._current_template
		if not isinstance(template_name, str) or not template_name:
			self.status_message.emit("No template selected")
			return
		if (
			len(anchor) != 2
			or any(
				isinstance(value, bool)
				or not isinstance(value, numbers.Real)
				or not math.isfinite(value)
				for value in anchor
			)
		):
			self.status_message.emit("Template anchor must use finite coordinates")
			return
		owner = getattr(self._persistent_operation, "__self__", None)
		snapshot = getattr(owner, "backend_snapshot", None)
		if snapshot is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"template.insert", "Place Template",
			(
				("expected_revision", snapshot.revision),
				("template_name", template_name),
				("anchor", (float(anchor[0]), float(anchor[1]))),
			),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
