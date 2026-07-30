# SPDX-License-Identifier: LGPL-3.0-or-later

"""Small, explicit HTTPS transport for caller-initiated PubChem PUG requests."""

# Standard Library
import collections.abc
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

# local repo modules
import oasa.pubchem


PUBCHEM_HOST = "pubchem.ncbi.nlm.nih.gov"
PUG_PATH_PREFIX = "/rest/pug/"
REQUEST_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "BKChem-OASA PubChem transport"


#============================================
class _RejectRedirects(urllib.request.HTTPRedirectHandler):
	"""Prevent urllib from contacting a redirect destination automatically."""
	def redirect_request(
		self,
		req: urllib.request.Request,
		fp: object,
		code: int,
		msg: str,
		headers: object,
		newurl: str,
	) -> urllib.request.Request:
		"""Reject every redirect before urllib can open its Location URL."""
		raise urllib.error.HTTPError(req.full_url, code, "PubChem redirect refused", headers, fp)


#============================================
def _open_without_redirects(request: urllib.request.Request, timeout: int) -> object:
	"""Open only the original approved URL and turn redirects into HTTP errors."""
	opener = urllib.request.build_opener(_RejectRedirects())
	response = opener.open(request, timeout=timeout)
	return response


#============================================
def fetch_json(
	url: str,
	opener: collections.abc.Callable[..., object] | None = None,
) -> dict:
	"""Fetch one approved PUG REST JSON object through an injectable opener.

	The caller chooses when to make a request. This helper accepts only the
	canonical PubChem HTTPS PUG path and rejects every redirect before it can
	be followed. An injected opener must accept a ``Request`` plus ``timeout``
	and return a context-managed response with ``geturl()`` and ``read(size)``.
	"""
	_validated_url(url)
	if opener is not None and not callable(opener):
		raise oasa.pubchem.PubChemTransportError("PubChem opener must be callable")
	request = urllib.request.Request(
		url,
		headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
	)
	open_request = _open_without_redirects if opener is None else opener
	try:
		response = open_request(request, timeout=REQUEST_TIMEOUT_SECONDS)
		with response:
			final_url = response.geturl()
			_validated_url(final_url)
			if final_url != url:
				raise oasa.pubchem.PubChemTransportError("PubChem HTTPS request redirected to another path")
			body = response.read(MAX_RESPONSE_BYTES + 1)
	except urllib.error.HTTPError as exc:
		exc.close()
		if exc.code == 404:
			raise oasa.pubchem.PubChemNotFoundError("PubChem returned HTTP 404") from exc
		message = f"PubChem HTTP request failed with status {exc.code}"
		raise oasa.pubchem.PubChemTransportError(message) from exc
	except urllib.error.URLError as exc:
		if isinstance(exc.reason, TimeoutError):
			raise oasa.pubchem.PubChemTransportError("PubChem HTTPS request timed out") from exc
		raise oasa.pubchem.PubChemTransportError(f"PubChem HTTPS request failed: {exc.reason}") from exc
	except (TimeoutError, socket.timeout) as exc:
		raise oasa.pubchem.PubChemTransportError("PubChem HTTPS request timed out") from exc
	except OSError as exc:
		raise oasa.pubchem.PubChemTransportError(f"PubChem HTTPS request failed: {exc}") from exc
	except (AttributeError, TypeError) as exc:
		raise oasa.pubchem.PubChemTransportError("PubChem opener returned a malformed response") from exc
	if not isinstance(body, bytes):
		raise oasa.pubchem.PubChemTransportError("PubChem HTTPS response was not bytes")
	if len(body) > MAX_RESPONSE_BYTES:
		raise oasa.pubchem.PubChemTransportError("PubChem HTTPS response exceeded byte limit")
	try:
		text = body.decode("utf-8")
		payload = json.loads(text)
	except (UnicodeDecodeError, json.JSONDecodeError) as exc:
		raise oasa.pubchem.PubChemTransportError("PubChem HTTPS response was not UTF-8 JSON") from exc
	if not isinstance(payload, dict):
		raise oasa.pubchem.PubChemTransportError("PubChem HTTPS JSON root was not an object")
	return payload


#============================================
def _validated_url(url: str) -> None:
	"""Reject URLs outside the canonical PubChem PUG HTTPS endpoint."""
	if not isinstance(url, str):
		raise oasa.pubchem.PubChemTransportError("PubChem URL must be text")
	try:
		parsed = urllib.parse.urlsplit(url)
	except ValueError as exc:
		raise oasa.pubchem.PubChemTransportError("PubChem URL was malformed") from exc
	decoded_path = _decoded_path(parsed.path)
	path_segments = decoded_path.replace("\\", "/").split("/")
	has_traversal = any(segment in (".", "..") for segment in path_segments)
	is_allowed = (
		parsed.scheme == "https"
		and parsed.netloc == PUBCHEM_HOST
		and parsed.path.startswith(PUG_PATH_PREFIX)
		and len(parsed.path) > len(PUG_PATH_PREFIX)
		and not parsed.query
		and not parsed.fragment
		and not has_traversal
	)
	if not is_allowed:
		raise oasa.pubchem.PubChemTransportError("PubChem URL is outside the approved HTTPS PUG endpoint")


#============================================
def _decoded_path(path: str) -> str:
	"""Decode nested percent escapes before looking for structural traversal."""
	decoded = path
	while True:
		new_decoded = urllib.parse.unquote(decoded)
		if new_decoded == decoded:
			break
		decoded = new_decoded
	return decoded
