# Requirement Traceability

This matrix records current repository evidence. `REQUIREMENTS.md` remains the product authority. A passing fake or offline test never counts as physical-watch acceptance.

| Requirement | Current status | Evidence | Remaining gate |
| --- | --- | --- | --- |
| FR-001 Device discovery | Partial | `AdbService`, doctor command, exact device selection tests | USB/MTP, Garmin Express, and physical acceptance |
| FR-002 Capability discovery | Partial | Detailed read-only capability manifest and fake-device contract | Physical model, firmware, and selector evidence |
| FR-003 Configuration export | Partial | Sanitized bundle capture with YAML, manifest, summary, coverage, and checksums | Broader setting groups and optional safe raw artifacts |
| FR-004 Declarative configuration | Implemented for offline scope | Strict YAML and JSON models, generated schema, example, stable identifiers, merge policy | Comment-preserving round trips and approved reset operations |
| FR-005 Backup catalog | Not implemented | Tracked in `FUTURE-UPGRADES.md` | Catalog, search, inspect, and recoverable deletion |
| FR-006 Validation and migration | Partial | Syntax, schema, sensitive-input, checksum, model, and firmware validation | Schema migration and compatibility mappings |
| FR-007 Diff and dry-run plan | Implemented for read-only scope | Snapshot planning covers compliant, guided, unsupported, unknown, and blocked states | Automatic operation planning requires an approved adapter |
| FR-007a Bundle comparison | Implemented for read-only scope | Offline bundle or configuration comparison and model-specific warning | GUI workflow |
| FR-008 Apply engine | Blocked by policy | In-memory simulation only; no physical adapter | Authorization, backup, physical evidence, and Class 4 ADR |
| FR-009 Verification | Blocked by policy | Simulation independently verifies restoration | Approved physical read and write adapter |
| FR-010 Activity management | Not implemented | Schema accepts semantic activity settings | Physical discovery and guided or approved adapter workflow |
| FR-011 Activity profiles | Not implemented | Architecture and schema can carry nested values | Capability evidence and UI |
| FR-012 Watch faces | Not implemented | Read-only policy documented | Documented metadata surface and guided workflow |
| FR-013 Additional domains | Partial | Stable generic settings and explicit coverage states | Domain-specific profiles and physical evidence |
| FR-014 Guided actions | Partial | Plans classify mismatches as `requires_user_action` with guidance | Versioned model-specific instruction library and re-verification |
| FR-015 GUI | Partial | Shared service-based read-only audit shell | Bundle, comparison, plan, catalog, and accessibility workflows |
| FR-016 CLI | Partial | Audit plus offline capture, validate, compare, plan, import, and export | Uniform JSON mode, non-interactive contract, catalog, and approved apply commands |
| FR-017 Reports and audit | Partial | Sanitized JSON and Markdown audit, comparison, plan, and simulation reports | Unified job catalog and physical operation results |
| FR-018 Import and portability | Partial | Strict directory and ZIP import, safe export, checksums, cross-model warnings | Raw-artifact rules and compatibility mappings |
| FR-019 Profiles and overlays | Implemented for offline scope | Ordered overlays with explicit conflict reporting | GUI editor |
| FR-020 Compatibility data | Partial | Versioned schema, explicit unknown firmware blocking, compatibility evidence | Signed release-shipped profiles |
| FR-021 Documentation compliance | Implemented | Tier 2 authorities, machine mapping, docs check, traceability | Continue routing on every Class 2 or higher change |
| AC-001 Safe read-only audit | Fake contract passed | Exact package, authentication, identity, firmware, settings, cleanup, redaction | Physical Enduro 2 acceptance |
| AC-002 Configuration capture | Offline contract passed | Valid bundle, checksums, coverage states, tamper detection | Physical capture evidence |
| AC-003 Favorites plan | Structural support only | Generic semantic plan engine | Physical favorites inventory evidence |
| AC-004 through AC-009 | Blocked or partial | Simulation and fail-closed planning only | Approved adapter, recovery, hardware, and rollback gates |
| AC-010 Secret redaction | Automated passed | Recursive redaction and malicious-input tests | Manual artifact review remains required |
