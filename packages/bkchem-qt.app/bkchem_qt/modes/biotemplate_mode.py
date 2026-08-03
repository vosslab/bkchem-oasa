"""Qt projection client for OASA-owned biomolecule template placement."""

# Standard Library
import math
import numbers

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class BioTemplateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Select a packaged biomolecule and submit one detached placement intent."""

	#============================================
	def __init__(
			self, view: object, parent: PySide6.QtCore.QObject | None = None,
			catalog: tuple[object, ...] | None = None,
			) -> None:
		"""Initialize the mode from immutable OASA-owned catalog descriptors."""
		super().__init__(view, parent)
		self._name = "biomolecule templates"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._biotemplate_action = None
		self._catalog = self._validate_catalog(catalog)
		self._by_key = {entry.catalog_key: entry for entry in self._catalog}
		self._category_keys = tuple(dict.fromkeys(entry.category for entry in self._catalog))
		self._category_labels = tuple(key.replace("_", " ").strip() for key in self._category_keys)
		self._category_label_to_key = dict(zip(self._category_labels, self._category_keys))
		self._current_catalog_key = self._catalog[0].catalog_key
		self._install_submodes(self._category_keys[0])

	#============================================
	def set_biotemplate_action(self, action: object | None) -> None:
		"""Install the plain session-owned biomolecule placement action."""
		if action is not None and not callable(action):
			raise TypeError("Biomolecule placement action must be callable")
		self._biotemplate_action = action

	#============================================
	def _validate_catalog(self, catalog: object) -> tuple[object, ...]:
		"""Validate plain descriptors without importing OASA's implementation type."""
		if not isinstance(catalog, tuple) or not catalog:
			raise ValueError("Biomolecule mode requires a nonempty immutable catalog")
		for entry in catalog:
			if any(
				not isinstance(getattr(entry, field, None), str)
				or not getattr(entry, field).strip()
				for field in ("catalog_key", "category", "subcategory", "name", "label")
			):
				raise ValueError("Biomolecule mode received an invalid catalog")
		if len({entry.catalog_key for entry in catalog}) != len(catalog):
			raise ValueError("Biomolecule mode catalog keys must be unique")
		return catalog

	#============================================
	def _entries_for_category(self, category: str) -> tuple[object, ...]:
		"""Return catalog entries in one selected category."""
		return tuple(entry for entry in self._catalog if entry.category == category)

	#============================================
	def _install_submodes(self, category: str) -> None:
		"""Render categories and labels while retaining only durable catalog keys."""
		entries = self._entries_for_category(category)
		self.submodes = [list(self._category_labels), [entry.catalog_key for entry in entries]]
		self.submodes_names = [list(self._category_labels), [entry.label for entry in entries]]
		self.submode = [self._category_keys.index(category), 0]
		self.group_layouts = ["row", "grid"]
		self.group_labels = ["Category", "Templates"]
		for entry in entries:
			self.tooltip_map[entry.catalog_key] = entry.name.replace("_", " ")
		if entries:
			self._current_catalog_key = entries[0].catalog_key

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Select a category or one immutable OASA catalog key."""
		if submode_index == 0:
			category = self._category_label_to_key.get(name)
			if category is None:
				self.status_message.emit("Unknown biomolecule category")
				return
			self._install_submodes(category)
			main_window = self._env.window
			if hasattr(main_window, "_submode_ribbon"):
				main_window._submode_ribbon.refresh_group(1)
		elif submode_index == 1 and name in self._by_key:
			self._current_catalog_key = name
			self.status_message.emit("Template: %s" % self._by_key[name].name)

	#============================================
	def activate(self) -> None:
		"""Describe the currently selected backend-owned template."""
		super().activate()
		entry = self._by_key.get(self._current_catalog_key)
		self.status_message.emit(
			"Biomolecule mode: %s" % entry.name if entry is not None
			else "Biomolecule mode: no template selected",
		)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Submit one detached placement at the event's finite scene anchor."""
		self._submit_biomolecule((scene_pos.x(), scene_pos.y()))

	#============================================
	def _submit_biomolecule(self, anchor: tuple[object, object]) -> None:
		"""Send exactly one plain revision-bound biomolecule request to the session."""
		if self._biotemplate_action is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		if self._current_catalog_key not in self._by_key:
			self.status_message.emit("No biomolecule template selected")
			return
		if (
			len(anchor) != 2 or any(
				isinstance(value, bool) or not isinstance(value, numbers.Real)
				or not math.isfinite(value) for value in anchor
			)
		):
			self.status_message.emit("Biomolecule anchor must use finite coordinates")
			return
		outcome = self._biotemplate_action(
			self._current_catalog_key, (float(anchor[0]), float(anchor[1])),
		)
		self.status_message.emit(outcome.message)
