# SPDX-License-Identifier: LGPL-3.0-or-later

"""Offline unit tests for the bounded PubChem HTTPS transport."""

# Standard Library
import io
import socket
import urllib.error
import unittest.mock

# Third Party
import pytest

# local repo modules
import oasa.pubchem
import oasa.pubchem_http


#============================================
class FakeResponse:
	"""Small context-managed HTTP response for injected-opener tests."""
	def __init__(self, url: str, body: bytes) -> None:
		self.url = url
		self.body = body

	def __enter__(self) -> "FakeResponse":
		return self

	def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
		return None

	def geturl(self) -> str:
		return self.url

	def read(self, amount: int = -1) -> bytes:
		if amount < 0:
			return self.body
		return self.body[:amount]


#============================================
def test_fetch_json_builds_an_approved_json_request() -> None:
	recorded_requests = []

	def opener(request: object, timeout: int) -> FakeResponse:
		recorded_requests.append((request, timeout))
		return FakeResponse(request.full_url, b'{"CID": 962}')

	payload = oasa.pubchem_http.fetch_json(
		"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
	)
	request, unused_timeout = recorded_requests[0]
	assert payload == {"CID": 962}
	assert all(label in request.get_header("User-agent") for label in ("BKChem", "OASA")) and request.get_header("Accept") == "application/json"


#============================================
def test_fetch_json_rejects_a_redirect_to_another_pug_path() -> None:
	def opener(request: object, timeout: int) -> FakeResponse:
		return FakeResponse("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/963/JSON", b"{}")

	with pytest.raises(oasa.pubchem.PubChemTransportError, match="redirected"):
		oasa.pubchem_http.fetch_json(
			"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
		)


#============================================
def test_fetch_json_rejects_an_oversized_response() -> None:
	def opener(request: object, timeout: int) -> FakeResponse:
		body = b"x" * (oasa.pubchem_http.MAX_RESPONSE_BYTES + 1)
		return FakeResponse(request.full_url, body)

	with pytest.raises(oasa.pubchem.PubChemTransportError, match="byte limit"):
		oasa.pubchem_http.fetch_json(
			"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
		)


#============================================
def test_fetch_json_maps_timeout_to_a_transport_error() -> None:
	def opener(request: object, timeout: int) -> object:
		raise socket.timeout("offline test timeout")

	with pytest.raises(oasa.pubchem.PubChemTransportError, match="timed out"):
		oasa.pubchem_http.fetch_json(
			"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
		)


#============================================
def test_fetch_json_maps_http_404_to_not_found() -> None:
	def opener(request: object, timeout: int) -> object:
		raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, io.BytesIO())

	with pytest.raises(oasa.pubchem.PubChemNotFoundError, match="404"):
		oasa.pubchem_http.fetch_json(
			"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
		)


#============================================
def test_default_opener_does_not_follow_a_malicious_redirect() -> None:
	opened_urls = []
	redirect_handler = None
	url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON"

	class FakeOpener:
		"""Simulate urllib returning a redirect status without opening Location."""
		def open(self, request: object, timeout: int) -> object:
			opened_urls.append(request.full_url)
			return redirect_handler.redirect_request(
				request, io.BytesIO(), 302, "redirect", {"Location": "https://evil.invalid/"}, "https://evil.invalid/"
			)

	def build_opener(handler: object) -> FakeOpener:
		nonlocal redirect_handler
		redirect_handler = handler
		return FakeOpener()

	with unittest.mock.patch.object(oasa.pubchem_http.urllib.request, "build_opener", build_opener):
		with pytest.raises(oasa.pubchem.PubChemTransportError, match="302"):
			oasa.pubchem_http.fetch_json(url)
	assert opened_urls == [url]


#============================================
@pytest.mark.parametrize("suffix", ["../cid/962/JSON", "%2e%2e%2fother", "%252e%252e%252fother"])
def test_fetch_json_rejects_dot_segment_traversal(suffix: str) -> None:
	url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{suffix}"
	with pytest.raises(oasa.pubchem.PubChemTransportError, match="approved"):
		oasa.pubchem_http.fetch_json(url)


#============================================
def test_fetch_json_maps_a_malformed_injected_response() -> None:
	def opener(request: object, timeout: int) -> object:
		return object()

	with pytest.raises(oasa.pubchem.PubChemTransportError, match="malformed"):
		oasa.pubchem_http.fetch_json(
			"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON", opener
		)


#============================================
def test_fetch_json_maps_a_malformed_url_to_a_transport_error() -> None:
	with pytest.raises(oasa.pubchem.PubChemTransportError, match="malformed"):
		oasa.pubchem_http.fetch_json("https://[::1/rest/pug/compound/cid/962/JSON")
