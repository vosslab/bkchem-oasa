"""Viewport and coordinate transform mixin methods for BKChem paper."""

import math

from oasa.transform_lib import Transform


class PaperTransformsMixin:
	"""Viewport and coordinate transform helpers extracted from paper.py."""

	def set_viewport( self, view=(0,0,640,480)):
		x1, y1, x2, y2 = view
		self._view = tuple( view)

		self._real2screen = Transform()
		self._real2screen.set_move( -x1, -y1)
		ratiox, ratioy = 640/(x2-x1), 480/(y2-y1)
		self._real2screen.set_scaling_xy( ratiox, ratioy)
		self._ratio = math.sqrt( ratioy*ratiox)

		self._screen2real = Transform()
		ratiox, ratioy = (x2-x1)/640, (y2-y1)/480
		self._screen2real.set_scaling_xy( ratiox, ratioy)
		self._screen2real.set_move( x1, y1)

	def real_to_canvas(self, lenghts):
		"""Transforms distances or coordinates from real (as stored in eg: atom.x)
				to those in the canvas (as stored for items)."""
		try:
			result = []
			for lenght in lenghts:
				result.append(lenght*self._scale)
			return result
		except TypeError:
			return lenghts*self._scale

	def canvas_to_real(self, lenghts):
		"""Transforms distances or coordinates from those in the canvas (as stored for items)
				to real ones (as stored in eg: BkAtom.x)."""
		try:
			result = []
			for lenght in lenghts:
				result.append(lenght/self._scale)
			return result
		except TypeError:
			return lenghts/self._scale

	def screen_to_real_coords( self, coords):
		"""transforms set of x,y coordinates to real coordinates, input list must have even length.
		It's called when exporting files."""
		if len( coords) % 2:
			raise ValueError("only even number of coordinates could be transformed")
		out = []
		for i in range( 0, len( coords), 2):
			out.extend( self._screen2real.transform_xy( coords[i], coords[i+1]))
		return out


	def real_to_screen_coords( self, coords):
		"""transforms set of x,y coordinates to screen coordinates, input list must have even length.
		It's called when importing files."""
		if len( coords) % 2:
			raise ValueError("only even number of coordinates could be transformed")
		out = []
		for i in range( 0, len( coords), 2):
			out.extend( self._real2screen.transform_xy( coords[i], coords[i+1]))
		return out


	def screen_to_real_ratio( self):
		return 1.0/self._ratio


	def real_to_screen_ratio( self):
		return self._ratio
