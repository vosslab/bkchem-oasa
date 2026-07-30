# VectorMode M0 decision

Date: 2026-07-30

## Result

M0 selects creation-only `rect`, `oval`, and `polyline` gestures for the
backend-authoritative VectorMode slice. The Qt preview is transient feedback;
the completed gesture supplies immutable shape and endpoint data to the
session, which commits one complete-CDML candidate and reprojects OASA's
canonical snapshot.

## Compatibility rule

The historical gesture threshold is retained exactly: discard only when both
absolute drag axes are less than `5.0` scene points. A horizontal or vertical
rectangle or oval with one zero axis is deliberately accepted.

## Boundaries

The visible M0 choices are Rectangle, Oval, and Polyline. Square, circle, and
polygon creation, every existing-vector edit/move/style/delete/reorder path,
and opaque `<vector>` semantics remain outside this slice. Accepted creates
use OASA-issued durable IDs and backend revision history; Qt undo owns none of
the accepted route.
