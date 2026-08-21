# Generate Project Subagents

`generate-project-subagents` is a Codex Skill that analyzes a repository,
generates a small set of persistent project-scoped custom agents, and optionally
installs a model-led automatic delegation policy in the project `AGENTS.md`.

中文简介：这个 Skill 根据项目的真实目录、技术栈和验证命令生成
`.codex/agents/*.toml`，并可为后续 Codex 任务安装条件式自动委派规则。

> Status: **Alpha**. The configuration-generation workflow is usable, but exact
> runtime role, model, reasoning, and sandbox verification depends on metadata
> exposed by the active Codex launcher.

## What it does

- Inspects repository guidance, manifests, tests, CI, and existing Codex config.
- Chooses only roles justified by distinct, repeatable project work surfaces.
- Generates project custom-agent files under `.codex/agents/`.
- Supports per-agent model and reasoning-effort overrides.
- Maintains an isolated, replaceable delegation-policy block in root
  `AGENTS.md` unless TOML-only output is requested.
- Validates generated TOML, agent names, capability declarations, delegation
  references, and optional runtime metadata.

It does **not** replace Codex's subagent runtime, spawn one-off agents merely
because a task is complex, report account quota, or infer effective runtime
settings when the launcher does not expose them.

## Requirements

- A current Codex client with Skills support.
- Python 3.11 or newer for the bundled validator (`tomllib` is used).
- Git is recommended for repository discovery and reviewing changes.

The Skill and validator have no third-party runtime dependencies.

## Installation

Place this repository at one of the Codex Skill locations, for example:

```text
~/.codex/skills/generate-project-subagents/
```

The installed directory must contain `SKILL.md` at its root. Restart or refresh
Codex if the Skill does not appear immediately.

## Usage

Normal generation with automatic delegation policy:

```text
Use $generate-project-subagents to generate project agents for this repository.
```

Preview without writes:

```text
Use $generate-project-subagents in preview mode. Show the proposed agents,
model choices, and AGENTS.md policy diff without changing files.
```

Generate agent TOML files only:

```text
Use $generate-project-subagents in toml-only mode. Do not modify AGENTS.md.
```

User-defined model policy:

```text
Model policy:
- default: gpt-5.6-terra / medium
- reviewer: gpt-5.6 / high
- project_explorer: inherit
```

The Skill supports three modes:

| Mode | Writes agent TOML | Writes managed `AGENTS.md` policy |
| --- | :---: | :---: |
| `preview` | No | No |
| `apply` | Yes | Yes, unless explicitly disabled |
| `toml-only` | Yes | No |

## Generated project layout

Depending on project evidence, output can look like:

```text
project/
├── .codex/
│   └── agents/
│       ├── project-explorer.toml
│       ├── backend-worker.toml
│       └── reviewer.toml
└── AGENTS.md
```

The Skill does not create roles just for symmetry. A frontend agent, backend
agent, reviewer, debugger, or other specialist is generated only when its
instructions, tools, evidence, or write scope materially differ.

## Model and reasoning precedence

Generation-time policy decides which fields the Skill writes to a custom-agent
TOML:

1. explicit per-agent user override;
2. explicit user default;
3. the Skill's role-based recommendation;
4. inheritance only when the user requests `inherit`, `auto`, or an unpinned
   field.

At runtime, Codex first resolves a base value for each setting:

1. explicit spawn value;
2. the corresponding `[agents]` default;
3. the parent session value.

Codex then applies the selected custom-agent TOML. A `model` or
`model_reasoning_effort` present in that file overrides the corresponding base
value. A spawn override therefore cannot replace a value pinned in the selected
custom-agent TOML.

If a custom-agent file sets only `model`, it preserves the reasoning effort
resolved before the file is applied. The selected model must support that
effort.

See the official [Codex Subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [the local schema reference](references/custom-agent-schema.md).

## Validation

Validate a generated project:

```bash
python3 scripts/validate_generated_agents.py /absolute/path/to/project
```

Require an environment capability catalog:

```bash
python3 scripts/validate_generated_agents.py /absolute/path/to/project \
  --capabilities /absolute/path/to/capabilities.json \
  --require-capabilities
```

Compare independently captured runtime metadata:

```bash
python3 scripts/validate_generated_agents.py /absolute/path/to/project \
  --runtime-report /absolute/path/to/runtime.json \
  --require-runtime-report
```

Static validation proves declarations, not runtime application. A role is only
`effective` when launcher- or host-provided metadata confirms the selected role
and applied settings. Child self-reporting must remain labeled as self-reported.

## Development

Run the test suite with only the Python standard library:

```bash
python3 -m unittest discover -s tests -v
```

Run a syntax check:

```bash
python3 -m compileall -q scripts tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution expectations and
[CHANGELOG.md](CHANGELOG.md) for release notes.

## Security and safety

The Skill preserves existing custom-agent files by default, limits managed
`AGENTS.md` changes to a marked block, and does not edit application code,
credentials, CI secrets, or production settings as part of agent generation.

Generated sandbox values are declarations. The active host or parent session
can impose runtime behavior that differs from a custom-agent file, so safety
claims must rely on observed runtime metadata rather than TOML alone.

## License

Released under the [MIT License](LICENSE).
