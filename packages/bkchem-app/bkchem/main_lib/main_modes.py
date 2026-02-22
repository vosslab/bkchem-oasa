"""Mode switching mixin methods for BKChem main application."""

# Standard Library
import tkinter.ttk as ttk
from tkinter import Frame, Label, LEFT

from bkchem import bkchem_utils
from bkchem import theme_manager
from bkchem.modes.config import get_modes_config
from bkchem import pixmaps

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


class MainModesMixin:
	"""Mode and submode switching helpers extracted from main.py."""

	def change_mode( self, tag):
		old_mode = self.mode
		self.mode = self.modes[ tag]
		if not bkchem_utils.myisstr(old_mode):
			old_mode.cleanup()
			self.mode.copy_settings( old_mode)

		# tear down previous submode widgets (buttons, labels, separators)
		# destroy edit pool buttons before destroying the ribbon frame they live in
		self.editPool.destroy_buttons()
		if self.subbuttons:
			for butts in self.subbuttons:
				butts.destroy()
		self.subbuttons = []
		for widget in getattr(self, '_sub_extra_widgets', []):
			widget.destroy()
		self._sub_extra_widgets = []

		m = self.mode
		# YAML-driven ribbon fields
		mode_icon_map = getattr(m, 'icon_map', {})
		group_labels = getattr(m, 'group_labels', [])
		tooltip_map = getattr(m, 'tooltip_map', {})

		for i in range( len( m.submodes)):
			# render group separator or label before button row
			label_text = group_labels[i] if i < len(group_labels) else ''
			if label_text:
				# group label replaces separator line (they are redundant together)
				lbl = Label(self.subFrame, text=label_text, font=('sans-serif', 8),
										fg=theme_manager.get_color('group_label_fg'), anchor='w', padx=1, pady=0)
				lbl.pack(side=LEFT, padx=(2, 0))
				self._sub_extra_widgets.append(lbl)
			elif i > 0:
				# no label: show a vertical separator line between groups
				sep = Frame(self.subFrame, width=1, bg=theme_manager.get_color('group_separator'))
				sep.pack(side=LEFT, fill='y', padx=2, pady=1)
				self._sub_extra_widgets.append(sep)

			# determine layout for this submode group
			layout = 'row'
			if hasattr(m, 'group_layouts') and i < len(m.group_layouts):
				layout = m.group_layouts[i]

			if layout == 'grid':
				# button grid layout (e.g. biomolecule templates with short labels)
				grid_frame = self._build_submode_grid(m, i, tooltip_map)
				self.subbuttons.append(grid_frame)
				grid_frame.pack(side=LEFT, padx=(0, 2))
			elif layout == 'row':
				# normal horizontal button row using ttk.Button
				row_frame = self._build_submode_row(m, i, mode_icon_map, tooltip_map)
				self.subbuttons.append(row_frame)
				row_frame.pack(side=LEFT, padx=(0, 2))
			else:
				# fallback: dropdown menu using ttk.Combobox
				import tkinter
				combo_var = tkinter.StringVar()
				combo = ttk.Combobox(self.subFrame, textvariable=combo_var,
					values=m.submodes_names[i], state='readonly', width=16)
				combo.bind('<<ComboboxSelected>>', lambda e, cv=combo_var: self.change_submode(cv.get()))
				if m.submodes_names[i]:
					combo.current(0)
				self.subbuttons.append(combo)
				combo.pack(side=LEFT, padx=(0, 2))

		# add edit pool buttons to ribbon for text-entry modes (YAML show_edit_pool)
		if getattr(m, 'show_edit_pool', False):
			# vertical separator before the button group if submodes already exist
			if self.subbuttons:
				sep = Frame(self.subFrame, width=1, bg=theme_manager.get_color('group_separator'))
				sep.pack(side=LEFT, fill='y', padx=2, pady=1)
				self._sub_extra_widgets.append(sep)
			bf = self.editPool.create_buttons(self.subFrame)
			bf.pack(side=LEFT)
			self._sub_extra_widgets.append(bf)
			# show the Entry bar
			self.editPool.grid(row=5, sticky="wens")
		else:
			# hide the Entry bar for non-editing modes
			self.editPool.grid_remove()

		# set the active mode on the StringVar -- ttk Radiobutton selection
		# styling follows automatically from the StringVar and state maps
		if hasattr(self, '_mode_var'):
			self._mode_var.set(tag)

		self.paper.mode = self.mode
		# update status bar mode name
		self.mode_name_var.set(self.modes[tag].name)
		self.mode.startup()


	def change_submode( self, tag):
		self.mode.set_submode( tag)


	def _build_submode_row(self, m, group_index, mode_icon_map, tooltip_map):
		"""Build a ttk.Button row for a submode group.

		Args:
			m: The current mode object.
			group_index: Index of the submode group.
			mode_icon_map: Dict mapping submode keys to icon names.
			tooltip_map: Dict mapping submode keys to tooltip text.

		Returns:
			Frame: A Tk Frame containing ttk.Button widgets.
		"""
		row_frame = Frame(self.subFrame, borderwidth=0)
		row_frame._row_buttons = {}
		row_frame._row_selected = None

		def on_row_click(name, btn, frame=row_frame):
			"""Handle row button click -- highlight and set submode."""
			# deselect previous
			if frame._row_selected and frame._row_selected.winfo_exists():
				frame._row_selected.configure(style='Submode.TButton')
			# select new
			btn.configure(style='Selected.Submode.TButton')
			frame._row_selected = btn
			self.change_submode(name)

		for sub in m.submodes[group_index]:
			# use icon_map for YAML default cascade (key->icon override)
			icon_name = mode_icon_map.get(sub, sub)
			img_name = m.__class__.__name__.replace("_mode", "") + "-" + icon_name
			if img_name in pixmaps.images:
				img = pixmaps.images[img_name]
			elif icon_name in pixmaps.images:
				img = pixmaps.images[icon_name]
			else:
				img = None
			# tooltip: prefer YAML tooltip_map, fall back to display name
			sub_idx = m.submodes[group_index].index(sub)
			display_name = m.submodes_names[group_index][sub_idx]
			tip_text = tooltip_map.get(sub, display_name)
			btn_kwargs = {'style': 'Submode.TButton'}
			if img:
				btn_kwargs['image'] = img
			else:
				btn_kwargs['text'] = display_name
			btn = ttk.Button(row_frame,
				command=lambda n=sub: on_row_click(n, row_frame._row_buttons[n]),
				**btn_kwargs)
			btn.pack(side=LEFT, padx=1)
			row_frame._row_buttons[sub] = btn
			self.balloon.bind(btn, tip_text)

		# select the default submode
		default_key = m.submodes[group_index][m.submode[group_index]]
		if default_key in row_frame._row_buttons:
			on_row_click(default_key, row_frame._row_buttons[default_key])

		return row_frame


	def _build_submode_grid(self, m, group_index, tooltip_map):
		"""Build a ttk Frame with buttons arranged in a grid layout.

		Args:
			m: The current mode object.
			group_index: Index of the submode group.
			tooltip_map: Dict mapping submode keys to tooltip text.

		Returns:
			Frame: A ttk Frame containing the grid of buttons.
		"""
		# get column count from YAML config
		yaml_key = type(m).__name__.replace('_mode', '')
		cfg = get_modes_config()['modes'].get(yaml_key, {})
		columns = 4
		submode_groups = cfg.get('submodes', [])
		if group_index < len(submode_groups):
			columns = submode_groups[group_index].get('columns', 4)

		grid_frame = ttk.Frame(self.subFrame)
		# track the selected button for this grid
		grid_frame._grid_buttons = {}
		grid_frame._grid_selected = None

		def on_grid_click(name, btn):
			"""Handle grid button click -- highlight and set submode."""
			# un-highlight previous selection
			if grid_frame._grid_selected and grid_frame._grid_selected.winfo_exists():
				grid_frame._grid_selected.configure(style='Grid.TButton')
			# highlight new selection
			btn.configure(style='Selected.Grid.TButton')
			grid_frame._grid_selected = btn
			self.change_submode(name)

		submodes_list = m.submodes[group_index]
		names_list = m.submodes_names[group_index]
		for idx, sub in enumerate(submodes_list):
			row = idx // columns
			col = idx % columns
			display_name = names_list[idx] if idx < len(names_list) else sub
			tip_text = tooltip_map.get(sub, display_name)
			btn = ttk.Button(
				grid_frame, text=display_name,
				width=4, style='Grid.TButton',
				command=lambda n=sub, b_idx=idx: on_grid_click(n, grid_frame._grid_buttons[b_idx]),
			)
			btn.grid(row=row, column=col, padx=1, pady=1)
			grid_frame._grid_buttons[idx] = btn
			self.balloon.bind(btn, tip_text)

		# auto-select first button
		if submodes_list and 0 in grid_frame._grid_buttons:
			first_btn = grid_frame._grid_buttons[0]
			first_btn.configure(style='Selected.Grid.TButton')
			grid_frame._grid_selected = first_btn
			self.change_submode(submodes_list[0])

		return grid_frame


	def refresh_submode_buttons(self, group_index):
		"""Rebuild the submode widget at the given group index.

		Used when the template list changes (e.g. category switch
		in biomolecule mode).

		Args:
			group_index: Index of the submode group to rebuild.
		"""
		if group_index >= len(self.subbuttons):
			return
		m = self.mode
		tooltip_map = getattr(m, 'tooltip_map', {})
		mode_icon_map = getattr(m, 'icon_map', {})
		# destroy existing widget
		old_widget = self.subbuttons[group_index]
		old_widget.destroy()
		# determine layout
		layout = 'row'
		if hasattr(m, 'group_layouts') and group_index < len(m.group_layouts):
			layout = m.group_layouts[group_index]
		if layout == 'grid':
			new_widget = self._build_submode_grid(m, group_index, tooltip_map)
		else:
			# rebuild as ttk button row
			new_widget = self._build_submode_row(m, group_index, mode_icon_map, tooltip_map)
		new_widget.pack(side=LEFT, padx=(0, 2))
		self.subbuttons[group_index] = new_widget
