"""Object factory mixin methods for BKChem paper."""

from bkchem import classes
from bkchem import graphics
from bkchem.arrow_lib import BkArrow
from bkchem.molecule_lib import BkMolecule
from bkchem.reaction_lib import BkReaction


class PaperFactoriesMixin:
	"""Object creation and deserialization helpers extracted from paper.py."""

	def new_molecule( self):
		mol = BkMolecule( self)
		self.stack.append( mol)
		return mol


	def add_molecule( self, mol):
		self.stack.append( mol)


	def new_arrow( self, points=[], spline=0, type="normal"):
		arr = BkArrow( self, type=type, points=points, spline=spline)
		self.stack.append( arr)
		arr.draw()
		return arr


	def new_plus( self, x, y):
		pl = classes.plus( self, xy = (x,y))
		self.stack.append( pl)
		pl.draw()
		return pl


	def new_text( self, x, y, text=''):
		txt = classes.text( self, xy=(x,y), text=text)
		self.stack.append( txt)
		return txt


	def new_rect( self, coords):
		rec = graphics.rect( self, coords=coords)
		self.stack.append( rec)
		return rec


	def new_oval( self, coords):
		ovl = graphics.oval( self, coords=coords)
		self.stack.append( ovl)
		return ovl


	def new_square( self, coords):
		rec = graphics.square( self, coords=coords)
		self.stack.append( rec)
		return rec


	def new_circle( self, coords):
		ovl = graphics.circle( self, coords=coords)
		self.stack.append( ovl)
		return ovl


	def new_polygon( self, coords):
		p = graphics.polygon( self, coords=coords)
		self.stack.append( p)
		return p


	def new_polyline( self, coords):
		p = graphics.polyline( self, coords=coords)
		self.stack.append( p)
		return p


	def add_object_from_package( self, package):
		if package.nodeName == 'molecule':
			o = BkMolecule( self, package=package)
		elif package.nodeName == 'arrow':
			o = BkArrow( self, package=package)
		elif package.nodeName == 'plus':
			o = classes.plus( self, package=package)
		elif package.nodeName == 'text':
			o = classes.text( self, package=package)
		elif package.nodeName == 'rect':
			o = graphics.rect( self, package=package)
		elif package.nodeName == 'oval':
			o = graphics.oval( self, package=package)
		elif package.nodeName == 'square':
			o = graphics.square( self, package=package)
		elif package.nodeName == 'circle':
			o = graphics.circle( self, package=package)
		elif package.nodeName == 'polygon':
			o = graphics.polygon( self, package=package)
		elif package.nodeName == 'polyline':
			o = graphics.polyline( self, package=package)
		elif package.nodeName == 'reaction':
			react = BkReaction()
			react.read_package( package)
			if react.arrows:
				react.arrows[0].reaction = react
			o = None
		else:
			o = None
		if o:
			self.stack.append( o)
		return o
