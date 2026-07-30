#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Download Haworth-style images from User:NEUROtiker gallery archive pages."""

# Standard Library
import argparse
import html.parser
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_URL = "https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive1"
ARCHIVE_URL_2 = "https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive2"
ARCHIVE_URL_3 = "https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive3"
ARCHIVE_URL_4 = "https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive4"
DEFAULT_ARCHIVE_URLS = [ARCHIVE_URL, ARCHIVE_URL_2, ARCHIVE_URL_3, ARCHIVE_URL_4]
API_URL = "https://commons.wikimedia.org/w/api.php"
ALLOWED_HOSTS = {"commons.wikimedia.org", "upload.wikimedia.org"}
ALLOWED_ARCHIVE_PATH_RE = re.compile(r"^/wiki/User:NEUROtiker/gallery/archive\d+$")
KEYWORD_TERMS = ("haworth", "pyranose", "furanose")
MAX_RETRIES = 6
DELAY_BASE = 1.0


#============================================
class AnchorCollector(html.parser.HTMLParser):
	"""Collect anchor tags with href/title/text content."""

	def __init__(self) -> None:
		super().__init__()
		self.anchors = []
		self._current_href = ""
		self._current_title = ""
		self._current_text = []
		self._in_anchor = False

	def handle_starttag(self, tag: object, attrs: object) -> None:
		if tag.lower() != "a":
			return
		attr_map = dict(attrs)
		self._current_href = attr_map.get("href", "")
		self._current_title = attr_map.get("title", "")
		self._current_text = []
		self._in_anchor = True

	def handle_data(self, data: object) -> None:
		if self._in_anchor:
			self._current_text.append(data)

	def handle_endtag(self, tag: object) -> None:
		if tag.lower() != "a" or not self._in_anchor:
			return
		self.anchors.append(
			{
				"href": self._current_href,
				"title": self._current_title,
				"text": "".join(self._current_text).strip(),
			}
		)
		self._current_href = ""
		self._current_title = ""
		self._current_text = []
		self._in_anchor = False


#============================================
def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Download Haworth-like files from User:NEUROtiker archive pages."
	)
	parser.add_argument(
		"archive_urls",
		nargs="*",
		help=(
			"Optional archive URLs. Defaults to archive1, archive2, archive3, and archive4 if omitted."
		),
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=0,
		help="Optional limit on number of files to download (0 = no limit).",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		default=False,
		help="Resolve file list and manifest without downloading file bytes.",
	)
	return parser.parse_args()


#============================================
def _validate_url(url: object, allowed_hosts: object, allowed_path_prefix: object=None) -> object:
	"""Validate URL scheme/host and optional path prefix."""
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https"):
		raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
	host = parsed.netloc.lower()
	if host not in allowed_hosts:
		raise ValueError(f"Unsupported URL host: {parsed.netloc}")
	if allowed_path_prefix:
		if not parsed.path.startswith(allowed_path_prefix):
			raise ValueError(f"Unsupported URL path: {parsed.path}")


#============================================
def _validate_archive_url(url: object) -> object:
	"""Validate archive URL points to User:NEUROtiker gallery archive# page."""
	_validate_url(url, {"commons.wikimedia.org"})
	parsed = urllib.parse.urlparse(url)
	path = parsed.path.rstrip("/")
	if not ALLOWED_ARCHIVE_PATH_RE.fullmatch(path):
		raise ValueError(
			"Archive URL must match /wiki/User:NEUROtiker/gallery/archive#: "
			f"got {parsed.path}"
		)


#============================================
def _archive_raw_url(archive_url: object) -> object:
	"""Build MediaWiki raw-content URL from archive page URL."""
	parsed = urllib.parse.urlparse(archive_url)
	title = ""
	if parsed.path.startswith("/wiki/"):
		title = parsed.path[len("/wiki/"):]
	elif parsed.path.rstrip("/") == "/w/index.php":
		query_map = urllib.parse.parse_qs(parsed.query)
		title_values = query_map.get("title", [])
		if title_values:
			title = title_values[0]
	else:
		title = parsed.path.lstrip("/")
	if not title:
		raise ValueError(f"Could not derive MediaWiki title from URL: {archive_url}")
	query = urllib.parse.urlencode({"title": title, "action": "raw"})
	return f"https://commons.wikimedia.org/w/index.php?{query}"


#============================================
def _sleep_between_requests(delay_base: object) -> None:
	"""Sleep before each request with random jitter."""
	time.sleep(delay_base + random.random())


#============================================
def _retry_wait_seconds(http_error: object, attempt: object, delay_base: object) -> object:
	"""Compute wait seconds for transient retry attempts."""
	retry_after = http_error.headers.get("Retry-After", "").strip()
	if retry_after.isdigit():
		return max(float(retry_after), delay_base + random.random())
	return max(delay_base + random.random(), float((attempt + 1) * 2))


#============================================
def _urlopen_with_retries(request: object, timeout: object, max_retries: object, delay_base: object) -> object:
	"""Open URL with polite delay and retry on transient errors."""
	attempt = 0
	while True:
		_sleep_between_requests(delay_base)
		try:
			with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - scheme/host validated
				return response.read()
		except urllib.error.HTTPError as error:
			transient = error.code in (429, 500, 502, 503, 504)
			if transient and attempt < max_retries:
				time.sleep(_retry_wait_seconds(error, attempt, delay_base))
				attempt += 1
				continue
			raise
		except urllib.error.URLError:
			if attempt < max_retries:
				time.sleep(max(delay_base + random.random(), float((attempt + 1) * 2)))
				attempt += 1
				continue
			raise


#============================================
def fetch_text(url: object, max_retries: object, delay_base: object) -> object:
	"""Download UTF-8 text from a validated URL."""
	_validate_url(url, {"commons.wikimedia.org"})
	request = urllib.request.Request(
		url,
		headers={"User-Agent": "bkchem-neurotiker-haworth-fetch/1.0"},
	)
	content = _urlopen_with_retries(
		request=request,
		timeout=30,
		max_retries=max_retries,
		delay_base=delay_base,
	)
	return content.decode("utf-8", errors="replace")


#============================================
def fetch_json(url: object, max_retries: object, delay_base: object) -> object:
	"""Download JSON from a validated URL."""
	_validate_url(url, {"commons.wikimedia.org"})
	request = urllib.request.Request(
		url,
		headers={"User-Agent": "bkchem-neurotiker-haworth-fetch/1.0"},
	)
	content = _urlopen_with_retries(
		request=request,
		timeout=30,
		max_retries=max_retries,
		delay_base=delay_base,
	)
	payload = content.decode("utf-8", errors="replace")
	return json.loads(payload)


#============================================
def download_binary(url: object, max_retries: object, delay_base: object) -> object:
	"""Download binary content from upload.wikimedia/commons.wikimedia."""
	_validate_url(url, ALLOWED_HOSTS)
	request = urllib.request.Request(
		url,
		headers={"User-Agent": "bkchem-neurotiker-haworth-fetch/1.0"},
	)
	return _urlopen_with_retries(
		request=request,
		timeout=60,
		max_retries=max_retries,
		delay_base=delay_base,
	)


#============================================
def _dedupe_preserve_order(values: object) -> object:
	"""Return unique values preserving first-seen order."""
	seen = set()
	ordered = []
	for value in values:
		if value in seen:
			continue
		seen.add(value)
		ordered.append(value)
	return ordered


#============================================
def _normalize_file_title(text: object) -> object:
	"""Normalize File: title to MediaWiki-style title with spaces."""
	title = text.strip().replace("_", " ")
	if not title.lower().startswith("file:"):
		title = "File:" + title.split(":", 1)[-1]
	return "File:" + title.split(":", 1)[1]


#============================================
def _line_matches_terms(text: object, terms: object) -> bool:
	"""Return True if line/corpus contains any configured search term."""
	if not terms:
		return True
	lower_text = text.lower()
	for term in terms:
		if term in lower_text:
			return True
	return False


#============================================
def find_haworth_file_titles_from_wikitext(archive_wikitext: object, keyword_terms: object) -> object:
	"""Extract File: titles from archive wikitext line/caption keyword matches."""
	matches = []
	for line in archive_wikitext.splitlines():
		if "File:" not in line and "file:" not in line:
			continue
		match = re.search(r"(?i)file:[^|\]\n]+", line)
		if not match:
			continue
		title = _normalize_file_title(match.group(0))
		if not _line_matches_terms(line, keyword_terms):
			continue
		matches.append(title)
	return _dedupe_preserve_order(matches)


#============================================
def find_haworth_file_titles_from_html(archive_html: object, keyword_terms: object) -> object:
	"""Extract unique File: titles matching keyword from archive HTML anchors."""
	collector = AnchorCollector()
	collector.feed(archive_html)
	matches = []
	for anchor in collector.anchors:
		href = anchor["href"] or ""
		if not href.startswith("/wiki/File:"):
			continue
		parsed = urllib.parse.urlparse(href)
		path = parsed.path
		title = urllib.parse.unquote(path[len("/wiki/"):])
		corpus = " ".join([href, anchor["title"], anchor["text"], title]).lower()
		if not _line_matches_terms(corpus, keyword_terms):
			continue
		matches.append(_normalize_file_title(title))
	return _dedupe_preserve_order(matches)


#============================================
def chunked(items: object, chunk_size: object) -> object:
	"""Yield fixed-size chunks from a list."""
	for index in range(0, len(items), chunk_size):
		yield items[index:index + chunk_size]


#============================================
def resolve_imageinfo(file_titles: object, max_retries: object, delay_base: object) -> object:
	"""Resolve original file URLs and metadata for file titles via MediaWiki API."""
	resolved = []
	for title_chunk in chunked(file_titles, 50):
		params = {
			"action": "query",
			"format": "json",
			"prop": "imageinfo",
			"iiprop": "url|size|sha1|mime",
			"titles": "|".join(title_chunk),
		}
		api_url = API_URL + "?" + urllib.parse.urlencode(params)
		data = fetch_json(
			api_url,
			max_retries=max_retries,
			delay_base=delay_base,
		)
		pages = data.get("query", {}).get("pages", {})
		for page in pages.values():
			title = page.get("title", "")
			if not title.startswith("File:"):
				continue
			imageinfo = page.get("imageinfo", [])
			if not imageinfo:
				continue
			info = imageinfo[0]
			file_page = (
				"https://commons.wikimedia.org/wiki/"
				+ urllib.parse.quote(title.replace(" ", "_"))
			)
			resolved.append(
				{
					"title": title,
					"file_page": file_page,
					"url": info.get("url", ""),
					"sha1": info.get("sha1", ""),
					"size": info.get("size", 0),
					"mime": info.get("mime", ""),
				}
			)
	return sorted(resolved, key=lambda item: item["title"].lower())


#============================================
def filename_from_url(url: object) -> object:
	"""Get decoded basename from file URL path."""
	parsed = urllib.parse.urlparse(url)
	return urllib.parse.unquote(os.path.basename(parsed.path))


#============================================
def ensure_dir(path: object) -> None:
	"""Create directory if needed."""
	os.makedirs(path, exist_ok=True)


#============================================
def write_manifest(manifest_path: object, payload: object) -> None:
	"""Write manifest JSON with deterministic formatting."""
	with open(manifest_path, "w", encoding="utf-8") as handle:
		json.dump(payload, handle, indent=2, sort_keys=True)
		handle.write("\n")


#============================================
def run() -> None:
	"""Run archive scan and optional download for default archives or inputs."""
	args = parse_args()
	archive_urls = args.archive_urls
	if not archive_urls:
		archive_urls = list(DEFAULT_ARCHIVE_URLS)
	keyword_terms = list(KEYWORD_TERMS)

	total_downloaded = 0
	total_failed = 0
	total_resolved = 0
	for archive_url in archive_urls:
		_validate_archive_url(archive_url)
		archive_path = urllib.parse.urlparse(archive_url).path.rstrip("/")
		archive_slug = archive_path.rsplit("/", 1)[-1]
		output_dir = os.path.join(REPO_ROOT, "output", f"neurotiker_haworth_{archive_slug}")
		manifest_path = os.path.join(output_dir, "manifest.json")
		output_dir = os.path.abspath(output_dir)
		manifest_path = os.path.abspath(manifest_path)

		raw_url = _archive_raw_url(archive_url)
		archive_wikitext = fetch_text(
			raw_url,
			max_retries=MAX_RETRIES,
			delay_base=DELAY_BASE,
		)
		file_titles = find_haworth_file_titles_from_wikitext(
			archive_wikitext,
			keyword_terms,
		)
		if not file_titles:
			archive_html = fetch_text(
				archive_url,
				max_retries=MAX_RETRIES,
				delay_base=DELAY_BASE,
			)
			file_titles = find_haworth_file_titles_from_html(
				archive_html,
				keyword_terms,
			)
		if args.limit > 0:
			file_titles = file_titles[:args.limit]
		image_entries = resolve_imageinfo(
			file_titles,
			max_retries=MAX_RETRIES,
			delay_base=DELAY_BASE,
		)

		downloaded = 0
		skipped_existing = 0
		failed = 0
		items = []
		if not args.dry_run:
			ensure_dir(output_dir)
		for entry in image_entries:
			image_url = entry["url"]
			filename = filename_from_url(image_url)
			local_path = os.path.join(output_dir, filename)
			file_record = {
				"title": entry["title"],
				"file_page": entry["file_page"],
				"url": image_url,
				"sha1": entry["sha1"],
				"size": entry["size"],
				"mime": entry["mime"],
				"local_path": local_path,
				"downloaded": False,
				"error": "",
			}
			if args.dry_run:
				items.append(file_record)
				continue
			if os.path.isfile(local_path):
				skipped_existing += 1
				items.append(file_record)
				continue
			try:
				content = download_binary(
					image_url,
					max_retries=MAX_RETRIES,
					delay_base=DELAY_BASE,
				)
			except urllib.error.HTTPError as error:
				failed += 1
				file_record["error"] = f"HTTPError {error.code}"
				items.append(file_record)
				print(f"WARN: {entry['title']} failed with HTTP {error.code}")
				continue
			except urllib.error.URLError as error:
				failed += 1
				file_record["error"] = f"URLError {error.reason}"
				items.append(file_record)
				print(f"WARN: {entry['title']} failed with URLError {error.reason}")
				continue
			with open(local_path, "wb") as handle:
				handle.write(content)
			downloaded += 1
			file_record["downloaded"] = True
			items.append(file_record)

		manifest = {
			"archive_url": archive_url,
			"keyword_terms": keyword_terms,
			"generated_at_utc": datetime.now(timezone.utc).isoformat(),
			"dry_run": args.dry_run,
			"output_dir": output_dir,
			"total_matched_links": len(file_titles),
			"resolved_files": len(image_entries),
			"downloaded_files": downloaded,
			"skipped_existing": skipped_existing,
			"failed_files": failed,
			"files": items,
		}
		ensure_dir(os.path.dirname(manifest_path))
		write_manifest(manifest_path, manifest)

		total_resolved += len(image_entries)
		total_downloaded += downloaded
		total_failed += failed
		print(f"Archive URL: {archive_url}")
		print(f"Keyword terms: {', '.join(keyword_terms)}")
		print(f"Resolved files: {len(image_entries)}")
		print(f"Downloaded files: {downloaded}")
		print(f"Skipped existing: {skipped_existing}")
		print(f"Failed files: {failed}")
		print(f"Manifest: {manifest_path}")

	print(f"Total resolved: {total_resolved}")
	print(f"Total downloaded: {total_downloaded}")
	print(f"Total failed: {total_failed}")


if __name__ == "__main__":
	run()
