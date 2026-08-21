# Contributing

Contributions should preserve the Skill's narrow purpose: generating persistent
project-scoped Codex custom-agent configuration and an optional managed
delegation policy.

## Before submitting a change

1. Keep `SKILL.md` focused on decisions needed while the Skill runs. Put schema,
   runtime-verification, or packaging details in the relevant supporting file.
2. Preserve user-authored project files and authorization boundaries.
3. Do not claim runtime role, model, reasoning, sandbox, token, or quota values
   without independent metadata from the launcher or host.
4. Add or update behavioral tests for validator changes.
5. Run:

   ```bash
   python3 -m unittest discover -s tests -v
   python3 -m compileall -q scripts tests
   ```

6. Validate at least one realistic generated project when changing the Skill's
   workflow or custom-agent schema guidance.

## Pull requests

Keep pull requests focused. Describe the user-visible behavior, the evidence or
official documentation behind configuration changes, and the validation that
was performed. Avoid unrelated formatting or refactoring.

By contributing, you agree that your contributions are licensed under the MIT
License included in this repository.
