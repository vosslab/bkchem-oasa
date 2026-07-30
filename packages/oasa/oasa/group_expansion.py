"""Pure planning for expanding one legacy CDML group into an OASA graph.

This module deliberately stops before document mutation.  A frontend command
can use the returned detached graph, placements, and rewires as one atomic
operation while retaining the original group if planning fails.
"""

# Standard Library
import copy
import dataclasses
import math
import re

# local repo modules
import oasa.linear_formula
import oasa.periodic_table


_CHAIN_FORMULA = re.compile(r"^[cC][0-9]*[hH][0-9]*$")
_SUPPORTED_TYPES = frozenset({"builtin", "implicit", "chain"})


#============================================
@dataclasses.dataclass(frozen=True)
class GroupAnchor:
	"""The removed group's stable identity and canvas coordinate."""

	group_id: str
	x: float
	y: float


#============================================
@dataclasses.dataclass(frozen=True)
class GroupAttachment:
	"""One exterior bond that a future command must reconnect."""

	bond_id: str
	exterior_atom_id: str
	bond_order: int
	attributes: tuple[tuple[str, str], ...] = ()


#============================================
@dataclasses.dataclass(frozen=True)
class TemplateResolution:
	"""A caller-supplied builtin template and its local attachment atom."""

	graph: object
	attachment_atom: object


#============================================
@dataclasses.dataclass(frozen=True)
class AtomPlacement:
	"""One deterministic local graph coordinate for a future command."""

	vertex_index: int
	x: float
	y: float


#============================================
@dataclasses.dataclass(frozen=True)
class AttachmentRewire:
	"""Intent to replace an old group endpoint with one planned graph atom."""

	bond_id: str
	exterior_atom_id: str
	replacement_vertex_index: int
	bond_order: int
	attributes: tuple[tuple[str, str], ...]


#============================================
@dataclasses.dataclass(frozen=True)
class GroupExpansionPlan:
	"""An immutable plan containing a detached graph and future mutations."""

	group_type: str
	group_name: str
	graph: object
	replacement_vertex_index: int
	placements: tuple[AtomPlacement, ...]
	rewires: tuple[AttachmentRewire, ...]


#============================================
def plan_group_expansion(
		group_type: str, group_name: str, formula: str | None,
		anchor: GroupAnchor, attachments: tuple[GroupAttachment, ...],
		molecule_factory: object, template_resolver: object | None = None,
		bond_length: float = 1.0,
		) -> GroupExpansionPlan:
	"""Plan a narrow, non-mutating expansion for one supported group.

	``molecule_factory`` is mandatory for newly parsed or chained graphs.
	Builtin expansion instead requires an injected ``template_resolver`` which
	accepts ``(group_name, anchor, attachments)`` and returns
	:class:`TemplateResolution`.  More than one exterior bond is ambiguous for
	the legacy group model and is therefore rejected before any graph work.
	"""
	_validate_request(group_type, group_name, anchor, attachments, bond_length)
	if group_type == "builtin":
		graph, replacement = _plan_builtin(
			group_name, anchor, attachments, template_resolver,
		)
	elif group_type == "implicit":
		graph, replacement = _plan_implicit(
			group_name, formula, attachments, molecule_factory,
		)
	else:
		graph, replacement = _plan_chain(formula, molecule_factory)
	replacement_index = graph.vertices.index(replacement)
	placements = _place_graph(graph, replacement_index, anchor, bond_length)
	rewires = _plan_rewires(attachments, replacement_index)
	plan = GroupExpansionPlan(
		group_type=group_type,
		group_name=group_name,
		graph=graph,
		replacement_vertex_index=replacement_index,
		placements=placements,
		rewires=rewires,
	)
	return plan


#============================================
def _validate_request(
		group_type: str, group_name: str, anchor: GroupAnchor,
		attachments: tuple[GroupAttachment, ...], bond_length: float,
		) -> None:
	"""Reject unsupported or ambiguous source data before graph allocation."""
	if group_type not in _SUPPORTED_TYPES:
		raise ValueError("unsupported group type: " + repr(group_type))
	if not group_name:
		raise ValueError("group name is required")
	if not anchor.group_id:
		raise ValueError("group anchor id is required")
	if not math.isfinite(anchor.x) or not math.isfinite(anchor.y):
		raise ValueError("group anchor coordinates must be finite")
	if not math.isfinite(bond_length) or bond_length <= 0:
		raise ValueError("bond length must be finite and positive")
	if len(attachments) > 1:
		raise ValueError("multiple group attachments are ambiguous")
	for attachment in attachments:
		if not attachment.bond_id or not attachment.exterior_atom_id:
			raise ValueError("attachment must identify its bond and exterior atom")
		if attachment.bond_order <= 0:
			raise ValueError("attachment bond order must be positive")


#============================================
def _plan_builtin(
		group_name: str, anchor: GroupAnchor,
		attachments: tuple[GroupAttachment, ...], template_resolver: object | None,
		) -> tuple[object, object]:
	"""Detach an injected builtin template without consulting frontend state."""
	if template_resolver is None:
		raise ValueError("builtin group expansion requires a template resolver")
	resolution = template_resolver(group_name, anchor, attachments)
	if not isinstance(resolution, TemplateResolution):
		raise TypeError("template resolver must return TemplateResolution")
	if resolution.attachment_atom not in resolution.graph.vertices:
		raise ValueError("template attachment atom is not in its graph")
	attachment_index = resolution.graph.vertices.index(resolution.attachment_atom)
	graph = copy.deepcopy(resolution.graph)
	replacement = graph.vertices[attachment_index]
	return graph, replacement


#============================================
def _plan_implicit(
		group_name: str, formula: str | None,
		attachments: tuple[GroupAttachment, ...], molecule_factory: object,
		) -> tuple[object, object]:
	"""Parse an implicit formula through the caller's explicit graph factory."""
	text = formula if formula is not None else group_name
	if not text:
		raise ValueError("implicit group formula is required")
	if molecule_factory is None:
		raise ValueError("implicit group expansion requires a molecule factory")
	occupied_valency = len(attachments)
	graph = molecule_factory()
	parsed = oasa.linear_formula.linear_formula(
		text,
		start_valency=occupied_valency,
		root_molecule=graph,
	)
	if parsed.molecule is None:
		raise ValueError("cannot parse implicit group formula: " + text)
	replacement = parsed.first_atom
	if replacement is None:
		replacement = parsed.molecule.vertices[0]
	return parsed.molecule, replacement


#============================================
def _plan_chain(formula: str | None, molecule_factory: object) -> tuple[object, object]:
	"""Build the legacy saturated alkyl-chain subset with an injected factory."""
	if formula is None or not _CHAIN_FORMULA.match(formula):
		raise ValueError("chain expansion requires a CnHm formula")
	if molecule_factory is None:
		raise ValueError("chain expansion requires a molecule factory")
	composition = oasa.periodic_table.formula_dict(formula.upper())
	if not composition.is_saturated_alkyl_chain():
		raise ValueError("chain formula is not a saturated alkyl chain")
	graph = molecule_factory()
	last_atom = None
	for _index in range(composition["C"]):
		atom = graph.create_vertex()
		atom.symbol = "C"
		graph.add_vertex(atom)
		if last_atom is not None:
			graph.add_edge(last_atom, atom)
		last_atom = atom
	replacement = graph.vertices[0]
	return graph, replacement


#============================================
def _place_graph(
		graph: object, replacement_index: int, anchor: GroupAnchor,
		bond_length: float,
		) -> tuple[AtomPlacement, ...]:
	"""Give every detached vertex a stable finite coordinate rooted at anchor."""
	placements: list[AtomPlacement] = []
	queue: list[tuple[int, int | None, int]] = [(replacement_index, None, 0)]
	seen: set[int] = set()
	while queue:
		vertex_index, parent_index, depth = queue.pop(0)
		if vertex_index in seen:
			continue
		seen.add(vertex_index)
		if parent_index is None:
			x, y = anchor.x, anchor.y
		else:
			parent = placements[parent_index]
			angle = (vertex_index + depth) * math.pi / 3
			x = parent.x + bond_length * math.cos(angle)
			y = parent.y + bond_length * math.sin(angle)
		placements.append(AtomPlacement(vertex_index, x, y))
		vertex = graph.vertices[vertex_index]
		for neighbor in vertex.neighbors:
			neighbor_index = graph.vertices.index(neighbor)
			if neighbor_index not in seen:
				queue.append((neighbor_index, len(placements) - 1, depth + 1))
	placements.sort(key=lambda placement: placement.vertex_index)
	for placement in placements:
		vertex = graph.vertices[placement.vertex_index]
		vertex.x = placement.x
		vertex.y = placement.y
	result = tuple(placements)
	return result


#============================================
def _plan_rewires(
		attachments: tuple[GroupAttachment, ...], replacement_index: int,
		) -> tuple[AttachmentRewire, ...]:
	"""Preserve exterior-bond intent for the later document command."""
	rewires = tuple(
		AttachmentRewire(
			bond_id=attachment.bond_id,
			exterior_atom_id=attachment.exterior_atom_id,
			replacement_vertex_index=replacement_index,
			bond_order=attachment.bond_order,
			attributes=attachment.attributes,
		)
		for attachment in attachments
	)
	return rewires
