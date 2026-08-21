# Project custom-agent schema

Source: [Codex Subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Use this reference when generating or reviewing `.codex/agents/*.toml` files.

## Required fields

Each standalone project custom-agent file must define:

```toml
name = "role_name"
description = "When the parent agent should use this role."
developer_instructions = """
Role-specific instructions.
"""
```

The `name` field is the source of truth for the agent identifier. Matching the
filename to the name is the recommended convention, but Codex does not use the
filename as the identity.

## Optional settings

Custom agent files may include supported session configuration such as:

```toml
model = "gpt-5.6-terra"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
```

They may also configure `mcp_servers` and `skills.config` when those resources
are available and the role genuinely needs them. Omit optional settings when
inheritance is the safer or more portable choice.

## Official model-selection strategy

When a custom agent needs pinned model settings, follow the current Subagents
guidance:

- Start with `gpt-5.6` for demanding, ambiguous, or multi-step work that needs
  planning, tool use, validation, and follow-through.
- Use `gpt-5.6-terra` for faster and lower-cost exploration, read-heavy scans,
  large-file review, or supporting-document processing.
- Use `gpt-5.6-luna` for fast, narrow, clear, repeatable, or high-volume work.

For `model_reasoning_effort`:

- `medium` is the balanced default;
- `low` is for straightforward tasks;
- `high` is for complex logic, security, review, and edge cases;
- `xhigh`, `max`, and `ultra` are for unusually demanding tasks and only when
  supported by the selected model and environment.

This Skill pins the official role-based recommendation by default for newly
generated agents, making the intended model strategy visible and reproducible.
Omit both fields only when the user explicitly requests `inherit`, `auto`,
dynamic selection, or no pinned model; then let Codex balance intelligence,
speed, and price dynamically.

## User-customized model policy

The generator should allow the user to override the official strategy per role
or set a default for roles without a specific override. A compact input format
is:

```text
Model policy:
- default: gpt-5.6-terra / medium
- project_explorer: inherit
- reviewer: gpt-5.6 / high
- backend_worker: gpt-5.6 / medium
```

Equivalent natural-language instructions are valid. At generation time, resolve
the policy in this order:

1. explicit per-agent user override;
2. explicit user default;
3. official role-based strategy;
4. omitted fields and normal Codex inheritance only when the user explicitly
   requests dynamic selection.

This is the Skill's generation policy: it determines which values are written
to the custom-agent TOML. Do not confuse it with Codex's runtime configuration
precedence described below.

`inherit` or `auto` means omit the corresponding fields. Partial overrides are
valid: if the user provides only a model or only a reasoning effort, leave the
other field unset so it keeps the previously resolved base value. A custom agent
file that sets only `model` therefore preserves the already resolved reasoning
effort; verify that the model supports that effort. Never silently replace a
user-selected model or effort that is unavailable; report the issue and request
a fallback, unless the user has already authorized use of the official fallback
strategy.

The generated handoff should identify the source of every declared choice: user
override, user default, official recommendation, or inherited/dynamic. Describe
a value as effective only when runtime metadata independently confirms it.

## Precedence and inheritance

Codex resolves model and reasoning settings in two stages.

First, it resolves a base value for each setting in this order:

1. explicit spawn value;
2. the corresponding `[agents]` default;
3. the parent session value.

Second, Codex applies the selected custom-agent TOML as a configuration layer.
If that file sets `model` or `model_reasoning_effort`, the file's value overrides
the corresponding base value. Field by field, the practical final precedence is
therefore:

1. the value present in the selected custom-agent TOML;
2. an explicit spawn value;
3. the corresponding `[agents]` default;
4. the parent session value.

There is one important interaction between the two fields: a custom-agent TOML
that sets only `model` preserves the reasoning effort resolved in the base
stage. Set `model_reasoning_effort` in the file as well when the selected model
does not support that preserved effort or when the role needs a different one.
If an explicit spawn request or `[agents]` default selects a model and neither
supplies a reasoning effort, Codex uses that model's default effort before the
custom-agent file is applied.

An explicit spawn value cannot replace a `model` or
`model_reasoning_effort` pinned in the selected custom-agent TOML. To honor a
different user-requested value for that role, update the TOML with authorization
or select a role that leaves the corresponding field unpinned. Other session
settings, such as `sandbox_mode`, `mcp_servers`, and `skills.config`, inherit
from the parent when the custom agent file omits them.

Subagents inherit the current sandbox policy unless the custom-agent file
explicitly overrides it. Keep read-heavy roles read-only where possible, and
make write-capable roles narrow and explicit.

The file is a declaration; it is not by itself a runtime trace. The launcher
must support selecting a project custom agent by its exact `name` for the
custom instructions and session settings to be applied. A generic subagent
interface that accepts only a prompt, model, or reasoning override cannot be
counted as loading a project TOML just because the prompt mentions the role.

Verify configuration in three stages:

1. `declared`: the TOML parses and contains the expected fields;
2. `role-bound`: the launcher reports the exact `agent_role` or `agent_path`;
3. `effective`: the runtime reports the model, reasoning effort, and sandbox
   actually in force.

If the effective sandbox differs from the TOML, treat the runtime value as the
one that governs safety and report the custom setting as not applied. In
particular, a child observed as `workspace-write` is not a read-only reviewer
even if its TOML says `sandbox_mode = "read-only"`. An outer session or host
permission policy may take precedence; do not claim that the TOML narrowed the
permissions unless the runtime confirms it.

## Global `[agents]` settings

Global defaults belong in project `.codex/config.toml` only when the user asks for
them. Supported settings include:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 4
default_subagent_model = "gpt-5.6"
default_subagent_reasoning_effort = "medium"
interrupt_message = true
```

Do not add these settings as a side effect of generating role files. Explicit
spawn values override these defaults during base resolution, but a selected
custom-agent TOML value is applied afterward and overrides the corresponding
base value. `agents.max_threads` is a legacy alias for the concurrency setting.

## Review checklist

- The role is narrow enough that a parent can route a bounded subtask to it.
- The description says when to use the role, not just what the role is called.
- Instructions name non-goals and a concrete handoff format.
- Read-only roles cannot accidentally edit the repository.
- Write roles have disjoint or explicitly coordinated scopes.
- Every referenced command, path, MCP server, and Skill exists in the project or
  current Codex environment.
- Existing files are preserved unless the user authorized an update.

## Automatic delegation

The TOML files define the available custom-agent roles and their session
settings. They do not automatically start subagents. For persistent project
routing, this Skill may maintain a managed section in the repository root
`AGENTS.md`:

```md
<!-- BEGIN generate-project-subagents: delegation-policy -->
...
<!-- END generate-project-subagents: delegation-policy -->
```

The policy is installed by default when this Skill generates roles, unless the
user requests TOML-only output or explicitly disables automatic delegation. It
must reference only agent names whose `.codex/agents/<name>.toml` files exist.
Re-running the Skill replaces only the managed section and preserves all
content outside it.

Use conditional routing rather than launching every role for every task:

- skip delegation for trivial or single-file work;
- use a read-heavy explorer before broad or ambiguous implementation when one
  exists;
- run independent domain workers in parallel only when their write scopes do
  not overlap;
- when a task matches a custom role, spawn the exact TOML `name` rather than an
  untyped or generic subagent; user-facing automatic routing still requires an
  explicit role selection at spawn time;
- use a read-only reviewer after write work when one exists; and
- wait for requested subagents before the parent integrates and reports.

The parent agent remains responsible for final integration, project-wide
validation, and conflict resolution. After spawning, it should verify the
runtime's effective role, model, reasoning effort, and sandbox when those values
are exposed. A child thread appearing in the UI is not proof that a custom TOML
was applied. A direct user instruction not to delegate overrides the policy. The
policy also must not change the model or reasoning effort selected in a
custom-agent TOML; those settings come from the agent file and the documented
precedence rules above. If the user requests a different value, update the TOML
with authorization or use an unpinned role instead of promising a spawn-time
override. Automatic delegation is still model-led behavior supported by
applicable `AGENTS.md`/Skill instructions, not a deterministic guarantee that
every eligible task launches a thread.

## Capability validation and preview

Before pinning `model` or `model_reasoning_effort`, check the active environment
when a model capability catalog is available. A user-selected unsupported value
must be reported and must not be silently replaced. If no catalog is available,
the Skill should label the value unverified rather than claiming that the
configuration is supported. Only an unpinned official default may be adapted to
another currently available model, and the substitution must be reported.

The generator supports three operating modes:

- `preview`: analyze and show the proposed files, model choices, policy diff,
  and validation results without writing anything;
- `apply`: write the requested files and managed policy after the plan is
  reported; and
- `toml-only`: write only `.codex/agents/*.toml` and leave `AGENTS.md` alone.

The bundled `scripts/validate_generated_agents.py` performs read-only structural
checks for TOML fields, duplicate names, optional model capability maps, the
managed delegation block, and (when `--runtime-report` is supplied) observed
runtime configuration. Without a runtime report it does not prove that a
subagent was actually spawned; that still requires an end-to-end task in the
target project.
