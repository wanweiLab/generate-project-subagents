#!/usr/bin/env python3
"""Validate project-scoped Codex custom-agent files without modifying the project."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


BEGIN = "<!-- BEGIN generate-project-subagents: delegation-policy -->"
END = "<!-- END generate-project-subagents: delegation-policy -->"
REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
}
SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}
ROLE_LIKE_SUFFIXES = (
    "-worker",
    "-explorer",
    "-reviewer",
    "-runner",
    "-debugger",
    "-researcher",
)
ROLE_LIKE_UNDERSCORE_SUFFIXES = (
    "_worker",
    "_explorer",
    "_reviewer",
    "_runner",
    "_debugger",
    "_researcher",
)
ROLE_LIKE_NAMES = {"reviewer", "explorer", "worker", "test-runner"}
UNKNOWN_RUNTIME_VALUES = {"unknown", "unknown/unverified", "unverified"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate .codex/agents/*.toml and the managed AGENTS.md policy."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        type=Path,
        help="Project root to inspect (default: current directory).",
    )
    parser.add_argument(
        "--capabilities",
        type=Path,
        help=(
            "Optional JSON model capability map. Use either "
            "{\"model\": [\"medium\"]} or "
            "{\"models\": {\"model\": {\"reasoning_effort\": [\"medium\"]}}}."
        ),
    )
    parser.add_argument(
        "--require-capabilities",
        action="store_true",
        help="Fail when model support cannot be checked from --capabilities.",
    )
    parser.add_argument(
        "--strict-names",
        action="store_true",
        help="Treat a filename/name mismatch as an error instead of a warning.",
    )
    parser.add_argument(
        "--runtime-report",
        type=Path,
        help=(
            "Optional JSON report captured from an end-to-end launcher run. "
            "It is compared with the generated TOML settings."
        ),
    )
    parser.add_argument(
        "--require-runtime-report",
        action="store_true",
        help=(
            "Fail when --runtime-report is absent or does not contain the "
            "role, model, reasoning effort, and sandbox fields."
        ),
    )
    return parser.parse_args()


def load_capabilities(path: Path | None) -> dict[str, set[str] | None] | None:
    if path is None:
        return None

    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read capabilities JSON {path}: {exc}") from exc

    models = raw.get("models", raw) if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise ValueError("capabilities JSON must contain an object of models")

    normalized: dict[str, set[str] | None] = {}
    for model, value in models.items():
        if isinstance(value, list):
            normalized[str(model)] = {str(item) for item in value}
            continue
        if isinstance(value, dict):
            efforts = value.get("reasoning_effort", value.get("reasoning_efforts"))
            if efforts is None:
                efforts = value.get("efforts")
            if efforts is None:
                normalized[str(model)] = None
            elif isinstance(efforts, list):
                normalized[str(model)] = {str(item) for item in efforts}
            else:
                raise ValueError(
                    f"capability efforts for {model!r} must be a list"
                )
            continue
        raise ValueError(
            f"capability entry for {model!r} must be a list or object"
        )
    return normalized


def add_issue(
    issues: list[tuple[str, str]], severity: str, message: str
) -> None:
    issues.append((severity, message))


def load_runtime_report(path: Path) -> list[dict[str, object]]:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read runtime report {path}: {exc}") from exc

    records = raw.get("agents") if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        raise ValueError(
            "runtime report must be a JSON array or an object with an 'agents' array"
        )

    normalized: list[dict[str, object]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"runtime report record {index} must be an object")
        normalized.append(record)
    return normalized


def validate_runtime_report(
    root: Path,
    records: list[dict[str, object]],
    require_runtime_report: bool,
) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    agents_dir = root / ".codex" / "agents"
    expected_by_name: dict[str, tuple[Path, dict[str, object]]] = {}
    for path in sorted(agents_dir.glob("*.toml")):
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            expected_by_name[name] = (path.resolve(), data)

    seen: set[str] = set()
    required_fields = ("model", "reasoning_effort", "sandbox_mode")
    for index, record in enumerate(records):
        role = record.get("agent_role") or record.get("requested_name")
        if not isinstance(role, str) or not role.strip():
            add_issue(
                issues,
                "ERROR" if require_runtime_report else "WARNING",
                f"runtime report record {index}: missing agent_role or requested_name",
            )
            continue

        if role in seen:
            add_issue(issues, "ERROR", f"runtime report has duplicate role {role!r}")
        seen.add(role)
        expected = expected_by_name.get(role)
        if expected is None:
            add_issue(
                issues,
                "ERROR",
                f"runtime report references unknown agent {role!r}",
            )
            continue

        expected_path, toml_data = expected
        actual_path = record.get("agent_path")
        if actual_path is None:
            add_issue(
                issues,
                "ERROR" if require_runtime_report else "WARNING",
                f"runtime report {role!r}: missing agent_path",
            )
        elif not isinstance(actual_path, str) or Path(actual_path).resolve() != expected_path:
            add_issue(
                issues,
                "ERROR",
                f"runtime report {role!r}: agent_path does not match {expected_path}",
            )

        for field in required_fields:
            expected_key = (
                "model_reasoning_effort" if field == "reasoning_effort" else field
            )
            expected_value = toml_data.get(expected_key)
            actual_value = record.get(field)
            if expected_value is None:
                continue
            is_unknown = (
                isinstance(actual_value, str)
                and actual_value in UNKNOWN_RUNTIME_VALUES
            )
            if actual_value is None or is_unknown:
                add_issue(
                    issues,
                    "ERROR" if require_runtime_report else "WARNING",
                    f"runtime report {role!r}: missing effective {field}",
                )
            elif actual_value != expected_value:
                add_issue(
                    issues,
                    "ERROR",
                    f"runtime report {role!r}: effective {field}={actual_value!r} "
                    f"does not match TOML {expected_value!r}",
                )

    if not records:
        add_issue(
            issues,
            "ERROR" if require_runtime_report else "WARNING",
            "runtime report contains no agent records",
        )
    return issues


def validate_agents(
    root: Path,
    capabilities: dict[str, set[str] | None] | None,
    require_capabilities: bool,
    strict_names: bool,
) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    agents_dir = root / ".codex" / "agents"
    if not agents_dir.is_dir():
        add_issue(issues, "ERROR", f"missing agents directory: {agents_dir}")
        return issues

    files = sorted(agents_dir.glob("*.toml"))
    if not files:
        add_issue(issues, "ERROR", f"no custom-agent TOML files found in {agents_dir}")
        return issues

    names: dict[str, Path] = {}
    for path in files:
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            add_issue(issues, "ERROR", f"{path}: invalid TOML: {exc}")
            continue

        for field in ("name", "description", "developer_instructions"):
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                add_issue(issues, "ERROR", f"{path}: missing non-empty {field!r}")

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        if name in names:
            add_issue(
                issues,
                "ERROR",
                f"duplicate agent name {name!r}: {names[name]} and {path}",
            )
        else:
            names[name] = path

        if path.stem != name:
            severity = "ERROR" if strict_names else "WARNING"
            add_issue(
                issues,
                severity,
                f"{path}: filename stem {path.stem!r} differs from name {name!r}",
            )

        model = data.get("model")
        effort = data.get("model_reasoning_effort")
        if isinstance(effort, str) and effort not in REASONING_EFFORTS:
            add_issue(
                issues,
                "ERROR",
                f"{path}: unsupported reasoning effort value {effort!r}",
            )

        sandbox_mode = data.get("sandbox_mode")
        if sandbox_mode is not None and not isinstance(sandbox_mode, str):
            add_issue(issues, "ERROR", f"{path}: sandbox_mode must be a string")
        elif isinstance(sandbox_mode, str) and sandbox_mode not in SANDBOX_MODES:
            add_issue(
                issues,
                "WARNING",
                f"{path}: sandbox_mode {sandbox_mode!r} was not recognized by this validator",
            )

        if model is not None and not isinstance(model, str):
            add_issue(issues, "ERROR", f"{path}: model must be a string")
        if effort is not None and not isinstance(effort, str):
            add_issue(
                issues,
                "ERROR",
                f"{path}: model_reasoning_effort must be a string",
            )

        if model is not None and isinstance(model, str):
            if capabilities is None:
                severity = "ERROR" if require_capabilities else "WARNING"
                add_issue(
                    issues,
                    severity,
                    f"{path}: model support is unverified; provide --capabilities",
                )
            elif model not in capabilities:
                add_issue(
                    issues,
                    "ERROR",
                    f"{path}: model {model!r} is absent from the capability map",
                )
            elif (
                isinstance(effort, str)
                and capabilities[model] is not None
                and effort not in capabilities[model]
            ):
                add_issue(
                    issues,
                    "ERROR",
                    f"{path}: {model!r} does not advertise reasoning effort {effort!r}",
                )

    validate_policy(root, set(names), issues)
    return issues


def validate_policy(
    root: Path, agent_names: set[str], issues: list[tuple[str, str]]
) -> None:
    policy_path = root / "AGENTS.md"
    if not policy_path.exists():
        add_issue(issues, "WARNING", f"no root AGENTS.md found: {policy_path}")
        return

    try:
        text = policy_path.read_text()
    except OSError as exc:
        add_issue(issues, "ERROR", f"cannot read {policy_path}: {exc}")
        return

    begin_count = text.count(BEGIN)
    end_count = text.count(END)
    if begin_count != end_count:
        add_issue(
            issues,
            "ERROR",
            f"{policy_path}: delegation markers are unbalanced ({begin_count} begin, {end_count} end)",
        )
    if begin_count > 1 or end_count > 1:
        add_issue(
            issues,
            "ERROR",
            f"{policy_path}: expected at most one managed delegation block",
        )
    if begin_count != 1 or end_count != 1:
        return

    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END, start)
    block = text[start:finish]
    for token in re.findall(r"`([^`]+)`", block):
        if token in agent_names:
            continue
        if (
            token in ROLE_LIKE_NAMES
            or token.endswith(ROLE_LIKE_SUFFIXES)
            or token.endswith(ROLE_LIKE_UNDERSCORE_SUFFIXES)
        ):
            add_issue(
                issues,
                "ERROR",
                f"{policy_path}: delegation policy references unknown agent {token!r}",
            )


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    try:
        capabilities = load_capabilities(args.capabilities)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    issues = validate_agents(
        root,
        capabilities,
        args.require_capabilities,
        args.strict_names,
    )
    if args.runtime_report is not None:
        try:
            runtime_records = load_runtime_report(args.runtime_report)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        issues.extend(
            validate_runtime_report(
                root,
                runtime_records,
                args.require_runtime_report,
            )
        )
    elif args.require_runtime_report:
        issues.append(
            (
                "ERROR",
                "--require-runtime-report requires --runtime-report",
            )
        )
    for severity, message in issues:
        print(f"{severity}: {message}")

    errors = sum(severity == "ERROR" for severity, _ in issues)
    warnings = sum(severity == "WARNING" for severity, _ in issues)
    if errors:
        print(f"INVALID: {errors} error(s), {warnings} warning(s)")
        return 1
    print(f"VALID: 0 error(s), {warnings} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
