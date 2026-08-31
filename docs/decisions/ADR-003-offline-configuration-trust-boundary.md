# ADR-003: Offline Configuration Trust Boundary

- Status: Accepted.
- Date: 2026-08-30.
- Class: 4.

## Context

Configuration files and ZIP bundles are user-controlled input. They can contain malicious YAML features, oversized payloads, path traversal, links, invalid checksums, or sensitive values. Planning output must remain structurally unable to reach a device transport.

## Decision

- Configuration and planning commands complete before ADB or Appium services are constructed.
- YAML uses safe loading and rejects explicit tags, anchors, and aliases. JSON and YAML use strict typed models and size limits.
- Sensitive keys and values are rejected before they enter desired state.
- Bundle archives contain exactly `config.yaml`, `manifest.json`, and `summary.md` at the archive root.
- Archive paths, links, file sizes, expanded size, compression ratios, schemas, and SHA-256 records are validated before import.
- Imported content is redacted and receives new checksum records before persistence under the configured runtime directory.
- Redaction preserves only exact SHA-256 fields, validated semantic setting identifiers, and tool-generated correlation identifiers under their typed keys.
- Change plans expose no apply callback or adapter. Every mismatch is guided, unsupported, unknown, or blocked, and every operation has `automatic: false`.

## Consequences

Offline comparison and planning can progress without broadening the device trust boundary. Archives with extra files or advanced YAML features are intentionally rejected. A future signed-bundle or physical-apply design requires a separate decision and cannot reuse this read-only plan as authorization to mutate a watch.
