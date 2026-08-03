"""Focused contracts for the pure OASA group-expansion planner."""

# Standard Library
import math

# local repo modules
import pytest

import oasa.group_expansion
import oasa.molecule_lib
import oasa.oasa_config


#============================================
class _InjectedMolecule(oasa.molecule_lib.Molecule):
	"""A caller-selected graph family for factory-bound planning tests."""


#============================================
def _unexpected_molecule() -> object:
	"""Fail when a planner path falls back to the deprecated global factory."""
	msg = "Config.molecule_class should not be used"
	raise RuntimeError(msg)


#============================================
def _anchor() -> oasa.group_expansion.GroupAnchor:
	"""Create a stable group location used by the small planner tests."""
	anchor = oasa.group_expansion.GroupAnchor("group-1", 12.5, -4.0)
	return anchor


#============================================
def test_implicit_group_uses_explicit_factory_with_poisoned_config(
		monkeypatch: object,
		) -> None:
	"""Formula expansion remains in the caller's graph family."""
	monkeypatch.setattr(oasa.oasa_config.Config, "molecule_class", _unexpected_molecule)
	plan = oasa.group_expansion.plan_group_expansion(
		"implicit", "methanol", "CH3OH", _anchor(), (), _InjectedMolecule,
	)
	assert isinstance(plan.graph, _InjectedMolecule)


#============================================
def test_chain_plan_places_a_finite_replacement_at_its_anchor() -> None:
	"""A saturated chain gets usable, rooted coordinates before Qt owns it."""
	plan = oasa.group_expansion.plan_group_expansion(
		"chain", "ethyl", "C2H5", _anchor(), (), _InjectedMolecule,
	)
	replacement = plan.placements[plan.replacement_vertex_index]
	finite = all(math.isfinite(value) for placement in plan.placements
				for value in (placement.x, placement.y))
	assert finite and (replacement.x, replacement.y) == (12.5, -4.0)


#============================================
def test_builtin_plan_detaches_the_injected_template() -> None:
	"""Builtin planning copies caller template data rather than retaining it."""
	template = _InjectedMolecule()
	atom = template.create_vertex()
	atom.symbol = "C"
	template.add_vertex(atom)

	def resolve(
			_name: str, _anchor: object, _attachments: object,
			) -> oasa.group_expansion.TemplateResolution:
		"""Supply a small template without frontend or global state."""
		resolution = oasa.group_expansion.TemplateResolution(template, atom)
		return resolution

	plan = oasa.group_expansion.plan_group_expansion(
		"builtin", "Me", None, _anchor(), (), _InjectedMolecule, resolve,
	)
	assert plan.graph is not template


#============================================
def test_unsupported_group_does_not_call_the_factory() -> None:
	"""Rejected types fail before they could allocate or mutate a replacement."""
	calls: list[str] = []

	def make_graph() -> _InjectedMolecule:
		"""Record allocations that unsupported input must not trigger."""
		calls.append("called")
		graph = _InjectedMolecule()
		return graph

	with pytest.raises(ValueError, match="unsupported group type"):
		oasa.group_expansion.plan_group_expansion(
			"explicit", "R", None, _anchor(), (), make_graph,
		)
	assert not calls


#============================================
def test_attachment_rewire_is_deterministic() -> None:
	"""A future atomic command receives stable exterior-bond replacement intent."""
	attachment = oasa.group_expansion.GroupAttachment(
		"bond-4", "atom-9", 1, (("type", "n"),),
	)
	first = oasa.group_expansion.plan_group_expansion(
		"chain", "methyl", "CH3", _anchor(), (attachment,), _InjectedMolecule,
	)
	second = oasa.group_expansion.plan_group_expansion(
		"chain", "methyl", "CH3", _anchor(), (attachment,), _InjectedMolecule,
	)
	assert first.rewires == second.rewires


#============================================
def test_implicit_group_uses_end_valency_when_start_valency_is_unavailable() -> None:
	"""A directional formula retains its valid attachment endpoint."""
	plan = oasa.group_expansion.plan_group_expansion(
		"implicit", "H3CO", None, _anchor(),
		(oasa.group_expansion.GroupAttachment("b1", "a1", 1),),
		_InjectedMolecule,
	)
	assert plan.graph.vertices[plan.replacement_vertex_index].symbol == "C"
