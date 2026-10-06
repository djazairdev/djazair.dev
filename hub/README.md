# hub

The Project Hub (PRD §8). Python 3.12+, standard library only.

```sh
python3 -m hub check-registry   # validate projects.yml against hub/projects.schema.json
```

## Registry

[`projects.yml`](../projects.yml) lists the projects, one entry each: `repository`, `category`, `tags`, `maintainer_pledge` and `added` (PRD HUB-01). Language, licence and activity are read from GitHub, so they aren't stored. [CONTRIBUTING.md](../CONTRIBUTING.md#list-a-project-in-the-hub) explains each field and lists the tags.

| File | What it does |
|---|---|
| `projects.schema.json` | The JSON Schema for `projects.yml`. Editors with a YAML language server use it while you type |
| `registry.py` | Reads `projects.yml`, checks it against the schema, then checks what a schema can't: a repository listed twice (GitHub names ignore case) and a date in the future |
| `miniyaml.py` | A strict reader for the part of YAML the registry uses. Anything else (anchors, tags, block scalars, tabs, duplicate keys) is an error with its line number |
| `schemacheck.py` | Applies the JSON Schema keywords the schema uses, and refuses a schema that uses any other, so no check is silently skipped. Errors name the field (`projects[2] (owner/name).category`) and say what to write instead |

CI runs `python -m hub check-registry` on every pull request. In GitHub Actions each problem is also an annotation on the line to fix.

Still to come: the inclusion checks on submissions (#16), the issues feed refreshed every 6 hours (#25) and the daily health checks (#26).
