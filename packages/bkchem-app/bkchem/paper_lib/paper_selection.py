"""Selection management mixin methods for BKChem paper."""

import bkchem.chem_compat

from bkchem import bkchem_utils
from bkchem.group_lib import BkGroup
from bkchem.molecule_lib import BkMolecule


class PaperSelectionMixin:
	"""Selection management helpers extracted from paper.py."""

	@property
	def selected_mols(self):
		return [o for o in self.selected_to_unique_top_levels()[0] if isinstance( o, BkMolecule)]


	@property
	def selected_atoms(self):
		return [o for o in self.selected if bkchem.chem_compat.is_chemistry_vertex(o)]


	@property
	def selected_bonds(self):
		return [o for o in self.selected if bkchem.chem_compat.is_chemistry_edge(o)]


	@property
	def two_or_more_selected(self):
		if len( self.selected_to_unique_top_levels()[0]) > 1:
			return True
		else:
			return False


	@property
	def groups_selected(self):
		return [o for o in self.selected if isinstance( o, BkGroup)]


	@property
	def one_mol_selected(self):
		if len( self.selected_mols) != 1:
			return False
		else:
			return True


	def select( self, items):
		"adds an object to the list of other selected objects and calls their select() method"
		for o in items:
			if o.object_type in ('arrow','polygon','polyline'):
				# we cannot allow arrows or polygons to be selected because selection of arrow and its points
				# doubles some actions (moving etc.) and this couldn't be easily solved other way
				self.select( o.points)
			elif o.object_type == 'selection_rect' or o.object_type == 'selection_square':
				return
			elif o not in self.selected:
				self.selected.append( o)
				o.select()
		self.event_generate( "<<selection-changed>>")


	def unselect( self, items):
		"reverse of select()"
		for item in items:
			try:
				self.selected.remove( item)
				item.unselect()
			except ValueError:
				pass #warn( 'trying to unselect not selected object '+id( item))
		self.event_generate( "<<selection-changed>>")


	def unselect_all( self):
		[o.unselect() for o in self.selected]
		self.selected = []
		self.event_generate( "<<selection-changed>>")


	def select_all( self):
		self.unselect_all()
		self.select( [o for o in map( self.id_to_object, self.find_all()) if o and hasattr( o, 'select') and o.object_type != 'arrow'])
		self.add_bindings()


	def selected_to_unique_top_levels( self):
		"""maps all items in self.selected to their top_levels (atoms->molecule etc.),
		filters them to be unique and returns tuple of (unique_top_levels, unique)
		where unique is true when there was only one item from each container"""
		filtrate = []
		unique = 1
		for o in self.selected:
			if o.object_type == 'atom' or o.object_type == 'bond':
				if o.molecule not in filtrate:
					filtrate.append( o.molecule)
				else:
					unique = 0
			elif o.object_type == 'point':
				if o.arrow not in filtrate:
					filtrate.append( o.arrow)
				else:
					unique = 0
			else:
				if o not in filtrate:
					filtrate.append( o)
				else:
					unique = 0
		return (filtrate, unique)


	def toggle_center_for_selected( self):
		for o in self.selected:
			if o.object_type == 'atom' and o.show:
				o.toggle_center()


	def delete_selected( self):
		# ARROW
		to_delete = [o for o in self.selected if o.object_type == 'arrow']
		[a.arrow.delete_point( a) for a in self.selected if a.object_type == 'point' and (a.arrow not in to_delete)]
		for a in self.arrows:
			if a.is_empty_or_single_point():
				if a not in to_delete:
					to_delete += [a]
			else:
				a.redraw()
		list(map( self.stack.remove, to_delete))
		[o.delete() for o in to_delete]
		# PLUS
		to_delete = [o for o in self.selected if o.object_type == 'plus']
		list(map( lambda o: o.delete(), to_delete))
		list(map( self.stack.remove, to_delete))
		# TEXT
		to_delete = [o for o in self.selected if o.object_type == 'text']
		for t in to_delete:
			t.delete()
			self.stack.remove( t)
		# VECTOR GRAPHICS
		for o in [obj for obj in self.selected if obj.object_type == 'rect' or obj.object_type == 'oval']:
			o.delete()
			self.stack.remove( o)
		# polygon is special (points were removed on begining together with arrow points)
		to_delete = [o for o in self.selected if o.object_type in ('polygon','polyline')]
		for a in self.vectors:
			if a.object_type in ('polygon','polyline'):
				if a.is_empty_or_single_point():
					if a not in to_delete:
						to_delete += [a]
				else:
					a.redraw()
		list(map( self.stack.remove, to_delete))
		[o.delete() for o in to_delete]
		# BOND AND ATOM
		bonds = [o for o in self.selected if o.object_type == 'bond']
		atoms = [o for o in self.selected if o.object_type == 'atom']
		deleted, new, mols_to_delete = [], [], []
		changed_mols = []
		for mol in self.molecules:
			items = [o for o in bonds+atoms if o.molecule == mol]
			if items:
				changed_mols.append( mol)
			now_deleted, new_mols = mol.delete_items( items)
			deleted += now_deleted
			new += new_mols
			if new_mols:
				mols_to_delete.append( mol)
		if new:
			list(map( self.stack.remove, mols_to_delete))
			self.stack.extend( new)
		empty_mols = [o for o in self.molecules if o.is_empty()]
		[self.stack.remove( o) for o in empty_mols]
		# start new undo
		if self.selected:
			self.start_new_undo_record()
		self.selected = []
		#return deleted

		## check reactions
		[a.reaction.check_the_references( self.stack) for a in self.arrows]
		self.event_generate( "<<selection-changed>>")


	def bonds_to_update( self, exclude_selected_bonds=True):
		a = set().union(*(set(i) for i in (v.neighbor_edges for v in self.selected
																													if v.object_type == "atom")))
		# if bond is also selected then it moves with and should not be updated
		if exclude_selected_bonds:
			return [b for b in a if b not in self.selected]
		else:
			return a


	def atoms_to_update( self):
		a = []
		for o in self.selected:
			if o.object_type == 'bond':
				a.extend( o.atoms)
		if a:
			return bkchem_utils.difference( bkchem_utils.filter_unique( a), self.selected)
		else:
			return []


	def arrows_to_update( self):
		a = [o.arrow for o in [p for p in self.selected if p.object_type == 'point']]
		return bkchem_utils.filter_unique( a)
