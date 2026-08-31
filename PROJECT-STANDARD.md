# Project Standard

## Declaration

- Standard: Software Project Living Documentation Standard 2.2.
- Tier: 2, System.
- Lifecycle: Greenfield, Phase 0 research with a transport-free Phase 1 foundation.
- Requirements authority: `REQUIREMENTS.md` is a living product requirements document.
- Physical impact: Any future production write path is a Class 4 architectural and security change.

## Authority mapping

The machine-readable mirror is `.docs-authority.json`.

| Responsibility | Authority |
| --- | --- |
| Project overview | `README.md` |
| Current assessment | `ASSESSMENT.md` |
| Architecture | `ARCHITECTURE.md` |
| Change history | `CHANGELOG.md` |
| Defect tracking | `ISSUES.md` |
| Technical debt | `TECH-DEBT.md` |
| Deferred improvements | `FUTURE-UPGRADES.md` |
| Validation | `VALIDATION.md` |
| Operations | `OPERATIONS.md` |
| Decision history | `docs/decisions/` |
| Resolved history | `docs/archive/` |
| Development rules | `PROJECT-STANDARD.md` |
| Agent rules | `AGENTS.md` |

Supporting evidence lives in `TRACEABILITY.md`, `docs/COMPATIBILITY.md`, `docs/ADAPTERS.md`, `docs/ENDURO2-RESEARCH.md`, and `docs/SECURITY.md`. Those files do not replace the authorities above.

## Change classes

- Class 0: Formatting and generated output with no behavior change.
- Class 1: Documentation clarification with no scope or behavior change.
- Class 2: Internal implementation or test change that preserves public behavior.
- Class 3: User-visible behavior, CLI, schema, adapter, locator, or capability change.
- Class 4: Trust boundary, authentication, privacy, risk classification, backup, recovery, or physical write change.

Class 3 changes require updated tests, README or operations guidance, validation evidence, and changelog entry. Class 4 changes additionally require an ADR, threat-model review, failure-injection coverage, and explicit human approval.

## Required routed reads

Before changing code, read:

1. `AGENTS.md`.
2. The authority responsible for the affected behavior.
3. `docs/SECURITY.md` for authentication, persistence, automation, device, or privacy work.
4. `docs/ADAPTERS.md` for transport or capability work.
5. Relevant ADRs under `docs/decisions/`.

## Definition of done

A change is complete only when:

- The behavior is implemented without enabling physical writes.
- Tests cover success, important failure paths, malicious imports, and transport isolation.
- `python -m pytest`, Ruff, Mypy, `pip check`, schema drift verification, and `scripts/docs-check.ps1` pass.
- The dependency audit reports no known vulnerability, excluding the unpublished editable project itself.
- Required authorities and supporting evidence are updated.
- The diff contains no runtime artifacts, credentials, personal identifiers, or generated package metadata.
- Hardware-dependent claims remain pending until recorded physical evidence exists.
