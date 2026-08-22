# Pre-N Probe Transcript (August 21, 2026)

Environment: Cowork sandbox, fresh clone of github.com/metricminellc/metricmine at head 2bbf4b3 (v0.1.0). uv 0.8.17; CPython 3.12.3 for resolution probes. anthropic SDK probed at 1.0.0 (released 2026-08-20) in an isolated venv with jsonschema 4.x and pyyaml. No API key present: every probe below is offline by design; the live smoke call is Probe P3 on the Mac.

## Probe P1: dependency resolution against the committed lock

```
$ uv add --no-sync "anthropic>=1.0,<1.1"
Using CPython 3.12.3 interpreter at: /usr/bin/python3.12
Resolved 207 packages in 3.30s
exit=0
$ git diff --stat
 pyproject.toml |   1 +
 uv.lock        | 105 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
$ packages added to uv.lock: anthropic 1.0.0, httpcore2, httpx2 2.12.0, httpx2-jsfetch, jiter, sniffio, truststore
$ anthropic 1.0.0 dependencies: anyio, docstring-parser, httpx2, jiter, pydantic, sniffio, typing-extensions
$ httpx stays at 0.28.1 for the existing graph; httpx2 sits beside it (no conflict; F-22 class does not recur)

$ git checkout pyproject.toml uv.lock && uv add --no-sync "anthropic>=0.125,<1"   # recorded fallback line
Resolved 204 packages in 443ms  -> anthropic 0.125.0
```

## Probe P2: SDK surface at 1.0.0 and the proposal-schema projection

```
anthropic 1.0.0
MessageCreateParams keys: ['max_tokens', 'messages', 'model', 'cache_control', 'container', 'inference_geo', 'metadata', 'output_config', 'service_tier', 'stop_sequences', 'system', 'thinking', 'tool_choice', 'tools', 'user_profile_id']
OutputConfigParam.effort: Optional[Literal['low', 'medium', 'high', 'xhigh', 'max']]
OutputConfigParam.format: Optional[JSONOutputFormatParam]
JSONOutputFormatParam: {'schema': 'Required[Dict[str, object]]', 'type': "Required[Literal['json_schema']]"}
temperature/top_p/top_k present in MessageCreateParams: False
$ .venv/bin/python probe_schemas.py
1. frozen schema: transform_schema RAISED ValueError: Schema must have a 'type', 'anyOf', 'oneOf', or 'allOf' field.
2. mapping proposal schema: transform_schema OK; optional params=0 (limit 24); unions=0 (limit 16)
   transform changed the schema: False
3. rendered mapping proposal validates against the FROZEN schema: OK
   groundedness vs silver v0001: referenced=9 missing=[]
   profile content_hash field present: sha256:e65bee811...; schema_version=1.0.0
   negative case: hallucinated column caught by groundedness = ['region']
   first-class elements equal to committed v1.1.0: header=True fields=True
4. silver cleanup proposal schema: transform_schema OK; optional params=0 (limit 24); unions=0 (limit 16)
schemas written to /tmp/sdkprobe/*.schema.json
```

## Probe P2b: the headered schema files and the example proposals

The two schema drafts were renamed to their spec paths
(`docs/spec/agent-layer/gold-mapping-proposal.schema.json`,
`docs/spec/agent-layer/silver-cleanup-proposal.schema.json`) and given the
engine precedent's `$schema`, `$id`, `title`, and `description` header. The
probe script was renamed `2026-08-21_preN_probe_schemas.py` and made
repo-relative so it reruns from `docs/verification/evidence/`. Re-measured:

```
gold-mapping-proposal.schema.json   | Draft 2020-12 meta-valid | transform_schema OK with header | keyword scan clean | example-gold-mapping-proposal.json validates
silver-cleanup-proposal.schema.json | Draft 2020-12 meta-valid | transform_schema OK with header | keyword scan clean | example-silver-cleanup-proposal.json validates
top-level keys after transform_schema: ['type', 'description', 'title', 'properties', 'additionalProperties', 'required']
```

CORRECTION (re-measured later the same day): `transform_schema` does not
drop `$schema` and `$id`; it RELOCATES them, appending
`{$schema: ..., $id: ...}` to the top-level `description` text, and leaves
everything else byte-identical. Stripping the two keys BEFORE the call makes
the transform an exact identity (measured True for all three proposal
schemas). The harness therefore strips first, then transforms; the CI test
asserts identity on the stripped schema and non-identity on the unstripped
one, pinning the order. Keyword scan
rule, for the CI test: no `oneOf`, `allOf`, `anyOf`, `if`, `then`, `else`,
`contains`, `minContains`, `maxContains`, `pattern`, `patternProperties`,
`propertyNames`, or `not`; every `enum` typed `string`; every object
`additionalProperties: false` with every declared property required.

Not probed here, by design: the live call. Probe P3 runs on the Mac at
Session N Stage 1 with the key in the environment.
