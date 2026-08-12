"""Submode button ribbon for BKChem-Qt.

Displays submode buttons in a horizontal ribbon below the mode toolbar.
When the active mode changes, the ribbon is rebuilt to show that mode's
submode groups (row buttons, grid buttons, or a mix).  This mirrors the
Tk submode rendering in main_lib/main_modes.py.
"""

# PIP3 modules
import yaml
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.widgets.icon_loader
import bkchem_qt.resource_paths


# Package-owned modes.yaml supplies grid layout metadata.
_MODES_YAML_PATH = bkchem_qt.resource_paths.get_resource_path("modes.yaml")
_GRID_RESIZE_REBUILD_THRESHOLD = 24
_GRID_FALLBACK_MIN_WIDTH = 120
_GRID_BUTTON_PADDING = 26


#============================================
class SubModeRibbon(PySide6.QtWidgets.QWidget):
	"""Horizontal ribbon of submode buttons that updates per mode.

	When a mode is activated, call rebuild() to tear down old buttons
	and create new ones from the mode's submode data. Emits
	submode_selected when a button is clicked.

	Args:
		parent: Optional parent widget.
	"""

	# emitted when a submode button is clicked, carries the submode key
	submode_selected = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Initialize the submode ribbon with an empty layout.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Ignored,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		self._layout = PySide6.QtWidgets.QHBoxLayout(self)
		self._layout.setContentsMargins(4, 2, 4, 2)
		self._layout.setSpacing(6)
		# stretch at the end to push buttons left
		self._layout.addStretch()
		# track group widgets for refresh_group()
		self._group_widgets = []
		# track extra widgets (labels, separators) for teardown
		self._extra_widgets = []
		# reference to current mode for refresh operations
		self._current_mode = None
		self._current_mode_name = ""
		self._last_grid_reflow_width = -1
		self._in_resize_reflow = False

	#============================================
	def rebuild(self, mode_name: str) -> None:
		"""Tear down current buttons and build new ones for the mode.

		Called when the active mode changes. Reads the mode's submode
		data (submodes, group_labels, group_layouts, icon_map, etc.)
		and creates the appropriate button groups.

		Args:
			mode_name: Name of the newly active mode (used to look up
				the mode object from the parent's mode manager).
		"""
		# resolve the mode object from the mode manager
		main_window = self.window()
		if not hasattr(main_window, '_mode_manager'):
			return
		mode = main_window._mode_manager.current_mode
		if mode is None:
			return
		self._current_mode = mode
		self._current_mode_name = str(mode_name)
		self._rebuild_from_mode(mode)

	#============================================
	def _rebuild_from_mode(self, mode: object) -> None:
		"""Build submode buttons from a mode's submode attributes.

		Args:
			mode: BaseMode instance with submode data attributes.
		"""
		# tear down all existing widgets
		self._clear_all()

		# if the mode has no submodes, hide the ribbon
		if not mode.submodes:
			self.setVisible(False)
			self._last_grid_reflow_width = self.width()
			return
		self.setVisible(True)

		for group_idx in range(len(mode.submodes)):
			# add separator or group label between groups
			label_text = ''
			if group_idx < len(mode.group_labels):
				label_text = mode.group_labels[group_idx]

			if label_text:
				# group label widget
				label = PySide6.QtWidgets.QLabel(label_text)
				label.setStyleSheet(
					"font-size: 9px; color: gray; padding: 0 2px;"
				)
				self._layout.insertWidget(
					self._layout.count() - 1, label
				)
				self._extra_widgets.append(label)
			elif group_idx > 0:
				# vertical separator line between groups
				sep = PySide6.QtWidgets.QFrame()
				sep.setFrameShape(
					PySide6.QtWidgets.QFrame.Shape.VLine
				)
				sep.setFrameShadow(
					PySide6.QtWidgets.QFrame.Shadow.Sunken
				)
				self._layout.insertWidget(
					self._layout.count() - 1, sep
				)
				self._extra_widgets.append(sep)

			# determine layout for this submode group
			layout_type = 'row'
			if group_idx < len(mode.group_layouts):
				layout_type = mode.group_layouts[group_idx]

			if layout_type == 'grid':
				group_widget = self._build_grid_group(
					mode, group_idx
				)
			else:
				group_widget = self._build_row_group(
					mode, group_idx
				)
			self._layout.insertWidget(
				self._layout.count() - 1, group_widget
			)
			self._group_widgets.append(group_widget)
		self._last_grid_reflow_width = self.width()

	#============================================
	def _build_row_group(self, mode: object, group_index: int) -> PySide6.QtWidgets.QWidget:
		"""Build a horizontal row of submode buttons for a group.

		Args:
			mode: The active mode object.
			group_index: Index of the submode group.

		Returns:
			QWidget containing the row of buttons.
		"""
		container = PySide6.QtWidgets.QWidget()
		row_layout = PySide6.QtWidgets.QHBoxLayout(container)
		row_layout.setContentsMargins(0, 0, 0, 0)
		row_layout.setSpacing(1)
		# store button references for selection tracking
		container._buttons = {}
		container._selected_btn = None

		keys = mode.submodes[group_index]
		names = mode.submodes_names[group_index]

		for idx, key in enumerate(keys):
			display_name = names[idx] if idx < len(names) else key
			# tooltip: prefer tooltip_map, fall back to display name
			tip_text = mode.tooltip_map.get(key, display_name)

			btn = PySide6.QtWidgets.QPushButton()
			btn.setCheckable(True)

			# try to load an icon for this submode
			icon_name = mode.icon_map.get(key)
			has_icon = False
			if icon_name:
				icon = bkchem_qt.widgets.icon_loader.get_icon(
					icon_name
				)
				if not icon.isNull():
					btn.setIcon(icon)
					has_icon = True

			# show text if no icon or if size is 'large'
			size_hint = mode.size_map.get(key, '')
			if not has_icon or size_hint == 'large':
				btn.setText(display_name)

			btn.setToolTip(tip_text)
			btn.setMinimumHeight(24)

			# click handler with closure capture
			btn.clicked.connect(
				lambda checked, k=key, b=btn, c=container:
					self._on_row_button_clicked(k, b, c)
			)
			row_layout.addWidget(btn)
			container._buttons[key] = btn

		# auto-select the default submode
		default_idx = mode.submode[group_index]
		if default_idx < len(keys):
			default_key = keys[default_idx]
			default_btn = container._buttons.get(default_key)
			if default_btn is not None:
				default_btn.setChecked(True)
				container._selected_btn = default_btn

		return container

	#============================================
	def _build_grid_group(self, mode: object, group_index: int) -> PySide6.QtWidgets.QWidget:
		"""Build a grid of submode buttons for a group.

		Used for template grids with short labels arranged in columns.

		Args:
			mode: The active mode object.
			group_index: Index of the submode group.

		Returns:
			QWidget containing the button grid.
		"""
		keys = mode.submodes[group_index]
		# look up base columns from YAML and adapt to current width
		base_columns = self._get_grid_columns(mode, group_index)
		columns = self._get_adaptive_grid_columns(
			mode, group_index, keys, base_columns
		)

		container = PySide6.QtWidgets.QWidget()
		grid_layout = PySide6.QtWidgets.QGridLayout(container)
		grid_layout.setContentsMargins(0, 0, 0, 0)
		grid_layout.setSpacing(1)
		container._buttons = {}
		container._selected_btn = None
		container._effective_columns = columns
		container._base_columns = base_columns

		names = mode.submodes_names[group_index]

		for idx, key in enumerate(keys):
			row = idx // columns
			col = idx % columns
			display_name = names[idx] if idx < len(names) else key
			tip_text = mode.tooltip_map.get(key, display_name)

			btn = PySide6.QtWidgets.QPushButton(display_name)
			btn.setCheckable(True)
			btn.setToolTip(tip_text)
			btn.setMinimumHeight(22)

			btn.clicked.connect(
				lambda checked, k=key, b=btn, c=container:
					self._on_row_button_clicked(k, b, c)
			)
			grid_layout.addWidget(btn, row, col)
			container._buttons[key] = btn

		# auto-select the default
		default_idx = mode.submode[group_index]
		if default_idx < len(keys):
			default_key = keys[default_idx]
			default_btn = container._buttons.get(default_key)
			if default_btn is not None:
				default_btn.setChecked(True)
				container._selected_btn = default_btn

		return container

	#============================================
	def _on_row_button_clicked(self, key: str,
			btn: PySide6.QtWidgets.QPushButton,
			container: PySide6.QtWidgets.QWidget) -> None:
		"""Handle a submode button click.

		Deselects the previously selected button, selects the new one,
		and emits submode_selected.

		Args:
			key: The submode key string.
			btn: The clicked QPushButton.
			container: The group container holding button references.
		"""
		# deselect previous
		prev = container._selected_btn
		if prev is not None and prev is not btn:
			prev.setChecked(False)
		# select new
		btn.setChecked(True)
		container._selected_btn = btn
		self.submode_selected.emit(key)

	#============================================
	def refresh_group(self, group_index: int) -> None:
		"""Rebuild a single submode group widget in place.

		Used when a dynamic mode changes its submodes at runtime
		(e.g. biomolecule category switch refreshes the template grid).

		Args:
			group_index: Index of the submode group to rebuild.
		"""
		if self._current_mode is None:
			return
		if group_index >= len(self._group_widgets):
			return
		mode = self._current_mode

		# determine the layout type for insertion position tracking
		old_widget = self._group_widgets[group_index]
		# find the position in the layout
		layout_idx = self._layout.indexOf(old_widget)

		# remove old widget
		self._layout.removeWidget(old_widget)
		old_widget.deleteLater()

		# determine layout
		layout_type = 'row'
		if group_index < len(mode.group_layouts):
			layout_type = mode.group_layouts[group_index]

		# build replacement
		if layout_type == 'grid':
			new_widget = self._build_grid_group(mode, group_index)
		else:
			new_widget = self._build_row_group(mode, group_index)

		# insert at same position
		self._layout.insertWidget(layout_idx, new_widget)
		self._group_widgets[group_index] = new_widget
		self._last_grid_reflow_width = self.width()

	#============================================
	def _clear_all(self) -> None:
		"""Remove all group widgets and extra widgets from the layout."""
		for widget in self._group_widgets:
			self._layout.removeWidget(widget)
			widget.deleteLater()
		self._group_widgets.clear()
		for widget in self._extra_widgets:
			self._layout.removeWidget(widget)
			widget.deleteLater()
		self._extra_widgets.clear()

	#============================================
	def _get_grid_columns(self, mode: object, group_index: int) -> int:
		"""Look up the grid column count from YAML config.

		Args:
			mode: The active mode object.
			group_index: Index of the submode group.

		Returns:
			Number of columns for the grid layout (default 4).
		"""
		columns = 4
		if not _MODES_YAML_PATH.is_file():
			return columns
		with open(_MODES_YAML_PATH, "r") as fh:
			modes_config = yaml.safe_load(fh) or {}
		modes_defs = modes_config.get("modes", {})

		candidate_keys = []
		if self._current_mode_name:
			candidate_keys.append(self._current_mode_name)
		if mode.name:
			candidate_keys.append(str(mode.name).lower())

		for yaml_key in candidate_keys:
			mode_def = modes_defs.get(yaml_key)
			if not mode_def:
				continue
			submode_groups = mode_def.get("submodes", [])
			if group_index < len(submode_groups):
				columns = submode_groups[group_index].get("columns", 4)
			return max(1, int(columns))
		return columns

	#============================================
	def _get_adaptive_grid_columns(
		self,
		mode: object,
		group_index: int,
		keys: list,
		base_columns: int,
	) -> int:
		"""Return a grid-column count adapted to current ribbon width."""
		if not keys:
			return 1
		base = max(1, min(int(base_columns), len(keys)))
		fit_columns = self._resolve_fit_columns(mode, group_index, keys)
		return max(base, min(fit_columns, len(keys)))

	#============================================
	def _resolve_fit_columns(self, mode: object, group_index: int, keys: list) -> int:
		"""Estimate the number of columns that fit in available width."""
		button_width = self._estimate_grid_button_width(mode, group_index, keys)
		if button_width <= 0:
			return 1
		available = self._resolve_grid_available_width(mode, group_index)
		return max(1, int((available + 1) // (button_width + 1)))

	#============================================
	def _estimate_grid_button_width(self, mode: object, group_index: int, keys: list) -> int:
		"""Estimate width of the widest button in the grid group."""
		names = mode.submodes_names[group_index]
		font_metrics = self.fontMetrics()
		max_text_width = 0
		for idx, key in enumerate(keys):
			label = names[idx] if idx < len(names) else key
			max_text_width = max(
				max_text_width,
				font_metrics.horizontalAdvance(str(label)),
			)
		return max(48, max_text_width + _GRID_BUTTON_PADDING)

	#============================================
	def _resolve_grid_available_width(self, mode: object, group_index: int) -> int:
		"""Estimate width available to the target grid group."""
		available = self.width() - 12
		if available <= 0:
			parent = self.parentWidget()
			if parent is not None:
				available = parent.width() - 12
		if available <= 0:
			available = self.window().width() - 40
		if available <= _GRID_FALLBACK_MIN_WIDTH:
			return _GRID_FALLBACK_MIN_WIDTH

		for idx in range(len(mode.submodes)):
			if idx == group_index:
				continue
			layout_type = 'row'
			if idx < len(mode.group_layouts):
				layout_type = mode.group_layouts[idx]
			available -= 220 if layout_type == 'row' else 120
		return max(_GRID_FALLBACK_MIN_WIDTH, available)

	#============================================
	def resizeEvent(self, event: object) -> None:
		"""Rebuild grid groups when ribbon width changes significantly."""
		super().resizeEvent(event)
		if self._current_mode is None:
			return
		if self._in_resize_reflow:
			return
		if "grid" not in self._current_mode.group_layouts:
			return
		new_width = event.size().width()
		if abs(new_width - self._last_grid_reflow_width) < _GRID_RESIZE_REBUILD_THRESHOLD:
			return
		self._in_resize_reflow = True
		try:
			self._rebuild_from_mode(self._current_mode)
		finally:
			self._in_resize_reflow = False
