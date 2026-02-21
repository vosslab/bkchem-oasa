"""Mode switching mixin methods for BKChem main application."""

from tkinter import Button, Frame, Label, LEFT

import Pmw
from bkchem import bkchem_config
from bkchem import bkchem_utils
from bkchem.modes.config import get_modes_config
from bkchem import pixmaps

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)

# hover color for submode ribbon buttons
_SUB_HOVER_BG = bkchem_config.hover_color
# grid button selected color
_GRID_SELECTED_BG = '#b0c4de'


#============================================
def _on_sub_enter(btn, default_bg):
	"""Highlight a submode button on mouse hover."""
	# skip hover tint when the button is the active selection
	current_bg = str(btn.cget('background'))
	if current_bg == _GRID_SELECTED_BG:
		return
	btn.configure(background=_SUB_HOVER_BG)


#============================================
def _on_sub_leave(btn, default_bg):
	"""Restore a submode button background when mouse leaves."""
	current_bg = str(btn.cget('background'))
	if current_bg == _GRID_SELECTED_BG:
		return
	btn.configure(background=default_bg)


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
        if hasattr( butts, 'deleteall()'):
          butts.deleteall()
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
                    fg='#666666', anchor='w', padx=1, pady=0)
        lbl.pack(side=LEFT, padx=(2, 0))
        self._sub_extra_widgets.append(lbl)
      elif i > 0:
        # no label: show a vertical separator line between groups
        sep = Frame(self.subFrame, width=1, bg='#b0b0b0')
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
        # normal horizontal button row
        self.subbuttons.append( Pmw.RadioSelect( self.subFrame,
                                                 buttontype = 'button',
                                                 selectmode = 'single',
                                                 orient = 'horizontal',
                                                 command = self.change_submode,
                                                 hull_borderwidth = 0,
                                                 padx = 0,
                                                 pady = 0,
                                                 hull_relief = 'ridge',
                                                 ))
        self.subbuttons[i].pack(side=LEFT, padx=(0, 2))
        for sub in m.submodes[i]:
          # use icon_map for YAML default cascade (key->icon override)
          icon_name = mode_icon_map.get(sub, sub)
          img_name = m.__class__.__name__.replace("_mode","") + "-" + icon_name
          if img_name in pixmaps.images:
            img = pixmaps.images[img_name]
          elif icon_name in pixmaps.images:
            img = pixmaps.images[icon_name]
          else:
            img = None
          # tooltip: prefer YAML tooltip_map, fall back to display name
          sub_idx = m.submodes[i].index(sub)
          display_name = m.submodes_names[i][sub_idx]
          tip_text = tooltip_map.get(sub, display_name)
          if img:
            recent = self.subbuttons[i].add( sub, image=img, activebackground='grey', borderwidth=bkchem_config.border_width)
            self.balloon.bind(recent, tip_text)
          else:
            recent = self.subbuttons[i].add( sub, text=display_name, borderwidth=bkchem_config.border_width)
          # hover effect on submode buttons
          sub_bg = str(recent.cget('background'))
          recent.bind('<Enter>', lambda e, b=recent, bg=sub_bg: _on_sub_enter(b, bg))
          recent.bind('<Leave>', lambda e, b=recent, bg=sub_bg: _on_sub_leave(b, bg))
        # select the default submode
        j = m.submodes[i][ m.submode[i]]
        self.subbuttons[i].invoke( j)
      else:
        # fallback: dropdown menu
        self.subbuttons.append( Pmw.OptionMenu( self.subFrame,
                                                items = m.submodes_names[i],
                                                command = self.change_submode))
        self.subbuttons[i].pack(side=LEFT, padx=(0, 2))

    # add edit pool buttons to ribbon for text-entry modes (YAML show_edit_pool)
    if getattr(m, 'show_edit_pool', False):
      # vertical separator before the button group if submodes already exist
      if self.subbuttons:
        sep = Frame(self.subFrame, width=1, bg='#b0b0b0')
        sep.pack(side=LEFT, fill='y', padx=2, pady=1)
        self._sub_extra_widgets.append(sep)
      bf = self.editPool.create_buttons(self.subFrame)
      bf.pack(side=LEFT)
      self._sub_extra_widgets.append(bf)
      # show the Entry bar
      self.editPool.grid(row=4, sticky="wens")
    else:
      # hide the Entry bar for non-editing modes
      self.editPool.grid_remove()

    # highlight the active mode button with a colored fill and subtle border
    # capture default colors once so we can fully reset inactive buttons
    if not hasattr(self, '_btn_default_hlbg'):
      first_btn = self.get_mode_button(self.modes_sort[0])
      self._btn_default_hlbg = str(first_btn.cget('highlightbackground'))
      # toolbar buttons use the toolbar band bg
      self._btn_default_bg = bkchem_config.toolbar_color
    for btn_name in self.modes_sort:
      btn = self.get_mode_button(btn_name)
      if not btn:
        continue
      if btn_name == tag:
        # active: light blue fill + subtle blue border
        btn.configure(relief='groove', borderwidth=2,
          background=bkchem_config.active_mode_color,
          highlightbackground='#4a90d9',
          highlightcolor='#4a90d9',
          highlightthickness=1)
      else:
        # inactive: flat, default background
        btn.configure(relief='flat', borderwidth=1,
          background=self._btn_default_bg,
          highlightbackground=self._btn_default_hlbg,
          highlightcolor=self._btn_default_hlbg,
          highlightthickness=0)

    self.paper.mode = self.mode
    # update status bar mode name
    self.mode_name_var.set(self.modes[tag].name)
    self.mode.startup()


  def change_submode( self, tag):
    self.mode.set_submode( tag)


  def _build_submode_grid(self, m, group_index, tooltip_map):
    """Build a Tk Frame with buttons arranged in a grid layout.

    Args:
      m: The current mode object.
      group_index: Index of the submode group.
      tooltip_map: Dict mapping submode keys to tooltip text.

    Returns:
      Frame: A Tk Frame containing the grid of buttons.
    """
    # get column count from YAML config
    yaml_key = type(m).__name__.replace('_mode', '')
    cfg = get_modes_config()['modes'].get(yaml_key, {})
    columns = 4
    submode_groups = cfg.get('submodes', [])
    if group_index < len(submode_groups):
      columns = submode_groups[group_index].get('columns', 4)

    grid_frame = Frame(self.subFrame, relief='ridge', borderwidth=0)
    # track the selected button for this grid
    grid_frame._grid_buttons = {}
    grid_frame._grid_selected = None

    def on_grid_click(name, btn):
      """Handle grid button click -- highlight and set submode."""
      # un-highlight previous selection
      if grid_frame._grid_selected and grid_frame._grid_selected.winfo_exists():
        grid_frame._grid_selected.configure(relief='raised', bg='#d9d9d9')
      # highlight new selection
      btn.configure(relief='sunken', bg='#b0c4de')
      grid_frame._grid_selected = btn
      self.change_submode(name)

    submodes_list = m.submodes[group_index]
    names_list = m.submodes_names[group_index]
    for idx, sub in enumerate(submodes_list):
      row = idx // columns
      col = idx % columns
      display_name = names_list[idx] if idx < len(names_list) else sub
      tip_text = tooltip_map.get(sub, display_name)
      btn = Button(
        grid_frame, text=display_name,
        width=4, padx=1, pady=1,
        relief='raised', borderwidth=bkchem_config.border_width,
        font=('sans-serif', 9),
        command=lambda n=sub, b_idx=idx: on_grid_click(n, grid_frame._grid_buttons[b_idx]),
      )
      btn.grid(row=row, column=col, padx=1, pady=1)
      grid_frame._grid_buttons[idx] = btn
      self.balloon.bind(btn, tip_text)
      # hover effect on grid submode buttons
      grid_bg = str(btn.cget('background'))
      btn.bind('<Enter>', lambda e, b=btn, bg=grid_bg: _on_sub_enter(b, bg))
      btn.bind('<Leave>', lambda e, b=btn, bg=grid_bg: _on_sub_leave(b, bg))

    # auto-select first button
    if submodes_list and 0 in grid_frame._grid_buttons:
      first_btn = grid_frame._grid_buttons[0]
      first_btn.configure(relief='sunken', bg='#b0c4de')
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
      # rebuild as horizontal row
      new_widget = Pmw.RadioSelect(self.subFrame,
        buttontype='button', selectmode='single',
        orient='horizontal', command=self.change_submode,
        hull_borderwidth=0, padx=0, pady=0, hull_relief='ridge')
      for sub in m.submodes[group_index]:
        sub_idx = m.submodes[group_index].index(sub)
        display_name = m.submodes_names[group_index][sub_idx]
        new_widget.add(sub, text=display_name, borderwidth=bkchem_config.border_width)
      if m.submodes[group_index]:
        new_widget.invoke(m.submodes[group_index][0])
    new_widget.pack(side=LEFT, padx=(0, 2))
    self.subbuttons[group_index] = new_widget
