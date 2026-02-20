"""Layout, alignment, and cleanup mixin methods for BKChem paper."""

import copy
import math
import operator
import sys

import oasa
import oasa.coords_generator
from oasa import geometry
from oasa.transform_lib import Transform

import bkchem.chem_compat

from bkchem import bkchem_utils
from bkchem import dialogs
from bkchem import parents
from bkchem.atom_lib import BkAtom
from bkchem.group_lib import BkGroup
from bkchem.textatom_lib import BkTextatom
from bkchem.molecule_lib import BkMolecule
from bkchem.singleton_store import Store

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get('_', lambda m: m)


class PaperLayoutMixin:
	"""Layout, alignment, and cleanup helpers extracted from paper.py."""

	def align_selected( self, mode):
		"""aligns selected items according to mode - t=top, b=bottom,
		l=left, r=right, h=horizontal center, v=vertical center"""
		# locate all selected top_levels, filter them to be unique
		to_align, unique = self.selected_to_unique_top_levels()
		# check if there is anything to align
		if len( to_align) < 2:
			return None
		bboxes = []
		if not unique:
			# if not unique align is done according to bboxes of top_levels
			for o in to_align:
				bboxes.extend( o.bbox())
		else:
			# otherwise align according to bboxes of items
			for o in self.selected:
				if o.object_type == 'atom':
					if o.show:
						bboxes.extend( o.ftext.bbox())
					else:
						x, y = o.get_xy()
						bboxes.extend( (x,y,x,y))
				elif o.object_type == 'point':
					x, y = o.get_xy()
					bboxes.extend( (x,y,x,y))
				elif o.object_type == 'bond':
					x1, y1, x2, y2 = o.bbox()
					x = (x1+x2)/2
					y = (y1+y2)/2
					bboxes.extend( (x,y,x,y))
				else:
					bboxes.extend( o.bbox())
		# now the align itself
		# modes dealing with x
		if mode in 'lrv':
			if mode == 'l':
				xs = [bboxes[i] for i in range( 0, len( bboxes), 4)]
				x = min( xs)
			elif mode == 'r':
				xs = [bboxes[i] for i in range( 2, len( bboxes), 4)]
				x = max( xs)
			else:
				xmaxs = [bboxes[i] for i in range( 0, len( bboxes), 4)]
				xmins = [bboxes[i] for i in range( 2, len( bboxes), 4)]
				xs = list(map( operator.add, xmaxs, xmins))
				xs = list(map( operator.div, xs, len(xs)*[2]))
				x = (max(xs) + min(xs)) / 2
			for i in range( len( xs)):
				to_align[i].move( x-xs[i], 0)
		# modes dealing with y
		elif mode in 'tbh':
			if mode == 'b':
				ys = [bboxes[i] for i in range( 3, len( bboxes), 4)]
				y = max( ys)
			elif mode == 't':
				ys = [bboxes[i] for i in range( 1, len( bboxes), 4)]
				y = min( ys)
			else:
				ymaxs = [bboxes[i] for i in range( 1, len( bboxes), 4)]
				ymins = [bboxes[i] for i in range( 3, len( bboxes), 4)]
				ys = list(map( operator.add, ymaxs, ymins))
				ys = list(map( operator.div, ys, len(ys)*[2]))
				y = (max(ys) + min(ys)) / 2
			for i in range( len( ys)):
				to_align[i].move( 0, y-ys[i])
		self.start_new_undo_record()


	def place_next_to_selected( self, mode, align, dist, obj):
		"""Places an object (obj) in a distance (dist) next to the selection,
		by changing the x or the y value of the object according to the mode.
		Modes: l= left r=right a=above b=below
		Align: t=top b=bottom l=left r=right h=horizontal v=vertical
		align or mode can be set to "" to use only one function"""
		# locate all selected top_levels, filter them to be unique
		cp, unique = self.selected_to_unique_top_levels()
		# now find center of bbox of all objects in cp
		self.place_next_to_bbox( mode, align, dist, obj, self.common_bbox( cp))
		self.start_new_undo_record()


	def place_next_to_bbox( self, mode, align, dist, obj, bbox):
		"""Places an object (obj) in a distance (dist) next to the bbox,
		by changing the x or the y value of the object according to the mode.
		Modes: l= left r=right a=above b=below
		Align: t=top b=bottom l=left r=right h=horizontal v=vertical
		align or mode can be set to "" to use only one function"""
		# now find center of bbox of all objects in cp
		xmin, ymin, xmax, ymax = bbox
		x1o,y1o,x2o,y2o = obj.bbox()
		if mode == "l":
				obj.move(xmin-x2o-dist, 0)
		elif mode == "r":
				obj.move(xmax-x1o+dist, 0)
		elif mode == "b":
				obj.move(0, ymax-y1o+dist)
		elif mode == "a":
				obj.move(0, ymin-y2o-dist)
		if align == "t":
				obj.move (0,ymin-y1o)
		elif align == "b":
				obj.move (0,ymax-y2o)
		elif align == "l":
				obj.move (xmin-x1o,0)
		elif align == "r":
				obj.move (xmax-x2o,0)
		elif align == "v":
				obj.move ((xmax+xmin)/2-(x1o+x2o)/2,0)
		elif align == "h":
				obj.move (0,(ymax+ymin)/2-(y1o+y2o)/2)


	def swap_sides_of_selected( self, mode="vertical"):
		"""mirrors the selected things, vertical uses y-axis as a mirror plane,
		horizontal x-axis"""
		# locate all selected top_levels, filter them to be unique
		to_align, unique = self.selected_to_unique_top_levels()
		to_select_then = copy.copy( self.selected)
		self.unselect_all()
		# check if there is anything to align
		if len( to_align) < 1:
			return None
		bboxes = []
		for o in to_align:
			bboxes.extend( o.bbox())
		# vertical (rotate around y axis)
		if mode == 'vertical':
			xs = [bboxes[i] for i in range( 0, len( bboxes), 2)]
			x0 = (max( xs) + min( xs)) / 2.0
			for o in to_align:
				if o.object_type == 'molecule':
					tr = Transform()
					tr.set_move( -x0, 0)
					tr.set_scaling_xy( -1, 1)
					tr.set_move( x0, 0)
					o.transform( tr)
				else:
					pass
		# horizontal (rotate around x axis)
		if mode == 'horizontal':
			ys = [bboxes[i] for i in range( 1, len( bboxes), 2)]
			y0 = (max( ys) + min( ys)) / 2.0
			for o in to_align:
				if o.object_type == 'molecule':
					tr = Transform()
					tr.set_move( 0, -y0)
					tr.set_scaling_xy( 1, -1)
					tr.set_move( 0, y0)
					o.transform( tr)
				else:
					pass

		self.select( to_select_then)
		self.add_bindings()
		self.start_new_undo_record()


	def lift_selected_to_top( self):
		os = self.selected_to_unique_top_levels()[0]
		for o in os:
			self.stack.remove( o)
			self.stack.append( o)
		Store.log( _("selected items were lifted"))
		self.add_bindings()
		self.start_new_undo_record()


	def lower_selected_to_bottom( self):
		os = self.selected_to_unique_top_levels()[0]
		for o in os:
			self.stack.remove( o)
			self.stack.insert( 0, o)
		Store.log( _("selected items were put back"))
		self.add_bindings()
		self.start_new_undo_record()


	def swap_selected_on_stack( self):
		os = self.selected_to_unique_top_levels()[0]
		indxs = sorted(self.stack.index(o) for o in os)
		for i in range( len( indxs) // 2):
			self.stack[ indxs[i]], self.stack[ indxs[-1-i]] =  self.stack[ indxs[-1-i]], self.stack[ indxs[i]]
		Store.log( _("selected items were swapped"))
		self.add_bindings()
		self.start_new_undo_record()


	def center_object( self, obj, x, y):
		"""moves an object so that its centered on coordinates x,y"""
		x1, y1, x2, y2 = obj.bbox()
		dx = x2 - x1
		dy = y2 - y1
		obj.move( x-x1-dx/2.0, y-y1-dy/2.0)


	def center_objects( self, objs, x, y):
		"""moves a set of objects so that the center of the group is placed on coordinates x,y"""
		x1, y1, x2, y2 = self.common_bbox( objs)
		dx = x2 - x1
		dy = y2 - y1
		for obj in objs:
			obj.move( x-x1-dx/2.0, y-y1-dy/2.0)


	def common_bbox( self, objects):
		"""returns the bbox of all 'objects', in contrast to list_bbox it works with BKChem
		objects, not tkinter canvas objects"""
		if not objects:
			return None
		xmin, ymin, xmax, ymax = objects[0].bbox()
		for o in objects[:]:
			x0, y0, x1, y1 = o.bbox()
		if x0 < xmin:
			xmin = x0
		if y0 < ymin:
			ymin = y0
		if x1 > xmax:
			xmax = x1
		if ymax < y1:
			ymax = y1
		return xmin, ymin, xmax, ymax


	def list_bbox( self, items):
		"""extension of Canvas.bbox to provide support for lists of items"""
		self.dtag( 'bbox', 'bbox') # just to be sure
		for i in items:
			self.addtag_withtag( 'bbox', i)
		ret = self.bbox( 'bbox')
		self.dtag( 'bbox', 'bbox')
		return ret


	def clean_selected( self):
		"""cleans the geomerty of all selected molecules, the position of atoms that are selected will not be changed.
		The selection must define a continuos subgraph of the BkMolecule(s) otherwise the coords generation would not be possible,
		at least two atoms (one bond) must be selected for the program to give some meaningfull result"""
		# normalization of selection
		for item in self.selected:
			if item.object_type == 'bond':
				for a in item.atoms:
					if a not in self.selected:
						self.select( [a])

		mols, u = self.selected_to_unique_top_levels()
		for mol in mols:
			if isinstance( mol, BkMolecule):
				notselected = set( mol.atoms) - set( self.selected)
				selected = set( mol.atoms) & set( self.selected)
				# we must check if the selection defines one connected subgraph of the molecule
				# otherwise the coordinate generation will not work
				if len( selected) == 1:
					print("sorry, but the selection must contain at least two atoms (one bond)")
					return
				else:
					sub = mol.get_new_induced_subgraph( selected, mol.vertex_subgraph_to_edge_subgraph( selected))
					subs = [comp for comp in sub.get_connected_components()]
					if len( subs) != 1:
						print("sorry, but the selection must define a continuos block in the molecule")
						return

				# now we check what has been selected
				side = None
				if len( selected) == 2:
					# if only two atoms are selected we need the information about positioning to guess
					# how to mirror the molecule at the end
					atom1, atom2 = selected
					side = sum( [geometry.on_which_side_is_point( (atom1.x, atom1.y, atom2.x, atom2.y), (a.x,a.y)) for a in notselected])

				for a in notselected:
					a.x = None
					a.y = None

				oasa.coords_generator.calculate_coords( mol, force=0, bond_length=-1)

				if len( selected) == 2:
					side2 = sum( [geometry.on_which_side_is_point( (atom1.x, atom1.y, atom2.x, atom2.y), (a.x,a.y)) for a in notselected])
					if side * side2 < 0:
						x1, y1, x2, y2 = (atom1.x, atom1.y, atom2.x, atom2.y)
						centerx = ( x1 + x2) / 2
						centery = ( y1 + y2) / 2
						angle0 = geometry.clockwise_angle_from_east( x2 - x1, y2 - y1)
						if angle0 >= math.pi :
							angle0 = angle0 - math.pi
						tr = Transform()
						tr.set_move( -centerx, -centery)
						tr.set_rotation( -angle0)
						tr.set_scaling_xy( 1, -1)
						tr.set_rotation( angle0)
						tr.set_move(centerx, centery)

						mol.transform( tr)

			mol.redraw( reposition_double=1)
			self.start_new_undo_record()


	def handle_overlap( self):
		"puts overlaping molecules together to one and then calls handle_overlap(a1, a2) for that molecule"
		overlap = []
		for a in self.find_withtag('atom'):
			x, y = self.id_to_object( a).get_xy_on_paper()
			for b in self.find_overlapping( x-2, y-2, x+2, y+2):
				if (a != b) and ( 'atom' in self.gettags( b)):
					a1 = self.id_to_object( a)
					a2 = self.id_to_object( b)
					if ( abs( a1.x - a2.x) < 2) and ( abs( a1.y - a2.y) < 2):
						if (not [a2,a1] in overlap) and a1.z == a2.z:
							overlap.append( [a1,a2])

		deleted = []
		if overlap:
			mols = bkchem_utils.filter_unique( [[b.molecule for b in a] for a in overlap])
			a_eatenby_b1 = []
			a_eatenby_b2 = []
			for (mol, mol2) in mols:
				while (mol in a_eatenby_b1):
					mol = a_eatenby_b2[ a_eatenby_b1.index( mol)]
				while (mol2 in a_eatenby_b1):
					mol2 = a_eatenby_b2[ a_eatenby_b1.index( mol2)]
				if mol != mol2 and (mol2 not in a_eatenby_b1):
					mol.eat_molecule( mol2)
					a_eatenby_b1.append( mol2)
					a_eatenby_b2.append( mol)
					self.stack.remove( mol2)
				else:
					deleted.extend( mol.handle_overlap())
			deleted.extend(j for i in [mol.handle_overlap() for mol in bkchem_utils.difference(a_eatenby_b2, a_eatenby_b1)]
														for j in i)
			self.selected = bkchem_utils.difference( self.selected, deleted)
			self.add_bindings()
			Store.log( _('concatenated overlaping atoms'))

		preserved = []
		for a, b in overlap:
			preserved.append( a in deleted and b or a)
		return deleted, preserved


	def set_name_to_selected( self, name, interpret=1):
		"""sets name to all selected atoms and texts,
		also records it in an undo !!!"""
		if sys.version_info[0] > 2:
			if isinstance(name, bytes):
				name = name.decode('utf-8')
		else:
			if isinstance(name, str):
				name = name.decode('utf-8')
		vtype = None
		for item in self.selected[:]:
			if bkchem.chem_compat.is_chemistry_vertex(item):
				if name:
					self.unselect( [item])
					v = item.molecule.create_vertex_according_to_text( item, name, interpret=interpret)
					item.copy_settings( v)
					item.molecule.replace_vertices( item, v)
					item.delete()
					v.draw()
					self.select( [v])
					vtype = v.__class__.__name__
			if item.object_type == 'text':
				if name:
					item.xml_ftext = name
					item.redraw()
		if self.selected:
			self.start_new_undo_record()
		return vtype


	def expand_groups( self, selected=1):
		"""expands groups, if selected==1 only for selected, otherwise for all"""
		if selected:
			mols = [o for o in self.selected_to_unique_top_levels()[0] if o.object_type == 'molecule']
			atoms = [o for o in self.selected if isinstance( o, BkGroup)]
			self.unselect_all()
			for mol in mols:
				this_atoms = bkchem_utils.intersection( atoms, mol.atoms)
				mol.expand_groups( atoms = this_atoms)
		else:
			self.unselect_all()
			[m.expand_groups() for m in self.molecules]
		self.add_bindings()
		self.start_new_undo_record()


	def config_selected( self):
		if self.selected:
			dialog = dialogs.config_dialog( Store.app, self.selected[:])
			if dialog.changes_made:
				self.start_new_undo_record()
			self.add_bindings()


	def any_color_to_rgb_string( self, color):
		if not color:
			return "none"
		else:
			r, g, b = [(x < 256 and x) or (x >= 256 and x//256) for x in self.winfo_rgb( color)]
			return "#%02x%02x%02x" % (r,g,b)


	def mrproper( self):
		self.unselect_all()

		for a in self.stack:
			if isinstance( a, parents.container):
				for ch in a.children:
					if hasattr( ch, 'id'):
						Store.id_manager.unregister_id( ch.id, ch)

					if hasattr( ch, "paper"):
						try:
							ch.paper = None
						except KeyError:
							# Tried to set it on child, set it on parent
							ch.parent.paper = None
							pass
					if hasattr( ch, "canvas"):
						ch.canvas = None
					if hasattr( ch, "ftext") and ch.ftext:
						ch.ftext.canvas = None
						for i in ch.ftext.items:
							i.paper = None

			if isinstance( a, BkMolecule):
				for ch in a.children:
					ch.molecule = None
					if hasattr( ch, "group_graph"):
						ch.group_graph = None

					if isinstance( ch, BkAtom) or isinstance( ch, BkTextatom):
						for m in ch.marks:
							m.atom = None

		self.clean_paper()

		self.um.mrproper()

		del self.clipboard
		del self.standard
		del self.submode
		self.mode = None
		del self.selected
		del self._id_2_object
		del self.um
		del self.file_name


	def clean_paper( self):
		"removes all items from paper and deletes them from molecules and items"
		self.unselect_all()
		self.delete( 'all')
		self.background = None
		del self._id_2_object
		self._id_2_object = {}

		for obj in self.stack:
			obj.paper = None
			if hasattr( obj, 'id'):
				Store.id_manager.unregister_id( obj.id, obj)

		del self.stack
		self.stack = []
		self.um.clean()
		self.changes_made = 0


	def del_container( self, container):
		container.delete()
		self.stack.remove( container)


	def redraw_all(self):
		"""Redraws all the content of the paper."""
		for o in self.stack:
			o.redraw()
		# redraw hex grid if visible
		if hasattr(self, '_hex_grid_overlay') and self._hex_grid_overlay:
			if self._hex_grid_overlay.visible:
				self._hex_grid_overlay.redraw()
