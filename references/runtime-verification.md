# Runtime verification

Use this checklist when testing generated project agents end to end. Static
TOML validation proves only that a declaration is well formed. It does not
prove that a launcher selected the custom role or applied its settings.

## Required evidence

Capture one record for each role tested. The bundled validator accepts either a
JSON array or an object with an `agents` array:

```json
{
  "agents": [
    {
      "agent_role": "project-explorer",
      "agent_path": "/absolute/project/.codex/agents/project-explorer.toml",
      "model": "gpt-5.6-terra",
      "reasoning_effort": "medium",
      "sandbox_mode": "read-only"
    }
  ]
}
```

The values must come from the launcher/host's runtime metadata to count as
independent evidence. A child saying “I used model X” in its own prompt is
self-reported and should be labeled that way; it is useful for diagnosis but
does not prove provenance.

## Interpretation

Check the fields in order:

1. `declared`: the TOML has the expected fields and parses;
2. `role-bound`: `agent_role` or `agent_path` identifies the exact TOML file;
3. `effective`: model, reasoning effort, and sandbox match the TOML.

Any mismatch is a runtime configuration failure, even when the child follows
the written instructions. In particular, `workspace-write` is not equivalent
to `read-only`. If an outer session or host policy broadens the sandbox, keep
the role marked unverified/not applied and do not assign it a task that relies
on read-only enforcement.

## Validator commands

Static validation:

```bash
python3 /path/to/validate_generated_agents.py /path/to/project
```

End-to-end validation, requiring all effective fields:

```bash
python3 /path/to/validate_generated_agents.py /path/to/project \
  --runtime-report /path/to/runtime.json \
  --require-runtime-report
```

The strict form fails for a missing role/path, a missing effective field, or a
value that differs from the corresponding TOML. Use the non-strict report mode
when a launcher exposes only partial metadata, but report missing values as
unverified rather than as inherited or applied.

## Launcher compatibility rule

An automatic delegation policy can tell the parent which role to choose, but it
cannot add an `agent_type`/role parameter to a launcher that does not support
one. A generic spawn API that accepts only a prompt and optional model or
reasoning overrides must be treated as unable to prove custom-agent loading.
Use a launcher that supports exact-name custom-agent selection, or stop at the
role-bound verification step and report the compatibility gap.
