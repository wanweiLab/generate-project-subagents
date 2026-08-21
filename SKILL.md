---
name: generate-project-subagents
description: Generate or update project-scoped Codex custom subagent TOML files and, when enabled, install a project-level automatic delegation policy. Use when a project needs persistent specialized agents under `.codex/agents/`; do not use for ordinary one-off delegation without persistent agent files.
metadata:
  short-description: Generate project subagent constraint files
---

# Generate project subagents

Create a small, evidence-based set of project-scoped custom agents in
`.codex/agents/`. Each generated file is a constraint layer for one narrow role,
not a general-purpose prompt or a copy of the repository handbook.

The official Subagents documentation is the source of truth for the file format:
<https://learn.chatgpt.com/docs/agent-configuration/subagents>.
Read [custom-agent-schema.md](references/custom-agent-schema.md) when you need
the exact field and inheritance details.
Read [runtime-verification.md](references/runtime-verification.md) when you need
to prove that a generated role was selected and its model, reasoning effort,
and sandbox were applied by the launcher.

## Operating contract

- Work from the repository root. Confirm it with `git rev-parse --show-toplevel`
  when Git is available; otherwise use the current project directory.
- Inspect existing project guidance before writing anything: `AGENTS.md`, nested
  `AGENTS.md` files relevant to the target paths, `CONTRIBUTING*`, `README*`,
  package/build manifests, test configuration, CI workflows, and existing
  `.codex/config.toml` or `.codex/agents/*.toml` files.
- Treat repository instructions as requirements. The generated agents must not
  weaken them, invent tools or commands, or claim access to services that the
  project does not configure.
- Prefer a few complementary agents over a large catalog. Generate only roles
  that correspond to distinct, repeatable work surfaces found in the project.
- Preserve existing custom agent files by default. If a proposed role maps to an
  existing file, show the intended change and ask before overwriting it; merge
  only when the user explicitly asks for an update.
- Do not change application code, credentials, CI secrets, or production
  settings as part of this workflow.
- When automatic delegation is enabled or requested, the only permitted change
  to the root `AGENTS.md` is adding or replacing the managed delegation-policy
  section described in step 6. Preserve every user-authored line outside that
  section. When automatic delegation is disabled, do not change `AGENTS.md`.

## Workflow

### 1. Select the operating mode

Resolve the user's requested mode before discovery or writes:

- `preview`: inspect the repository, calculate proposed agents and policy, and
  show the effective model/reasoning choices plus a concise file diff. Do not
  create, update, delete, or sync any file.
- `apply`: perform the requested generation and policy update after reporting
  the plan. This is the normal mode when the user asks to generate or update
  agents without requesting preview or TOML-only output.
- `toml-only`: create or update only `.codex/agents/*.toml`; do not modify
  `AGENTS.md` or `.codex/config.toml`.

Natural-language equivalents are valid: “先预览不要修改”, “只生成 TOML”,
and “应用这个方案”. In `preview`, inspect existing files and compute the
same validation results as `apply`, but keep the operation read-only. If the
user requests `toml-only`, automatic delegation is disabled for that run.

### 2. Build a project profile

Collect only enough evidence to make role decisions:

- languages, frameworks, package managers, and build/test/lint commands;
- source, test, documentation, generated, and infrastructure directories;
- important boundaries such as frontend/backend, API/client, service/package
  ownership, or deployment/runtime separation;
- existing instructions about permissions, validation, branching, review, and
  files that must not be touched;
- current `.codex/agents` names and project-level `[agents]` defaults.

Use fast, targeted discovery (`rg --files`, manifest inspection, and focused
reads). Do not dump the entire repository into context.

### 3. Choose roles from actual parallel work

Start with a read-heavy role when the project has meaningful structure, then add
only roles justified by evidence. Common roles include:

- `project_explorer`: maps ownership, execution paths, conventions, and likely
  validation commands; read-only and evidence-focused. Prefer
  `gpt-5.6-terra` with `medium` when pinning a model is useful;
- `reviewer`: checks correctness, regressions, security, and test gaps; read-only
  unless the user explicitly requests a write-capable review workflow. Prefer
  `gpt-5.6` with `high` for complex review or security work;
- `test_runner` or `integration_debugger`: reproduces and diagnoses test or
  runtime failures using commands and configured browser/tooling. Use
  `gpt-5.6-terra` for straightforward scans and `gpt-5.6` when diagnosis spans
  multiple systems or requires substantial reasoning;
- `frontend_worker`, `backend_worker`, `data_worker`, or another domain worker
  only when the repository clearly contains that domain and the role has a
  distinct write scope. Prefer `gpt-5.6` with `medium` for demanding,
  multi-step implementation; use `gpt-5.6-luna` only for narrow, clear,
  repeatable work.

Do not create roles merely for naming symmetry. A role is warranted when its
instructions, evidence sources, tools, or validation loop differ materially from
another role. Keep implementation roles disjoint when parallel writes are
likely to collide. If there is no reliable evidence for a separate role, omit it
and explain the omission.

### 4. Choose models and reasoning using the official strategy

Follow the official Subagents guidance when a role needs pinned model settings:

- Start with `gpt-5.6` for most demanding or ambiguous agents that need planning,
  tool use, validation, and follow-through.
- Use `gpt-5.6-terra` for faster, lower-cost work such as exploration, read-heavy
  scans, large-file review, or processing supporting documents.
- Use `gpt-5.6-luna` only for fast, narrowly scoped, clear, repeatable, or
  high-volume work.
- Use `medium` as the balanced default reasoning effort, `low` for
  straightforward work, and `high` for complex logic, security, reviews, or
  edge cases. Use `xhigh`, `max`, or `ultra` only when the selected model and
  environment support them and the task justifies the extra cost and latency.
- This Skill pins the official role-based recommendation by default for newly
  generated agents, so the generated TOML makes the intended model strategy
  visible and reproducible. Omit `model` and `model_reasoning_effort` only when
  the user explicitly requests `inherit`, `auto`, dynamic selection, or no
  pinned model.

Never select a model merely to make a file look complete. When a model or effort
is pinned, record why in the handoff and verify that the selected model supports
the requested reasoning effort.

Before writing a pinned model, check the active environment's model capability
catalog when one is available. Verify both the model identifier and the
requested reasoning effort. If the catalog is unavailable, report the model as
unverified; do not claim that the environment supports it. If a user explicitly
selects a model or effort that is absent or unsupported, stop before writing and
report the exact unsupported value. Do not silently substitute another model.

For an official default that is unavailable, choose a currently available model
with the same intended role characteristics only when the user has not pinned a
model, and report the substitution and its rationale. Preserve `inherit`/`auto`
requests by omitting the corresponding fields.

### User overrides

The user may customize the model policy during generation. Treat explicit user
choices as intentional overrides of the official defaults, while still checking
that the requested values are supported:

```text
Model policy:
- default: gpt-5.6-terra / medium
- reviewer: gpt-5.6 / high
- backend_worker: gpt-5.6 / medium
- project_explorer: inherit
```

Also accept equivalent natural-language requests such as “use gpt-5.6 high for
the reviewer and let the explorer inherit.” Resolve generation-time choices in
this order:

1. an explicit per-agent user override;
2. an explicit user default for otherwise unspecified agents;
3. the official role-based strategy above;
4. omitted fields only when the user explicitly requests normal Codex
   inheritance or dynamic selection.

This order decides what the Skill writes into each custom-agent TOML. It is not
the runtime configuration precedence. At runtime, Codex first resolves a base
model and reasoning effort from an explicit spawn value, then the corresponding
`[agents]` default, then the parent session. It then applies the selected custom
agent file as a configuration layer. A `model` or `model_reasoning_effort`
present in that file overrides the corresponding base value.

`inherit`, `auto`, or an explicit request not to pin a role means omit that
role's `model` and `model_reasoning_effort` fields. A partial override is valid:
the user may set only `model` or only `model_reasoning_effort`. The omitted field
keeps the previously resolved base value. In particular, a custom agent file
that sets only `model` preserves the already resolved reasoning effort; verify
that the selected model supports it. Do not silently replace an unavailable
user-selected model or effort. Report the unsupported value and ask for a
fallback, or use the official strategy only after the user authorizes that
fallback.

In the final handoff, show the declared selection and its generation-time source
for every generated role, for example `reviewer → gpt-5.6/high (user override)`
or `project_explorer → inherited (user requested auto)`. Call it effective only
when runtime metadata independently confirms the applied values.

### 5. Write each custom agent file

Create `.codex/agents/<filename>.toml` with:

- `name`: the stable identifier used when spawning the agent;
- `description`: one sentence describing when the parent should use it;
- `developer_instructions`: concise, role-specific behavior and boundaries.

Optionally set `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`,
or `skills.config` only when the project evidence and user intent justify them.
Apply the official model strategy in the preceding section; otherwise inherit
the parent or project defaults.

Every `developer_instructions` value should cover the following, adapted to the
role:

1. mission and explicit non-goals;
2. allowed tool and file surface;
3. evidence standard (file paths, symbols, commands, logs, or reproduction
   steps);
4. write scope, if any, including files/directories the agent must leave alone;
5. validation commands appropriate to the changes;
6. handoff format: concise findings, changed files, validation results, and
   unresolved risks for the parent agent.

Use TOML multiline strings for instructions. Keep them actionable and specific
to this project; do not paste all repository guidance into every agent.

Treat TOML values as declared settings, not as proof of runtime behavior.
Before relying on a custom role, identify whether the available launcher can
select a project agent by an explicit role/type. If the launcher only accepts a
free-form prompt or generic subagent request, it cannot be treated as having
loaded a project TOML merely because the prompt names that role. Use a launcher
that supports the exact TOML `name`, or report role binding as unverified.

### 6. Install the automatic delegation policy

This Skill supports automatic delegation as a project behavior. The generated
`.codex/agents/*.toml` files define roles; they do not, by themselves, cause
Codex to start subagents. To make delegation persistent for future tasks,
maintain a managed policy block in the repository root `AGENTS.md`.

Unless the user explicitly says to generate agent files only, install the
policy. If the user asks for automatic delegation, delegation policy, or
automatic subagent routing, enable it by default. The user can explicitly turn
it off with requests such as “不要自动委派” or “只生成 TOML，不修改
AGENTS.md”.

Build the block from the actual generated and retained agent names. Never
reference a role whose `.toml` file does not exist, and never invent a role at
runtime. Use this exact marker pair:

```md
<!-- BEGIN generate-project-subagents: delegation-policy -->
...
<!-- END generate-project-subagents: delegation-policy -->
```

If the block already exists, replace only that block. Otherwise append it to
the root `AGENTS.md`, preserving the file's existing ending and adding a blank
line before the block when needed. If the file does not exist, create it with
the block and report that a new project instruction file was created.

The generated policy should express only the applicable rules below, using the
actual role names and scopes discovered in this run:

- Do not delegate trivial, single-file, or purely conversational tasks.
- For a broad or ambiguous task, use the generated explorer role first when it
  exists (for example, `project-explorer`); always use its exact TOML `name`.
  Pass its findings to the parent before implementation.
- For independent frontend and backend work, use the generated frontend and
  backend roles in parallel (for example, `frontend-worker` and
  `backend-worker`) only when both exist and their write scopes are disjoint.
  Adapt these rules to other domain workers when the project has different
  boundaries, and use each role's exact TOML `name`.
- When a task matches a configured role, spawn the custom agent by the exact
  TOML `name` value. Do not replace a matching custom agent with an untyped or
  generic subagent. “Automatic” means the parent chooses the role without the
  user naming it; it does not mean the spawn may omit the role.
- After each role-specific spawn, verify the effective `agent_role` or
  `agent_path` when the runtime exposes it, together with the effective model,
  reasoning effort, and sandbox mode. If the runtime does not expose those
  values, require the child handoff to report them and mark the configuration
  unverified when they cannot be confirmed. Never claim that a custom TOML was
  applied based only on a child thread appearing in the UI.
- Distinguish three states in the handoff: `declared` (the TOML parses and
  contains the value), `role-bound` (the launcher selected the exact TOML
  `name` or path), and `effective` (the runtime reports the value actually in
  force). A declared `sandbox_mode = "read-only"` is not effective evidence
  when the child actually runs with `workspace-write`.
- If the effective sandbox is broader than the TOML declaration, stop treating
  the role as read-only, do not broaden its task to compensate, and report the
  outer-runtime override. Do not weaken a TOML sandbox declaration merely to
  make it match an unverified launcher.
- After write-capable work, use `reviewer` when it exists and wait for the
  review before the parent summarizes completion. Use a test/debug role only
  when the task involves failing tests or runtime diagnosis and that role
  exists.
- Do not start every agent for every task. Delegate only the smallest set of
  roles that materially reduces risk or elapsed time.
- Give each subagent a bounded objective, allowed paths, evidence expected,
  validation command, and handoff format. Do not assign overlapping writes;
  the parent owns integration and conflict resolution.
- Wait for all requested subagents before finalizing. The parent remains
  responsible for applying findings, running the final project checks, and
  reporting unresolved risks.
- A direct user instruction overrides this policy. If the user says not to
  delegate, do not spawn subagents. Preserve a user's explicit model or
  reasoning-effort choice when generating or updating the selected agent TOML.
  At runtime, do not claim that an explicit spawn value overrides a value pinned
  in that TOML: the custom-agent file is applied afterward and takes precedence.
  To honor a different user-requested value, update the TOML with authorization
  or use a role that leaves the corresponding field unpinned.

The policy must state that automatic delegation is conditional and model-led:
it is a routing instruction, not a promise that every task launches a thread.
Do not add global `.codex/config.toml` settings merely to install this policy.

### 7. Add global settings only when requested

Do not create or edit `.codex/config.toml` automatically just because multiple
agents were generated. If the user explicitly wants orchestration defaults,
make the smallest scoped change under `[agents]`, such as a concurrency cap or a
default subagent model, and preserve unrelated settings. For the base model and
reasoning resolution, an explicit spawn value takes precedence over the
corresponding `[agents]` default, and that default takes precedence over the
parent value. Codex then applies the selected custom-agent TOML; any `model` or
`model_reasoning_effort` in that file overrides the corresponding base value.
Do not present a spawn override as a way to replace a value pinned in the
custom-agent TOML.

### 8. Validate before handoff

For each generated or updated file, verify:

- valid TOML syntax;
- required fields are present and non-empty;
- `name` values are unique and match the intended role;
- filenames are stable lowercase kebab-case where practical;
- sandbox and write permissions do not exceed the described task;
- no command, path, MCP server, model, or framework is unsupported by the
  project evidence;
- pinned model and reasoning settings follow the official model-selection
  strategy and are supported by the active environment;
- roles do not have overlapping write scopes without an explicit coordination
  rule;
- instructions do not contradict root or nested project guidance.
- if automatic delegation is enabled, the managed `AGENTS.md` block references
  only existing agent names, has no duplicate marker pair, preserves content
  outside the block, describes conditional routing rather than mandatory
  delegation for every task, and requires exact-name custom-agent spawning for
  matching roles.

Use an available TOML parser or the project's own validation tooling. Review the
diff and report exactly which files were created, updated, or intentionally left
unchanged. If a parser or required project command is unavailable, state that
limitation instead of claiming validation succeeded.

For an end-to-end delegation test, capture a runtime report from the host or
launcher and compare it with the generated TOML. The bundled validator accepts
`--runtime-report <path>`; add `--require-runtime-report` when the test must
fail if role, model, reasoning effort, or sandbox provenance is missing. A
runtime report is independent evidence only when it comes from the
launcher/host; values copied from a child handoff remain self-reported and
must be labeled as such.

When this Skill's validator is available, run it in read-only mode:

```bash
python3 /path/to/generate-project-subagents/scripts/validate_generated_agents.py \
  /path/to/project
```

If the active environment exposes a capability map, pass it with
`--capabilities /path/to/capabilities.json`. Use `--require-capabilities` when
the user requires proof that every pinned model and reasoning effort is
available. Use `--strict-names` when the project requires filename stems to
match the TOML `name` exactly. Use `--runtime-report /path/to/runtime.json` to
compare an end-to-end launcher report with the TOML, and
`--require-runtime-report` when missing runtime fields must fail validation. A
validation warning about an unavailable capability or missing runtime
provenance is not evidence of support; report it as unverified.

## Suggested handoff shape

Return:

1. the generated role table (`name`, purpose, sandbox/write mode, validation);
2. files created or changed, with absolute paths when available;
3. the project evidence that drove role selection;
4. validation performed and its result;
5. any follow-up needed, especially approval before overwriting existing agents
   or configuring global concurrency.

For `preview`, return the proposed role table, model capability status, policy
diff, and validation results, and explicitly state that no files were changed.
