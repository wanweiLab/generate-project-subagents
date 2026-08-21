# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Public repository documentation, contribution guidance, tests, and CI.

## [0.1.0-alpha.1] - 2026-08-21

### Added

- Project-scoped custom-agent generation workflow.
- Preview, apply, and TOML-only modes.
- Optional managed automatic-delegation policy for project `AGENTS.md`.
- Per-agent model and reasoning policy with user overrides.
- Static agent, capability, policy, and optional runtime-report validation.

### Changed

- Clarified the two-stage model and reasoning precedence: Codex resolves spawn,
  `[agents]`, and parent defaults first, then applies the custom-agent TOML as
  the overriding configuration layer for fields present in that file.
