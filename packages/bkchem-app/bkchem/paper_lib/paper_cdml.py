"""CDML serialization mixin methods for BKChem paper."""

import os
import tkinter.messagebox
import xml.dom.minidom as dom

from bkchem import data
from bkchem import messages
from bkchem import bkchem_config
from bkchem import dom_extensions
from bkchem import os_support
from bkchem import CDML_versions
from bkchem.id_manager import id_manager
from bkchem.molecule_lib import BkMolecule
from bkchem.singleton_store import Store

import builtins
_ = getattr( builtins, "_", None)
if not _:
	def _( text):
		return text
	builtins._ = _


class PaperCDMLMixin:
	"""CDML read/write helpers extracted from paper.py."""

	def read_package( self, CDML, draw=True):
		self.onread_id_sandbox_activate() # to sandbox the ids

		original_version = CDML.getAttribute( 'version')
		success = CDML_versions.transform_dom_to_version( CDML, bkchem_config.current_CDML_version)
		if not success:
			if not tkinter.messagebox.askokcancel(_('Proceed'),
																			_('''This CDML document does not seem to have supported version.
																			\n Do you want to proceed reading this document?'''),
																			default = 'ok',
																			parent=self):
				return None
		# paper properties
		paper = [o for o in CDML.childNodes if (not o.nodeValue) and (o.localName == 'paper')]
		if paper:
			paper = paper[0]
			t = paper.getAttribute( 'type')
			o = paper.getAttribute( 'orientation')
			sx = paper.getAttribute( 'size_x')
			sy = paper.getAttribute( 'size_y')
			if paper.getAttribute( 'crop_svg'):
				cr = int( paper.getAttribute( 'crop_svg'))
			else:
				cr = 1
			cm = int( paper.getAttribute( 'crop_margin') or self.standard.paper_crop_margin)
			use_real_minus = int( paper.getAttribute( 'use_real_minus') or Store.pm.get_preference( "use_real_minus") or 0)
			replace_minus = int( paper.getAttribute( 'replace_minus') or Store.pm.get_preference( "replace_minus") or 0)
			self.set_paper_properties( type=t, orientation=o, x=sx, y=sy, crop_svg=cr, crop_margin=cm, use_real_minus=use_real_minus, replace_minus=replace_minus)
		else:
			self.set_default_paper_properties()
		# viewport
		viewport = dom_extensions.getFirstChildNamed( CDML, 'viewport')
		if viewport:
			viewport = viewport.getAttribute( 'viewport')
			self.set_viewport( view= list(map( float, viewport.split(' '))))
		else:
			self.set_viewport()
		# standard must be read before all items
		new_standard = self.read_standard_from_dom( CDML)
		old_standard = self.standard
		if new_standard:
			self.standard = new_standard
		for p in CDML.childNodes:
			if p.nodeName in data.loadable_types:
				o = self.add_object_from_package( p)
				if not o:
					continue
				if o.object_type == 'molecule':
					if not o.is_connected():
						mols = o.get_disconnected_subgraphs()
					else:
						mols = [o]
					for mol in mols:
						if float( original_version) < 0.12:
							# we need to know if the bond is positioned according to the rules or the other way
							# it is however very expensive for large molecules with many double bonds and therefore
							# it was in version '0.12' of CDML moved to the saved package and does not have to be
							# checked on start anymore
							[b.post_read_analysis() for b in mol.bonds]
					if draw:
						[mol.draw( automatic="none") for mol in mols]
				else:
					if draw:
						o.draw()
		# now check if the old standard differs
		if new_standard and old_standard != self.standard and not Store.app.in_batch_mode:
			if self._is_template_file():
				pass
			elif not tkinter.messagebox.askokcancel(_('Replace standard values'),
																			messages.standards_differ_text,
																			default = 'ok',
																			parent=self):
				self.standard = old_standard

		# external data
		ees = CDML.getElementsByTagName( "external-data")
		if ees:
			[self.edm.read_package( ee) for ee in ees]

		# finish
		# we close the sandbox and generate new ids for everything
		self.onread_id_sandbox_finish()

		# this forces forgetting of old viewport and effectively transforms the coordinates for rest of work
		self.set_viewport()

		if draw:
			self.add_bindings()
		self.um.start_new_record()


	#============================================
	def _is_template_file( self):
		"""Return True when the current file lives in a template directory."""
		full_path = self.full_path
		if not full_path:
			return False
		full_path = os.path.abspath( full_path)
		for template_dir in os_support.get_dirs( 'template'):
			if not template_dir:
				continue
			template_dir = os.path.abspath( template_dir)
			try:
				if os.path.commonpath( [full_path, template_dir]) == template_dir:
					return True
			except ValueError:
				continue
		return False


	def onread_id_sandbox_activate( self):
		"""For reading we provide a new, clean id_manager as a sandbox to prevent
		clashes between ids that might be already on the paper and ids that are in the file.
		This is especialy needed for copying and template addition (although this is done somewhere else)"""
		self._old_id_manager = Store.id_manager
		Store.id_manager = id_manager()


	def onread_id_sandbox_finish( self, apply_to=None):
		Store.id_manager = self._old_id_manager
		del self._old_id_manager
		if apply_to is None:
			os = self.stack
		else:
			os = apply_to
		for o in os:
			o.generate_id()
			if isinstance( o, BkMolecule):
				[ch.generate_id() for ch in o.children]


	def get_package( self):
		doc = dom.Document()
		root = dom_extensions.elementUnder( doc, 'cdml', attributes = (('version', bkchem_config.current_CDML_version),
																																		( 'xmlns', data.cdml_namespace)))
		info = dom_extensions.elementUnder( root, 'info')
		dom_extensions.textOnlyElementUnder( info, 'author_program', 'BKChem', attributes = (('version',bkchem_config.current_BKChem_version),))
		metadata = dom_extensions.elementUnder( root, 'metadata')
		dom_extensions.elementUnder( metadata, 'doc', attributes=(('href', data.cdml_doc_url),))
		paper = dom_extensions.elementUnder( root, 'paper',
																					attributes = (('type', self._paper_properties['type']),
																												('orientation', self._paper_properties['orientation']),
																												('crop_svg', '%d' % self._paper_properties['crop_svg']),
																												('crop_margin', '%d' % self._paper_properties['crop_margin']),
																												('use_real_minus', '%d' % self._paper_properties['use_real_minus']),
																												('replace_minus', '%d' % self._paper_properties['replace_minus'])
																												))
		if self._paper_properties['type'] == 'custom':
			dom_extensions.setAttributes( paper, (('size_x', '%d' % self._paper_properties['size_x']),
																					('size_y', '%d' % self._paper_properties['size_y'])))
		dom_extensions.elementUnder( root, 'viewport', attributes = (('viewport','%f %f %f %f' % self._view),))
		root.appendChild( self.standard.get_package( doc))
		for o in self.stack:
			root.appendChild( o.get_package( doc))
		for a in self.arrows:
			if not a.reaction.is_empty():
				root.appendChild( a.reaction.get_package( doc))

		# external data
		edm_doc = self.edm.get_package( doc)
		if edm_doc:
			root.appendChild( edm_doc)

		return doc


	def get_cropping_bbox( self):
		if hasattr( self, '_cropping_bbox') and self._cropping_bbox:
			return self._cropping_bbox

		margin = self.get_paper_property('crop_margin')
		items = list( self.find_all())
		items.remove( self.background)
		# exclude hex grid dots from crop bbox
		hex_items = set(self.find_withtag("hex_grid"))
		if hex_items:
			items = [i for i in items if i not in hex_items]

		if not items:
			return None

		x1, y1, x2, y2 = self.list_bbox( items)
		return x1-margin, y1-margin, x2+margin, y2+margin


	def set_cropping_bbox( self, coords):
		self._cropping_bbox = coords


	def fix_current_cropping_bbox( self):
		self.set_cropping_bbox( self.get_cropping_bbox())
