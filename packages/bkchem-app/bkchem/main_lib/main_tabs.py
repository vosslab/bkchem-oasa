"""Tab management mixin methods for BKChem main application."""

import os

from tkinter import Button, Frame, Label, Scrollbar
from tkinter import HORIZONTAL, SUNKEN, VERTICAL

import Pmw
from bkchem import bkchem_config
from bkchem import bkchem_utils
from bkchem.paper import chem_paper
from bkchem.singleton_store import Store

import builtins
_ = builtins.__dict__.get( '_', lambda m: m)


class MainTabsMixin:
  """Tab management helpers extracted from main.py."""

  def change_paper(self, name):
    if self.papers:
      old_paper = self.paper
      # de-highlighting of current tab
      if old_paper in self.papers:
        i = self.papers.index(old_paper)
        self.notebook.tab(i).configure(background=bkchem_config.background_color, fg="black")
      i = self.notebook.index( name)
      # highlighting of current tab
      self.notebook.tab( i).configure( background="#777777", fg="white")
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
    # create the tab
    _tab_name = self.get_new_tab_name()
    page = self.notebook.add( _tab_name, tab_text = chem_paper.create_window_name( name_dic))
    paper = chem_paper( page,
                        scrollregion=(-100,-100,'300m','400m'),
                        background="grey",
                        closeenough=3,
                        file_name=name_dic)
    self._tab_name_2_paper[ _tab_name] = paper
    # the scrolling
    scroll_y = Scrollbar( page, orient = VERTICAL, command = paper.yview, bd=bkchem_config.border_width)
    scroll_x = Scrollbar( page, orient = HORIZONTAL, command = paper.xview, bd=bkchem_config.border_width)
    paper.grid( row=0, column=0, sticky="news")
    page.grid_rowconfigure( 0, weight=1, minsize = 0)
    page.grid_columnconfigure( 0, weight=1, minsize = 0)
    scroll_x.grid( row=1, column=0, sticky='we')
    scroll_y.grid( row=0, column=1, sticky='ns')
    paper['yscrollcommand'] = scroll_y.set
    paper['xscrollcommand'] = scroll_x.set

    # Zoom controls at bottom of each tab page
    zoom_frame = Frame(page)
    zoom_frame.grid(row=2, column=0, columnspan=2, sticky='e')

    zoom_out_btn = Button(zoom_frame, text="\u2212", width=2, command=paper.zoom_out)
    zoom_out_btn.pack(side='left', padx=1)

    zoom_label = Label(zoom_frame, text="100%", width=5, relief=SUNKEN)
    zoom_label.pack(side='left', padx=1)

    zoom_in_btn = Button(zoom_frame, text="+", width=2, command=paper.zoom_in)
    zoom_in_btn.pack(side='left', padx=1)

    zoom_reset_btn = Button(zoom_frame, text="100%", width=4, command=paper.zoom_reset)
    zoom_reset_btn.pack(side='left', padx=2)

    zoom_fit_btn = Button(zoom_frame, text="Fit", width=3, command=paper.zoom_to_fit)
    zoom_fit_btn.pack(side='left', padx=2)

    zoom_content_btn = Button(zoom_frame, text="Content", width=6, command=paper.zoom_to_content)
    zoom_content_btn.pack(side='left', padx=2)

    def update_zoom_label(event=None, lbl=zoom_label, p=paper):
      lbl.config(text="%d%%" % int(p._scale * 100))
    paper.bind('<<zoom-changed>>', update_zoom_label)

    self.papers.append( paper)
    self.change_paper( _tab_name)
    self.notebook.selectpage( Pmw.END)
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
      dialog = Pmw.MessageDialog( self,
                                  title= _("Really close?"),
                                  message_text = _("There are unsaved changes in file %s, what should I do?") % name,
                                  buttons = (_('Close'),_('Save'),_('Cancel')),
                                  defaultbutton = _('Close'))
      result = dialog.activate()
      if result == _('Save'):
        self.save_CDML()
      elif result == _('Cancel'):
        return 0 # we skip away
    self.papers.remove( p)

    # cleanup
    # find the name of the tab
    name = self.get_paper_tab_name( p)
    del self._tab_name_2_paper[ name]
    p.mrproper()
    self.notebook.delete( name or Pmw.SELECT)
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
