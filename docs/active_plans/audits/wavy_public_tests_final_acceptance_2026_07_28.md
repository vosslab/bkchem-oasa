# Final acceptance: Wavy creation public tests

Date: 2026-07-28. Scope: independent acceptance review of the creation-only
normal Wavy backend-authority slice and its current public behavioral tests.
This review made no production, test, contract, plan, or changelog edit. This
report is its only artifact.

## Verdict

**PASS -- creation-only Wavy is accepted.** No P1, P2, or concrete blocking
P3 finding remains in the Wavy acceptance slice.

This accepts only normal Wavy creation through the backend-authoritative
coordinator. It does not accept configure, move, delete, other presentation
families, or M4 as a whole.

## Findings

### P1

None.

### P2

None.

### P3

None in scope. The Wavy tests now use public `MainWindow.on_new()`,
`MainWindow.sessions`, `MainWindow.document`, `MainWindow.close_session_at()`,
`DocumentSession.mode_manager`, `DocumentSession.backend_snapshot`, and
supported `DocumentSession.write_backend_snapshot()` boundaries. They select
canonical and projected records by semantic namespace/local-name/durable-ID
facts rather than child offsets or private window/session aliases. Their
paired assertions represent one coherent behavioral state transition; pure
geometry endpoint indexing is a direct mathematical observation and is
allowed.

`test_misc_mode_wavy.py` still contains `_seed_atom()` for the unrelated
numbering-ribbon regression, which invokes private
`DrawMode._create_atom_at()`. That helper neither selects nor observes Wavy
state and is outside this creation-only Wavy acceptance scope. It is not a
blocking Wavy P3 finding. No remaining private MainWindow, active-session,
mode-manager alias, transient Wavy-preview, or Wavy-start access occurs in
the accepted Wavy tests.

## Architectural evidence

- `MiscMode.mouse_release()` drops transient preview/start state, validates
  geometry, and submits immutable `wavy.add`; it has no Qt-local persistent
  fallback.
- `DocumentSession` rejects targeted or malformed requests, then submits only
  immutable endpoints. OASA derives bounded geometry, rejects zero-length
  gestures, authors the Wavy CDML, and commits it atomically.
- Accepted mutation goes through `submit_persistent_operation()`: OASA commits
  the complete CDML, backend history records the revision, and the canonical
  snapshot is reprojected. Undo/redo tests observe the backend-driven
  disappearance/restoration of both canonical and disposable projection.
- `write_backend_snapshot()` publishes the exact synchronized snapshot and
  only then marks the backend saved baseline; the focused Save test observes
  equivalent published Wavy semantics and `is_dirty is False`.
- Rejected, unavailable, zero-length, and extreme inputs preserve the public
  backend snapshot and leave no presentation-object fallback.

## Verification

Every pytest command used `source source_me.sh && QT_QPA_PLATFORM=offscreen
python3 -W error -m pytest --kill-after 3 -q` and ran in its own process.

| Exact command selection | Result | Exit |
| --- | --- | ---: |
| `test_wavy_candidate_preserves_existing_core_records` | `1 passed in 0.17s` | 0 |
| `test_wavy_candidate_preserves_opaque_namespace_text` | `1 passed in 0.16s` | 0 |
| `test_wavy_candidate_assigns_durable_identity_and_defaults` | `1 passed in 0.16s` | 0 |
| `test_wavy_candidate_preserves_requested_geometry` | `1 passed in 0.16s` | 0 |
| `test_wavy_rejections_preserve_registered_backend` | `5 passed in 0.18s` | 0 |
| `test_wavy_targeted_creation_request_preserves_registered_authority` | `1 passed in 0.16s` | 0 |
| `test_wavy_validation_precedes_candidate_building` | `1 passed in 0.16s` | 0 |
| `test_registered_wavy_drag_matches_canonical_projection` | `1 passed in 0.28s` | 0 |
| `test_registered_wavy_drag_has_requested_endpoints_and_bend` | `1 passed in 0.28s` | 0 |
| `test_registered_wavy_drag_uses_backend_history_not_qt_undo` | `1 passed in 0.28s` | 0 |
| `test_registered_wavy_public_undo_redo_reprojects_state` | `1 passed in 0.38s` | 0 |
| `test_registered_wavy_authoritative_save_publishes_clean_snapshot` | `1 passed in 0.25s` | 0 |
| `test_zero_length_wavy_gesture_is_a_clean_no_op` | `1 passed in 0.16s` | 0 |
| `test_extreme_wavy_drag_leaves_public_document_unchanged` | `1 passed in 0.16s` | 0 |
| `test_absent_wavy_callback_leaves_state_clean_and_accepts_a_new_gesture` | `1 passed in 0.16s` | 0 |
| `test_rejected_wavy_callback_leaves_state_clean_and_accepts_a_new_gesture` | `1 passed in 0.16s` | 0 |
| `source source_me.sh && python3 -m py_compile` on the three implementation and two Wavy test modules | clean | 0 |
| `git diff --check --` on those five paths | clean | 0 |

The quarantined native-SIGSEGV node
`test_qt_backend_session_adapter.py::test_same_tab_native_open_releases_replaced_native_wrappers`
was deliberately not run. No broad test file or suite, network operation, or
`/tmp` path was used.
