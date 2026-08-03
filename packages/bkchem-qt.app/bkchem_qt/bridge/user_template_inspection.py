"""Qt-free bridge for OASA saved user-template admission."""

# local repo modules
import oasa.cdml_document


class UserTemplateInspectionError(ValueError):
	"""Raised when OASA rejects one serialized user template."""


#============================================
def inspect_user_template_display_name(template_cdml: str) -> str | None:
	"""Return OASA's optional display name for one eligible template.

	Args:
		template_cdml: Exact complete CDML text saved in one user template.

	Returns:
		A stripped nonblank molecule name, or ``None`` when it is absent.

	Raises:
		UserTemplateInspectionError: If OASA rejects the template CDML.
	"""
	try:
		inspection = oasa.cdml_document.inspect_user_template(template_cdml)
	except oasa.cdml_document.CDMLDocumentError as error:
		raise UserTemplateInspectionError(str(error)) from error
	return inspection.display_name
