"""Plain detached-graph placement for backend molecule insertion proposals."""

# Standard Library
import decimal
import math


#============================================
def _finite_builtin_float(value: object, message: str) -> float:
	"""Normalize one exact built-in finite number at the public boundary."""
	if type(value) not in (int, float):
		raise ValueError(message)
	try:
		plain_value = float(value)
	except OverflowError:
		raise ValueError(message) from None
	if not math.isfinite(plain_value):
		raise ValueError(message)
	return plain_value


#============================================
def _finite_mean(values: list[float], message: str) -> float:
	"""Return a finite mean without overflowing or underflowing its sum."""
	maximum = max(abs(value) for value in values)
	if maximum == 0.0:
		return 0.0
	mean = maximum * (math.fsum(value / maximum for value in values) / len(values))
	if not math.isfinite(mean):
		raise ValueError(message)
	return mean


#============================================
def validate_insertion_placement(
		target_mean_bond_length: object, anchor: object,
		) -> tuple[float, tuple[float, float]]:
	"""Return finite built-in placement data suitable for a worker boundary."""
	if type(anchor) is not tuple or len(anchor) != 2:
		raise ValueError("Insertion anchor must be a finite scene-point pair")
	anchor_x, anchor_y = anchor
	target = _finite_builtin_float(
		target_mean_bond_length, "Insertion bond length must be a finite positive number",
	)
	plain_anchor = (
		_finite_builtin_float(anchor_x, "Insertion anchor must be a finite scene-point pair"),
		_finite_builtin_float(anchor_y, "Insertion anchor must be a finite scene-point pair"),
	)
	if target <= 0.0:
		raise ValueError("Insertion bond length must be a finite positive number")
	return target, plain_anchor


#============================================
def place_molecules_for_insertion(
		molecules: object, target_mean_bond_length: object, anchor: object,
		) -> None:
	"""Scale real bonds collectively and center detached atoms at ``anchor``.

	The inputs intentionally contain no frontend objects.  Bond-free proposals
	are valid: their existing atom centroid is translated without fabricating
	chemistry or requiring a scale measurement.
	"""
	target, (anchor_x, anchor_y) = validate_insertion_placement(
		target_mean_bond_length, anchor,
	)
	molecule_list = list(molecules)
	atoms = [atom for molecule in molecule_list for atom in molecule.vertices]
	if not atoms:
		raise ValueError("Insertion proposal requires at least one positioned atom")
	atom_coordinates = []
	coordinates_by_identity = {}
	for atom in atoms:
		try:
			atom_x = _finite_builtin_float(
				atom.x, "Insertion proposal has non-finite atom coordinates",
			)
			atom_y = _finite_builtin_float(
				atom.y, "Insertion proposal has non-finite atom coordinates",
			)
		except ValueError:
			if type(atom.x) not in (int, float) or type(atom.y) not in (int, float):
				raise ValueError("Insertion proposal has incomplete atom coordinates") from None
			raise
		atom_coordinates.append((atom, atom_x, atom_y))
		coordinates_by_identity[id(atom)] = (atom_x, atom_y)
	bond_lengths = []
	for molecule in molecule_list:
		for bond in molecule.edges:
			atom_one, atom_two = bond.vertices
			atom_one_x, atom_one_y = coordinates_by_identity[id(atom_one)]
			atom_two_x, atom_two_y = coordinates_by_identity[id(atom_two)]
			delta_x = atom_one_x - atom_two_x
			delta_y = atom_one_y - atom_two_y
			length = math.hypot(delta_x, delta_y)
			if not math.isfinite(length) or length <= 0.0:
				raise ValueError("Insertion proposal has an invalid bond length")
			bond_lengths.append(length)
	centroid_x = _finite_mean(
		[atom_x for _atom, atom_x, _atom_y in atom_coordinates],
		"Insertion proposal has non-finite atom coordinates",
	)
	centroid_y = _finite_mean(
		[atom_y for _atom, _atom_x, atom_y in atom_coordinates],
		"Insertion proposal has non-finite atom coordinates",
	)
	mean_bond_length = (
		_finite_mean(bond_lengths, "Insertion proposal has an invalid bond length")
		if bond_lengths else None
	)
	if mean_bond_length is not None and mean_bond_length <= 0.0:
		raise ValueError("Insertion proposal has an invalid bond length")
	scale = 1.0 if mean_bond_length is None else target / mean_bond_length
	if not math.isfinite(scale) or scale <= 0.0:
		raise ValueError("Insertion proposal has an invalid bond length")

	# Decimal intermediates preserve an affine difference when finite floats
	# have extreme, opposing magnitudes that would overflow before scaling.
	with decimal.localcontext() as context:
		context.prec = 64
		decimal_scale = decimal.Decimal.from_float(scale)
		decimal_centroid_x = decimal.Decimal.from_float(centroid_x)
		decimal_centroid_y = decimal.Decimal.from_float(centroid_y)
		decimal_anchor_x = decimal.Decimal.from_float(anchor_x)
		decimal_anchor_y = decimal.Decimal.from_float(anchor_y)
		placed_coordinates = []
		for atom, atom_x, atom_y in atom_coordinates:
			try:
				placed_x = float(
					(decimal.Decimal.from_float(atom_x) - decimal_centroid_x)
					* decimal_scale + decimal_anchor_x
				)
				placed_y = float(
					(decimal.Decimal.from_float(atom_y) - decimal_centroid_y)
					* decimal_scale + decimal_anchor_y
				)
			except OverflowError:
				raise ValueError("Insertion proposal has non-finite atom coordinates") from None
			if not math.isfinite(placed_x) or not math.isfinite(placed_y):
				raise ValueError("Insertion proposal has non-finite atom coordinates")
			placed_coordinates.append((atom, placed_x, placed_y))
	for atom, placed_x, placed_y in placed_coordinates:
		atom.x = placed_x
		atom.y = placed_y
