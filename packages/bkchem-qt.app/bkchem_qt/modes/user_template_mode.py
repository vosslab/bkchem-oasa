"""Qt projection client for detached user-template placement."""

# Standard Library
import math
import numbers

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class UserTemplateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Select one plain user template and submit one detached placement intent."""

	#============================================
	def __init__(
			self, view: object, parent: PySide6.QtCore.QObject | None = None,
			catalog: tuple[object, ...] = (),
			) -> None:
		"""Initialize the mode from immutable plain catalog descriptors."""
		super().__init__(view, parent)
		self._name = "user templates"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._user_template_action = None
		self._catalog = ()
		self._labels_by_key = {}
		self._current_catalog_key = None
		self.set_catalog(catalog)

	#============================================
	def set_user_template_action(self, action: object | None) -> None:
		"""Install or clear the session-owned detached-placement action."""
		if action is not None and not callable(action):
			raise TypeError("User template placement action must be callable")
		self._user_template_action = action

	#============================================
	def _validate_catalog(self, catalog: object) -> tuple[tuple[str, str], ...]:
		"""Copy only required plain descriptor fields into mode-owned data."""
		if not isinstance(catalog, tuple):
			raise ValueError("User template mode requires an immutable catalog")
		entries = []
		for entry in catalog:
			catalog_key = getattr(entry, "catalog_key", None)
			label = getattr(entry, "label", None)
			if (
				not isinstance(catalog_key, str) or not catalog_key.strip()
				or not isinstance(label, str) or not label.strip()
			):
				raise ValueError("User template mode received an invalid catalog entry")
			entries.append((catalog_key, label))
		if len({catalog_key for catalog_key, _label in entries}) != len(entries):
			raise ValueError("User template mode catalog keys must be unique")
		return tuple(entries)

	#============================================
	def set_catalog(self, catalog: tuple[object, ...]) -> None:
		"""Replace catalog projection while retaining a still-valid selected key."""
		entries = self._validate_catalog(catalog)
		previous_key = self._current_catalog_key
		self._catalog = entries
		self._labels_by_key = dict(entries)
		if previous_key in self._labels_by_key:
			self._current_catalog_key = previous_key
		elif entries:
			self._current_catalog_key = entries[0][0]
		else:
			self._current_catalog_key = None
		self._install_submodes()

	#============================================
	def _install_submodes(self) -> None:
		"""Render one Template group from catalog keys and labels."""
		self.submodes = [[catalog_key for catalog_key, _label in self._catalog]]
		self.submodes_names = [[label for _catalog_key, label in self._catalog]]
		self.submode = [
			self.submodes[0].index(self._current_catalog_key)
			if self._current_catalog_key is not None else 0
		]
		self.group_labels = ["Template"]
		self.group_layouts = ["row"]

	#============================================
	@property
	def catalog_keys(self) -> tuple[str, ...]:
		"""Return the current immutable opaque catalog keys."""
		catalog_keys = tuple(catalog_key for catalog_key, _label in self._catalog)
		return catalog_keys

	#============================================
	@property
	def current_catalog_key(self) -> str | None:
		"""Return the selected opaque key, if an entry is available."""
		return self._current_catalog_key

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return the interaction hint for the current availability state."""
		if self._current_catalog_key is None:
			return "User template mode: no templates available"
		return "Click to place detached user template"

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Select one key from the sole Template group."""
		if submode_index != 0:
			return
		if name not in self._labels_by_key:
			self.status_message.emit("Unknown user template")
			return
		self._current_catalog_key = name
		self.status_message.emit("Template: %s" % self._labels_by_key[name])

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Submit one detached placement at the exact scene click coordinate."""
		self._submit_user_template((scene_pos.x(), scene_pos.y()))

	#============================================
	def _submit_user_template(self, anchor: tuple[object, object]) -> None:
		"""Send one selected key and finite anchor to the owning session."""
		if self._current_catalog_key is None:
			self.status_message.emit("No user templates available")
			return
		if self._user_template_action is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		if (
			len(anchor) != 2 or any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value) for value in anchor
			)
		):
			self.status_message.emit("User template anchor must use finite coordinates")
			return
		outcome = self._user_template_action(
			self._current_catalog_key, (float(anchor[0]), float(anchor[1])),
		)
		self.status_message.emit(outcome.message)
