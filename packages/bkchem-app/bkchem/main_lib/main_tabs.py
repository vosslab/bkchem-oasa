"""Tab management mixin methods for BKChem main application."""

import os

import tkinter.messagebox
import tkinter.ttk as ttk

from bkchem import bkchem_utils
from bkchem import theme_manager
from bkchem.paper import chem_paper
from bkchem.singleton_store import Store

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


class MainTabsMixin:
  """Tab management helpers extracted from main.py."""

  def _on_tab_changed(self, event=None):
    """Handle <<NotebookTabChanged>> events from ttk.Notebook.

    Maps the currently selected tab frame back to a paper and
    calls change_paper().  Uses a guard flag to prevent re-entrant
    calls when change_paper() itself selects a tab programmatically.
    """
    if getattr(self, '_programmatic_tab_select', False):
      return
    sel = self.notebook.select()
    if not sel:
      return
    # find which paper lives on this frame
    for tab_name, frame in self._tab_name_2_frame.items():
      if str(frame) == str(sel):
        self.change_paper(tab_name)
        return


  def change_paper(self, name):
    if self.papers:
      old_paper = self.paper
      # look up paper index from tab name
      if name in self._tab_name_2_paper:
        paper = self._tab_name_2_paper[name]
        i = self.papers.index(paper)
      else:
        return
      # the rest
      self.paper = self.papers[i]
      if (hasattr(self, 'mode') and
          not bkchem_utils.myisstr(self.mode) and
          old_paper in self.papers and
          self.paper != old_paper):
        # this is not true on startup and tab closing
        self.mode.on_paper_switch( old_paper, self.paper)


  def add_new_paper( self, name=''):
    # check if the same file is opened
    p = self.check_if_the_file_is_opened( name)
    if p:
      Store.log( _("Sorry but I cannot open the same file twice: ")+"\n"+name, message_type="error")
      return False
    name_dic = self.get_name_dic( name=name)
    # create the tab: ttk.Notebook requires us to create the Frame first
    _tab_name = self.get_new_tab_name()
    page = ttk.Frame(self.notebook)
    tab_text = chem_paper.create_window_name(name_dic)
    self.notebook.add(page, text=tab_text)
    self._tab_name_2_frame[_tab_name] = page
    paper = chem_paper( page,
                        scrollregion=(-100,-100,'300m','400m'),
                        background=theme_manager.get_color('canvas_surround'),
                        closeenough=3,
                        file_name=name_dic)
    self._tab_name_2_paper[ _tab_name] = paper
    # the scrolling -- use ttk.Scrollbar for theme integration
    scroll_y = ttk.Scrollbar( page, orient='vertical', command=paper.yview)
    scroll_x = ttk.Scrollbar( page, orient='horizontal', command=paper.xview)
    paper.grid( row=0, column=0, sticky="news")
    page.grid_rowconfigure( 0, weight=1, minsize = 0)
    page.grid_columnconfigure( 0, weight=1, minsize = 0)
    scroll_x.grid( row=1, column=0, sticky='we')
    scroll_y.grid( row=0, column=1, sticky='ns')
    paper['yscrollcommand'] = scroll_y.set
    paper['xscrollcommand'] = scroll_x.set

    # Zoom controls at bottom of each tab page -- use ttk widgets
    zoom_frame = ttk.Frame(page)
    zoom_frame.grid(row=2, column=0, columnspan=2, sticky='e')

    zoom_out_btn = ttk.Button(zoom_frame, text="-", width=2, style='Zoom.TButton', command=paper.zoom_out)
    zoom_out_btn.pack(side='left', padx=1)

    zoom_label = ttk.Label(zoom_frame, text="100%", width=5, style='Zoom.TLabel')
    zoom_label.pack(side='left', padx=1)

    zoom_in_btn = ttk.Button(zoom_frame, text="+", width=2, style='Zoom.TButton', command=paper.zoom_in)
    zoom_in_btn.pack(side='left', padx=1)

    zoom_reset_btn = ttk.Button(zoom_frame, text="100%", width=4, style='Zoom.TButton', command=paper.zoom_reset)
    zoom_reset_btn.pack(side='left', padx=2)

    zoom_fit_btn = ttk.Button(zoom_frame, text="Fit", width=3, style='Zoom.TButton', command=paper.zoom_to_fit)
    zoom_fit_btn.pack(side='left', padx=2)

    zoom_content_btn = ttk.Button(zoom_frame, text="Content", width=6, style='Zoom.TButton', command=paper.zoom_to_content)
    zoom_content_btn.pack(side='left', padx=2)

    def update_zoom_label(event=None, lbl=zoom_label, p=paper):
      zoom_text = "%d%%" % int(p._scale * 100)
      lbl.config(text=zoom_text)
      # also update the status bar zoom indicator
      self.zoom_var.set(zoom_text)
    paper.bind('<<zoom-changed>>', update_zoom_label)

    self.papers.append( paper)
    self.change_paper( _tab_name)
    # select the newly added tab
    self._programmatic_tab_select = True
    self.notebook.select(page)
    self._programmatic_tab_select = False
    paper.bind( "<<selection-changed>>", self.update_menu_after_selection_change)
    paper.bind( "<<clipboard-changed>>", self.update_menu_after_selection_change)
    paper.bind( "<<undo>>", self.update_menu_after_selection_change)
    paper.bind( "<<redo>>", self.update_menu_after_selection_change)
    if not self.paper:
      self.paper = paper  # this is needed for the batch mode, normaly its done in change_paper
    else:
      self.paper.focus_set()
    return True


  def close_current_paper( self, call_quit_if_no_remains=True):
    ret = self.close_paper()
    if self.papers == [] and call_quit_if_no_remains:
      self._quit()
    return ret


  def close_paper( self, paper=None):
    p = paper or self.paper
    if hasattr( self, "editPool") and self.editPool.active:
      self.editPool._cancel(None)

    if p.changes_made and not self.in_batch_mode:
      name = p.file_name['name']
      # 3-button dialog: Close / Save / Cancel
      result = tkinter.messagebox._show(
        _("Really close?"),
        _("There are unsaved changes in file %s. Save before closing?") % name,
        icon=tkinter.messagebox.QUESTION,
        type=tkinter.messagebox.YESNOCANCEL,
        master=self,
      )
      # Yes = Save, No = Close without saving, Cancel = abort
      if result == 'yes':
        self.save_CDML()
      elif result == 'cancel':
        return 0 # we skip away
    self.papers.remove( p)

    # cleanup
    tab_name = self.get_paper_tab_name( p)
    frame = self._tab_name_2_frame.get(tab_name)
    del self._tab_name_2_paper[ tab_name]
    if tab_name in self._tab_name_2_frame:
      del self._tab_name_2_frame[ tab_name]
    p.mrproper()
    if frame:
      self.notebook.forget(frame)
    return 1


  def check_if_the_file_is_opened( self, name, check_current=1):
    """check_current says if the self.paper should be also included into the check,
    this is usefull to make it 0 for renames"""
    for p in self.papers:
      if not check_current and p == self.paper:
        continue
      if p.full_path == os.path.abspath( name):
        return p
    return None


  def check_number_of_opened_same_names( self, name):
    """checks if there are papers with same name and returns the highest value"""
    ps = [p.file_name['ord'] for p in self.papers if p.file_name['name'] == name['name']]
    if not ps:
      return 0
    else:
      return max( ps)+1


  def get_new_tab_name( self):
    self._last_tab += 1
    return "tab"+str(self._last_tab)


  def get_paper_tab_name( self, paper):
    for k in self._tab_name_2_paper:
      if self._tab_name_2_paper[ k] == paper:
        return k
    return None
