from __future__ import annotations

import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_generated_agents.py"
SPEC = importlib.util.spec_from_file_location("validate_generated_agents", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"cannot load validator from {SCRIPT}")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.agents_dir = self.root / ".codex" / "agents"
        self.agents_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_agent(
        self,
        filename: str,
        *,
        name: str,
        model: str | None = "gpt-test",
        effort: str | None = "medium",
        sandbox: str | None = "read-only",
        include_description: bool = True,
    ) -> Path:
        fields = [f'name = "{name}"']
        if include_description:
            fields.append('description = "A focused test role."')
        if model is not None:
            fields.append(f'model = "{model}"')
        if effort is not None:
            fields.append(f'model_reasoning_effort = "{effort}"')
        if sandbox is not None:
            fields.append(f'sandbox_mode = "{sandbox}"')
        fields.append(
            textwrap.dedent(
                '''
                developer_instructions = """
                Inspect the assigned scope and return evidence to the parent.
                """
                '''
            ).strip()
        )
        path = self.agents_dir / filename
        path.write_text("\n".join(fields) + "\n")
        return path

    def write_policy(self, body: str) -> None:
        (self.root / "AGENTS.md").write_text(
            f"{validator.BEGIN}\n{body}\n{validator.END}\n"
        )

    @staticmethod
    def messages(issues: list[tuple[str, str]]) -> list[str]:
        return [message for _, message in issues]

    def test_valid_agent_and_policy_have_no_issues(self) -> None:
        self.write_agent("reviewer.toml", name="reviewer")
        self.write_policy("Use `reviewer` after write-capable work.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=True,
        )

        self.assertEqual([], issues)

    def test_missing_required_field_is_an_error(self) -> None:
        self.write_agent(
            "reviewer.toml",
            name="reviewer",
            include_description=False,
        )
        self.write_policy("Use `reviewer` after write-capable work.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=True,
        )

        self.assertIn("ERROR", [severity for severity, _ in issues])
        self.assertTrue(
            any(
                "missing non-empty 'description'" in message
                for message in self.messages(issues)
            )
        )

    def test_duplicate_agent_name_is_an_error(self) -> None:
        self.write_agent("first.toml", name="shared-role")
        self.write_agent("second.toml", name="shared-role")
        self.write_policy("Delegate only when useful.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=False,
        )

        self.assertTrue(
            any(
                "duplicate agent name 'shared-role'" in message
                for message in self.messages(issues)
            )
        )

    def test_unknown_policy_role_is_an_error(self) -> None:
        self.write_agent("reviewer.toml", name="reviewer")
        self.write_policy("Use `backend-worker` for backend implementation.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=True,
        )

        self.assertTrue(
            any(
                "references unknown agent 'backend-worker'" in message
                for message in self.messages(issues)
            )
        )

    def test_unsupported_reasoning_effort_is_an_error(self) -> None:
        self.write_agent("reviewer.toml", name="reviewer", effort="impossible")
        self.write_policy("Use `reviewer` after write-capable work.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=True,
        )

        self.assertTrue(
            any(
                "unsupported reasoning effort value" in message
                for message in self.messages(issues)
            )
        )

    def test_capability_mismatch_is_an_error(self) -> None:
        self.write_agent("reviewer.toml", name="reviewer", effort="high")
        self.write_policy("Use `reviewer` after write-capable work.")

        issues = validator.validate_agents(
            self.root,
            {"gpt-test": {"medium"}},
            require_capabilities=True,
            strict_names=True,
        )

        self.assertTrue(
            any(
                "does not advertise reasoning effort 'high'" in message
                for message in self.messages(issues)
            )
        )

    def test_runtime_report_match_has_no_issues(self) -> None:
        path = self.write_agent("reviewer.toml", name="reviewer")
        records = [
            {
                "agent_role": "reviewer",
                "agent_path": str(path.resolve()),
                "model": "gpt-test",
                "reasoning_effort": "medium",
                "sandbox_mode": "read-only",
            }
        ]

        issues = validator.validate_runtime_report(
            self.root,
            records,
            require_runtime_report=True,
        )

        self.assertEqual([], issues)

    def test_runtime_report_mismatch_is_an_error(self) -> None:
        path = self.write_agent("reviewer.toml", name="reviewer")
        records = [
            {
                "agent_role": "reviewer",
                "agent_path": str(path.resolve()),
                "model": "another-model",
                "reasoning_effort": "low",
                "sandbox_mode": "workspace-write",
            }
        ]

        issues = validator.validate_runtime_report(
            self.root,
            records,
            require_runtime_report=True,
        )

        messages = self.messages(issues)
        self.assertTrue(
            any("effective model='another-model'" in message for message in messages)
        )
        self.assertTrue(
            any("effective reasoning_effort='low'" in message for message in messages)
        )
        self.assertTrue(
            any(
                "effective sandbox_mode='workspace-write'" in message
                for message in messages
            )
        )

    def test_capability_loader_supports_documented_shape(self) -> None:
        capability_path = self.root / "capabilities.json"
        capability_path.write_text(
            json.dumps(
                {
                    "models": {
                        "gpt-test": {"reasoning_efforts": ["low", "medium", "high"]}
                    }
                }
            )
        )

        capabilities = validator.load_capabilities(capability_path)

        self.assertEqual({"low", "medium", "high"}, capabilities["gpt-test"])


if __name__ == "__main__":
    unittest.main()
