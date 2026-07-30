# Human guidance

## Persistent document ownership

- The OASA backend owns the authoritative complete CDML document.
- Frontends communicate persistent changes to the backend exclusively through
  CDML. The first implementation uses complete-document CDML submissions and
  canonical complete-document responses.
- The backend preserves every persistent CDML object, either as a typed record
  or as opaque XML. This includes molecules, arrows, text, plus signs,
  brackets, vectors, groups, reactions, paper/header data, object order, IDs,
  references, attributes, and unknown XML.
- Qt owns only live projections and transient interaction state: graphics
  items, selection, hover, handles, gesture previews, dialogs, viewport, and
  Qt object lifetime.
- Qt must not restore or merge persistent content omitted by a backend
  round-trip. If it does, Qt is the hidden document owner and the CDML-only
  boundary has failed.
- The central acceptance invariant is: a backend-only CDML round-trip preserves
  every persistent object without any frontend re-merge.

## Boundary-preserving cleanup

- Cleanup is not authorization to redesign the architecture or expand scope.
- Preserve backend/frontend-agnostic contracts where they exist or can remain
  without expanding the work.
- Backend-facing APIs, data models, serialization, and tests use plain
  immutable Python data, complete CDML, and explicit request/response behavior.
  They must not acquire Qt, `QObject`, graphics, or frontend-lifetime
  assumptions.
- Qt types and lifetimes stay in frontend projections and adapters.

## Revision and identity rules

- Backend snapshots are immutable. Each accepted `commit(expected_revision,
  complete_cdml)` creates one new, monotonically increasing revision.
- `restore(target_revision, expected_revision)` copies the target content into
  a new, monotonically increasing revision; it never moves the revision
  counter backward.
- Qt records only undo/redo navigation entries and labels. Before a restore,
  the backend protects the immediate pre-restore revision so redo can restore
  it. Each restore replaces that redo protection with its own immediate
  pre-restore revision. A new accepted edit clears both Qt redo navigation and
  that protection, but never mutates retained backend snapshots.
- New and native-CDML backend sessions begin clean. A non-CDML import begins
  from a clean blank session, then commits converted complete CDML, so it is
  dirty and pathless until Save As succeeds.
- After a successful filesystem write, the frontend calls
  `mark_saved(expected_revision)`. The backend retains the canonical saved
  content and protects that exact saved revision from history eviction. History
  capacity is at least three revisions, so the current, saved, and immediate
  pre-restore revisions may all remain restorable when they differ. Older
  nonprotected history may evict. Clean state compares canonical content to
  the saved baseline, not revision numbers, so restoring saved content becomes
  clean.
- `__bkchem_new__<token>` is a transaction-local provisional correlation token
  in recognized ID declarations and known reference positions. Each declared
  token is unique; known references may repeat a declared token. Qt creates
  tokens, never durable persistent IDs. The backend validates and resolves only
  those recognized positions atomically during commit. The stored-snapshot and
  canonical-response prohibition applies only to recognized positions; matching
  strings in opaque XML, unknown attributes/elements, or text remain unchanged.

See
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
and the settled
[CDML backend document authority decision](active_plans/decisions/cdml_backend_document_authority_2026-07-27.md).
