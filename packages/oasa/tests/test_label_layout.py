"""Behavior tests for bounded generic label placement."""

# local repo modules
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.label_geometry import label_attach_contract_from_text_origin
from oasa.render_lib.label_layout import LabelPlacementCandidate
from oasa.render_lib.label_layout import choose_label_placement
from oasa.render_lib.label_layout import label_target_overlap_score


#============================================
def _candidate(
		key: tuple[int, int, int],
		origin: tuple[float, float]) -> LabelPlacementCandidate:
	"""Build one ordinary, non-Haworth label-placement candidate."""
	contract = label_attach_contract_from_text_origin(
		text_x=origin[0],
		text_y=origin[1],
		text="Cl",
		anchor="start",
		font_size=12.0,
	)
	return LabelPlacementCandidate(
		text="Cl",
		anchor="start",
		font_scale=1.0,
		nominal_origin=origin,
		connector_start=(0.0, 0.0),
		attach_contract=contract,
		constraints=AttachConstraints(target_gap=1.5),
		candidate_key=key,
		font_size=12.0,
	)


#============================================
def test_label_chooser_is_order_independent_for_equal_candidates() -> None:
	"""Stable candidate keys, rather than caller ordering, choose a tie."""
	first = _candidate((4, 0, 0), (20.0, 0.0))
	second = _candidate((2, 0, 0), (20.0, 0.0))
	forward = choose_label_placement((first, second))
	reversed_result = choose_label_placement((second, first))
	assert forward.candidate_key == reversed_result.candidate_key


#============================================
def test_label_chooser_avoids_an_occupied_lane() -> None:
	"""A blocked ordinary label lane yields to an unblocked alternative."""
	blocked = _candidate((0, 0, 0), (18.0, 0.0))
	clear = _candidate((1, 0, 0), (18.0, 20.0))
	result = choose_label_placement(
		candidates=(blocked, clear),
		occupied_targets=(make_box_target((14.0, -8.0, 36.0, 8.0)),),
	)
	assert result.candidate_key == clear.candidate_key


#============================================
def test_label_chooser_avoids_a_blocked_polygon() -> None:
	"""A generic polygon removes an otherwise convenient label lane."""
	blocked = _candidate((0, 0, 0), (18.0, 0.0))
	clear = _candidate((1, 0, 0), (18.0, 20.0))
	result = choose_label_placement(
		candidates=(blocked, clear),
		blocked_polygons=(((10.0, -10.0), (40.0, -10.0), (40.0, 10.0), (10.0, 10.0)),),
	)
	assert result.candidate_key == clear.candidate_key


#============================================
def test_label_target_overlap_score_is_geometry_only() -> None:
	"""The reusable overlap score accepts ordinary target facts, not labels."""
	first = make_box_target((0.0, 0.0, 10.0, 10.0))
	second = make_box_target((5.0, 0.0, 15.0, 10.0))
	assert label_target_overlap_score((first, second)) == 50.0
