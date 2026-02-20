"""Public entry point and orchestrator for 2D coordinate generation.

Produces RDKit-quality 2D coordinates without the RDKit dependency.
Uses ring system assembly, chain layout, collision resolution, and
force-field refinement.

Same interface as coords_generator: calculate_coords(mol, bond_length, force).
"""

from oasa.coords_gen import helpers
from oasa.coords_gen import phase1_rings
from oasa.coords_gen import phase2_chains
from oasa.coords_gen import phase3_collisions
from oasa.coords_gen import phase4_refinement


#============================================
class CoordsGenerator2:
	"""Four-phase 2D coordinate generator.

	Phase 1: Ring system placement (fused ring assembly)
	Phase 2: Chain and substituent placement (BFS outward)
	Phase 3: Collision detection and resolution
	Phase 4: Force-field refinement (spring model)
	"""

	def __init__(self, bond_length: float = 1.0):
		self.bond_length = bond_length

	#============================================
	def calculate_coords(self, mol, bond_length: float = 1.0,
		force: int = 0) -> None:
		"""Main entry point. Same signature as coords_generator.

		Args:
			mol: OASA molecule object.
			bond_length: target bond length; 0 keeps current; -1 derives from
				existing coords.
			force: if truthy, recalculate all coordinates.
		"""
		self.mol = mol
		# handle bond_length parameter
		if bond_length > 0:
			self.bond_length = bond_length
		elif bond_length < 0:
			# derive from existing coords
			bls = []
			for b in mol.edges:
				a1, a2 = b.vertices
				if a1.x is not None and a2.x is not None:
					bls.append(helpers.point_dist(a1.x, a1.y, a2.x, a2.y))
			if bls:
				self.bond_length = sum(bls) / len(bls)

		# check if all coords already present
		atms_with_coords = set(
			a for a in mol.vertices if a.x is not None and a.y is not None
		)
		if len(atms_with_coords) == len(mol.vertices) and not force:
			return

		if force:
			for a in mol.vertices:
				a.x = None
				a.y = None
			atms_with_coords = set()

		# build stereochemistry lookup
		self.stereo = {}
		for st in mol.stereochemistry:
			if st.__class__.__name__ == "CisTransStereochemistry":
				for a in (st.references[0], st.references[-1]):
					self.stereo[a] = self.stereo.get(a, []) + [st]

		# get SSSR rings
		self.rings = mol.get_smallest_independent_cycles()

		# identify ring atoms for later use in collision/refinement
		self.ring_atoms = set()
		for ring in self.rings:
			self.ring_atoms.update(ring)

		# placed tracks atoms with coordinates
		placed = set(atms_with_coords)

		# initialize deferred ring system state for Phase 1/2 coordination
		self.deferred_ring_systems = []
		self.ring_system_membership = {}

		# Phase 1: ring system placement
		placed = phase1_rings.place_ring_systems(self, placed)

		# build membership map for deferred systems so Phase 2 can find them
		for ring_system in self.deferred_ring_systems:
			for ring in ring_system:
				for atom in ring:
					self.ring_system_membership[atom] = ring_system

		# if no rings, seed a 2-atom backbone
		if not placed and len(mol.vertices) >= 2:
			a1 = mol.vertices[0]
			a2 = a1.neighbors[0]
			a1.x, a1.y = 0.0, 0.0
			a2.x, a2.y = self.bond_length, 0.0
			placed.add(a1)
			placed.add(a2)
		elif not placed and len(mol.vertices) == 1:
			a = mol.vertices[0]
			a.x, a.y = 0.0, 0.0
			a.z = 0
			placed.add(a)

		# Phase 2: chain and substituent placement
		phase2_chains.place_chains(self, placed)

		# ensure z is set
		for v in mol.vertices:
			if v.z is None:
				v.z = 0

		# when CXSMILES template was used, the template coords are the
		# final layout; skip collision/refinement/PCA which would distort it
		if getattr(self, 'template_used', False):
			return

		# Phase 3: collision resolution
		phase3_collisions.resolve_all_collisions(self)

		# Phase 4: force-field refinement
		phase4_refinement.force_refine(self)

		# Phase 5: PCA orientation (align major axis with x)
		helpers.canonicalize_orientation(self.mol)


#============================================
def calculate_coords(mol, bond_length: float = 1.0, force: int = 0) -> None:
	"""Module-level convenience function matching coords_generator signature."""
	g = CoordsGenerator2(bond_length=bond_length)
	g.calculate_coords(mol, bond_length=bond_length, force=force)
