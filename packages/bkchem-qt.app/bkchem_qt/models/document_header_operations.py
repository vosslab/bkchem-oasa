"""Plain adapters for backend-owned CDML paper and drawing-standard operations."""

# local repo modules
import oasa.cdml_document
import oasa.cdml_standard


#============================================
def prepare_paper_properties(
		snapshot: object, request: object, prepared_type: object,
		) -> object:
	"""Bind explicit paper intent to OASA's revision-bound patch grammar."""
	if request.target_keys:
		raise ValueError("Paper properties does not accept persistent targets")
	payload = dict(request.payload)
	if set(payload) != {"expected_revision", "changes"}:
		raise ValueError("Paper properties payload has unsupported fields")
	expected_revision = payload["expected_revision"]
	if type(expected_revision) is not int:
		raise ValueError("Paper properties expected_revision must be an integer")
	if expected_revision != snapshot.revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Paper properties expected revision does not match the current snapshot",
		)
	changes = payload["changes"]
	if type(changes) is not tuple:
		raise ValueError("Paper properties changes must be an immutable tuple")
	patch = oasa.cdml_document.CDMLPaperPropertiesPatch(expected_revision, changes)
	return prepared_type("paper-properties-patch", expected_revision, patch)


#============================================
def commit_paper_properties(backend: object, prepared: object) -> object:
	"""Submit one prepared paper patch to the backend authority."""
	if type(prepared.value) is not oasa.cdml_document.CDMLPaperPropertiesPatch:
		raise ValueError("Paper properties requires a paper properties patch")
	return backend.patch_paper_properties(prepared.value)


#============================================
def prepare_drawing_standard(
		snapshot: object, request: object, prepared_type: object,
		) -> object:
	"""Bind standard and override intent to OASA's revision-bound grammar."""
	payload = dict(request.payload)
	if set(payload) != {
			"expected_revision", "changes", "apply_scope", "root_ids", "override_fields",
		}:
		raise ValueError("Drawing standard payload has unsupported fields")
	expected_revision = payload["expected_revision"]
	if type(expected_revision) is not int:
		raise ValueError("Drawing standard expected_revision must be an integer")
	if expected_revision != snapshot.revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Drawing standard expected revision does not match the current snapshot",
		)
	changes = payload["changes"]
	if type(changes) is not tuple:
		raise ValueError("Drawing standard changes must be an immutable tuple")
	apply_scope = payload["apply_scope"]
	root_ids = payload["root_ids"]
	override_fields = payload["override_fields"]
	if type(root_ids) is not tuple or type(override_fields) is not tuple:
		raise ValueError("Drawing standard roots and override fields must be immutable tuples")
	if apply_scope == "selected":
		if (
				len(request.target_keys) != len(root_ids)
				or {identifier for _kind, identifier in request.target_keys} != set(root_ids)
				or any(kind not in {"molecule", "presentation"} for kind, _identifier in request.target_keys)
			):
			raise ValueError("Drawing standard target keys must match selected roots")
	elif request.target_keys:
		raise ValueError("Only selected drawing-standard scope accepts persistent targets")
	application = oasa.cdml_standard.CDMLDrawingStandardApplication(
		expected_revision, changes, apply_scope, root_ids, override_fields,
	)
	return prepared_type(
		"drawing-standard-patch", expected_revision, application,
		preserve_existing_selection=True,
	)


#============================================
def commit_drawing_standard(backend: object, prepared: object) -> object:
	"""Submit one prepared drawing-standard patch to the backend authority."""
	if type(prepared.value) is not oasa.cdml_standard.CDMLDrawingStandardApplication:
		raise ValueError("Drawing standard requires an exact application request")
	return backend.patch_drawing_standard(prepared.value)
