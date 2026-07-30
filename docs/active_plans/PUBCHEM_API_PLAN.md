# PubChem API plan

## Goals
- Provide a reliable molecule lookup path that can supply names, identifiers,
  and basic properties for OASA and BKChem workflows.
- Reuse existing PubChem parsing logic from
  `/Users/vosslab/nsh/biology-problems/problems/biochemistry-problems/PUBCHEM/pubchemlib.py`
  when practical.
- Keep the integration lightweight and explicit, without hidden environment
  variables or silent network calls.

## Non-goals
- Do not replace existing OASA core chemistry logic.
- Do not add UI changes in BKChem as part of the first iteration.
- Do not add new dependencies beyond what is already in `pip_requirements.txt`
  unless clearly required.

## Data sources
- Use the PubChem REST API as the authoritative lookup source.
- Seed or validate against the existing local dataset at
  `/Users/vosslab/nsh/biology-problems/data/pubchem_molecules_data.yml`.

## Data model
- Store normalized identifiers: PubChem CID, InChI, InChIKey, SMILES.
- Store a display name and any common synonyms returned by PubChem.
- Store minimal properties needed by BKChem and OASA (for example formula and
  molecular weight), not the full PubChem payload.

## Storage and caching
- Cache responses under `packages/oasa/oasa_data/pubchem_cache/` with one JSON
  file per CID.
- Track a compact index file mapping lookup keys to CIDs for fast reuse.
- Support a configurable cache refresh age (default: never refresh unless
  forced by a user command).

## Interface design
- Add a small `oasa.pubchem` module that exposes `lookup_by_name`,
  `lookup_by_inchi`, and `lookup_by_inchikey`.
- Add a single CLI tool (under `tools/`) that accepts a query, prints a summary,
  and optionally writes cache files.

## Implemented first slice

- `oasa.pubchem` now provides an offline-testable CID foundation:
  `lookup_by_cid(cid, transport)` fetches the PUG REST property and synonym
  endpoints only through a caller-supplied transport.
- The foundation normalizes the documented `PropertyTable.Properties` and
  `InformationList.Information[].Synonym` response shapes into an immutable
  compound record. It validates CIDs, required identifiers, and finite
  molecular weights.
- Malformed, not-found, and transport responses raise explicit domain errors
  at the backend boundary; callers may later choose a presentation policy.
- Name, InChI, and InChIKey query APIs now share the same injected-transport
  property/synonym pipeline. Query paths are percent-encoded and each lookup
  requires exactly one property record; ambiguous records, malformed payloads,
  not-found responses, and transport failures remain explicit domain errors.
- `oasa.pubchem_http.fetch_json(url, opener=None)` is an opt-in stdlib HTTPS
  transport foundation. It limits requests to canonical PubChem PUG HTTPS,
  sends JSON-focused request headers, bounds time and response size, rejects
  every redirect before its destination can be contacted, and maps HTTP 404
  to the existing not-found error.
  Lookup still makes no request unless a caller explicitly supplies this (or
  another) transport.
- BKChem-Qt now has an explicit, modeless Chemistry > Lookup PubChem dialog.
  A user click starts a session-owned worker using the explicit HTTPS transport;
  lookup, SMILES parsing, and coordinate generation stay off the GUI thread.
  Results are immutable until the separate Insert click creates undoable Qt
  molecules in the originating tab. Tests inject a transport, so no test makes
  a live request. Caching, retry policy, preferences, and CLI support remain
  unimplemented.

## Error handling
- Fail fast on network errors with a clear message that includes the query.
- Keep `PubChemNotFoundError` explicit at the backend boundary, so later CLI
  and UI policies can decide how to present absence without losing the cause.
- Logging cached versus network responses belongs to the future cache/client
  layer, not this injected-transport boundary.

## Rate limits and etiquette
- A future explicit client may implement PubChem's published usage guidance.
  The normalized backend and its injected transport do not schedule, delay,
  retry, or randomize requests.

## Tests
- Unit tests for parsing and normalization.
- Integration tests that run only when a local cache fixture is available.
- No live network calls in CI tests by default.

## Rollout steps
- Add the `oasa.pubchem` module and a CLI tool.
- Import and adapt `pubchemlib.py` helpers from the biology-problems repo.
- Add cache fixtures and tests.
- Document usage in `docs/USAGE.md` and `packages/oasa/docs/USAGE.md`.
