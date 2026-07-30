"""Stable CDML fragment metadata owned by the Qt document model."""

# Standard Library
import dataclasses


#============================================
@dataclasses.dataclass(frozen=True)
class FragmentProperty:
	"""One uninterpreted legacy ``<property>`` child of a CDML fragment.

	The old Tk frontend evaluated the ``type`` attribute.  The Qt frontend
	intentionally retains it as XML metadata until it has a safe, explicit
	property model for the particular fragment type.
	"""

	name: str
	value: str
	type_name: str
	attributes: tuple[tuple[str, str], ...] = ()
	raw_xml: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class FragmentModel:
	"""An immutable CDML fragment addressed only by stable atom and bond IDs."""

	fragment_id: str
	fragment_type: str
	name: str
	atom_ids: tuple[str, ...]
	bond_ids: tuple[str, ...]
	properties: tuple[FragmentProperty, ...] = ()
	attributes: tuple[tuple[str, str], ...] = ()
	unknown_children_xml: tuple[str, ...] = ()
	raw_xml: str | None = None
