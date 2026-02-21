"""Paper properties and standard management mixin methods for BKChem paper."""

import copy
import os
import xml.dom.minidom as dom

from tkinter import ALL

from bkchem import data
from bkchem import classes
from bkchem import bkchem_config
from bkchem import dom_extensions
from bkchem import os_support
from bkchem import safe_xml
from bkchem import theme_manager
from bkchem.arrow_lib import BkArrow
from bkchem.molecule_lib import BkMolecule
from bkchem import graphics
from bkchem.singleton_store import Store


class PaperPropertiesMixin:
	"""Paper properties and standard management helpers extracted from paper.py."""

	@property
	def molecules(self):
		return [o for o in self.stack if isinstance( o, BkMolecule)]


	@property
	def arrows(self):
		return [o for o in self.stack if isinstance( o, BkArrow)]


	@property
	def pluses(self):
		return [o for o in self.stack if isinstance( o, classes.plus)]


	@property
	def texts(self):
		return [o for o in self.stack if isinstance( o, classes.text)]


	@property
	def vectors(self):
		return [o for o in self.stack if isinstance( o, graphics.vector_graphics_item)]


	@property
	def top_levels(self):
		return self.stack


	@property
	def full_path(self):
		return os.path.abspath( os.path.join( self.file_name['dir'], self.file_name['name']))


	@property
	def window_name(self):
		return self.create_window_name( self.file_name)


	@staticmethod
	def create_window_name(name_dict):
		if name_dict['ord'] == 0:
			return name_dict['name']
		else:
			return name_dict['name'] + '<%d>' % name_dict['ord']


	def get_base_name( self):
		return os.path.splitext( self.file_name['name'])[0]


	def set_default_paper_properties( self):
		t = self.standard.paper_type
		o = self.standard.paper_orientation
		if o == 'portrait':
			sy, sx = data.paper_types[t]
		else:
			sx, sy = data.paper_types[t]

		self._paper_properties = {'type': t,
															'orientation': o,
															'size_x': sx,
															'size_y': sy}

		# use theme colors for paper background (display-only, not saved to CDML)
		paper_fill = theme_manager.get_paper_color('fill')
		paper_outline = theme_manager.get_paper_color('outline')
		if not 'background' in self.__dict__ or not self.background:
			self.background = self.create_rectangle( 0, 0, '%dm'%sx, '%dm'%sy, fill=paper_fill, outline=paper_outline, tags="no_export")
		else:
			self.coords( self.background, 0, 0, '%dm'%sx, '%dm'%sy)
			self.itemconfig( self.background, fill=paper_fill, outline=paper_outline)

		# crop svg
		self._paper_properties['crop_svg'] = self.standard.paper_crop_svg
		# crop margin
		self._paper_properties['crop_margin'] = self.standard.paper_crop_margin
		self._paper_properties['use_real_minus'] = Store.pm.get_preference( "use_real_minus") or 0
		self._paper_properties['replace_minus'] = Store.pm.get_preference( "replace_minus") or 0
		self.update_scrollregion()
		# redraw hex grid overlay to match paper dimensions
		if hasattr(self, '_hex_grid_overlay') and self._hex_grid_overlay:
			if self._hex_grid_overlay.visible:
				self._hex_grid_overlay.redraw()


	def create_background( self):
		sx = self._paper_properties['size_x']
		sy = self._paper_properties['size_y']
		# use theme colors for paper background (display-only, not saved to CDML)
		paper_fill = theme_manager.get_paper_color('fill')
		paper_outline = theme_manager.get_paper_color('outline')

		if not 'background' in self.__dict__ or not self.background:
			self.background = self.create_rectangle( 0, 0, '%dm'%sx, '%dm'%sy, fill=paper_fill, outline=paper_outline, tags="no_export")
		else:
			self.coords( self.background, 0, 0, '%dm'%sx, '%dm'%sy)
			self.itemconfig( self.background, fill=paper_fill, outline=paper_outline)


	def set_paper_properties( self, type=None, orientation=None, x=None, y=None, crop_svg=None, all=None, crop_margin=None, use_real_minus=None, replace_minus=None):
		if all:
			self._paper_properties = copy.copy( all)
			return
		if type:
			if type != 'custom':
				t = type or self.standard.paper_type
				o = orientation or self.standard.paper_orientation
				if o == 'portrait':
					sy, sx = data.paper_types[t]
				else:
					sx, sy = data.paper_types[t]
			else:
				t = 'custom'
				o = orientation or self._paper_properties['orientation']
				sx, sy = x, y
			self._paper_properties['type'] = t
			self._paper_properties['orientation'] = o
			self._paper_properties['size_x'] = sx
			self._paper_properties['size_y'] = sy

		# crop svg
		if crop_svg is not None:
			self._paper_properties['crop_svg'] = crop_svg

		if crop_margin is not None:
			self._paper_properties['crop_margin'] = crop_margin

		if use_real_minus is not None:
			old = 'use_real_minus' in self._paper_properties and self._paper_properties['use_real_minus'] or 0
			self._paper_properties['use_real_minus'] = use_real_minus
			if old != use_real_minus:
				[i.redraw() for i in self.stack]

		if replace_minus is not None:
			self._paper_properties['replace_minus'] = replace_minus

		self.create_background()
		self.update_scrollregion()
		# redraw hex grid overlay to match new paper dimensions
		if hasattr(self, '_hex_grid_overlay') and self._hex_grid_overlay:
			if self._hex_grid_overlay.visible:
				self._hex_grid_overlay.redraw()


	def update_scrollregion( self):
		x1,y1,x2,y2 = self.bbox(ALL)
		self.config( scrollregion=(x1-100,y1-100,x2+100,y2+100))


	def get_paper_property( self, name):
		if name in self._paper_properties:
			return self._paper_properties[ name]
		else:
			return None


	def read_standard_from_dom( self, d):
		std = dom_extensions.getFirstChildNamed( d, 'standard')
		if std:
			st = classes.standard()
			st.read_package( std)
			return st
		return None


	def apply_current_standard( self, objects=[], old_standard=None, template_mode=0):
		"""if no objects are given all are used, if old_standard is given only the values
		that have changed are applied; in template mode no changes of paper format are made"""
		if not template_mode:
			self.create_background()
		objs = objects or self.top_levels
		to_redraw = []
		for m in objs:
			if m.object_type == 'molecule':
				for b in m.bonds:
					b.read_standard_values( self.standard, old_standard=old_standard)
					to_redraw.append( b)
				for a in m.atoms:
					a.read_standard_values( self.standard, old_standard=old_standard)
					to_redraw.append( a)
			elif m.object_type != "point":
				m.read_standard_values( self.standard, old_standard=old_standard)
				to_redraw.append( m)
		return to_redraw


	def get_personal_standard( self):
		name = os_support.get_config_filename( 'standard.cdml', level="personal", mode="r")
		if name:
			try:
				cdml = safe_xml.parse_dom_from_file( name).childNodes[0]
			except IOError:
				return classes.standard()
			return self.read_standard_from_dom( cdml)
		return classes.standard()


	def save_personal_standard( self, st):
		name = os_support.get_config_filename( 'standard.cdml', level="personal", mode="w")
		if name:
			doc = dom.Document()
			root = dom_extensions.elementUnder( doc, 'cdml', attributes = (('version', bkchem_config.current_CDML_version),
																																			( 'xmlns', data.cdml_namespace)))
			info = dom_extensions.elementUnder( root, 'info')
			dom_extensions.textOnlyElementUnder( info, 'author_program', 'BKChem', attributes = (('version',bkchem_config.current_BKChem_version),))
			metadata = dom_extensions.elementUnder( root, 'metadata')
			dom_extensions.elementUnder( metadata, 'doc', attributes=(('href', data.cdml_doc_url),))
			root.appendChild( st.get_package( doc))
			dom_extensions.safe_indent( root)
			try:
				f = open(name, 'wb')
			except IOError:
				return 0
			try:
				f.write(doc.toxml('utf-8'))
			except IOError:
				f.close()
				return 0
			f.close()
			return name
		return 0
