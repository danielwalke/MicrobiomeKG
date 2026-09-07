# MicrobiomeKG Pipeline — State of the Art

Snapshot of how the pipeline is architected and exactly how far the
implementation currently reaches. Written after getting Stage 1 (raw graph)
runnable end to end; stages 2-6 are still dormant.

## Architecture in one paragraph

The pipeline is not "six containerized compute steps" — it's **six containerized
graph snapshots**, glued together by host-side Python. Each stage's
`docker-compose.yml` starts nothing but a Neo4j database holding that stage's
version of the graph. The actual transform logic (`main.py` per stage) runs on
the **host**, connects to whichever Neo4j container is currently up over bolt,
mutates it with Cypher, and then physically copies the resulting Neo4j `data`
directory forward into the next stage's directory via `src/utils/clone_kg.py`
— which is how the graph moves from stage to stage. `run_pipeline.sh`
orchestrates this: bring the right container up, wait for it, run that
stage's `main.py` against it, move on.

## Orchestration: `run_pipeline.sh`

- `run_stage(module_name, desktop_port, meta_desktop_port)`: cds into
  `src/<stage>`, runs `docker compose up -d`, waits for the Neo4j HTTP port to
  respond, cds back to the repo root, then runs
  `PYTHONPATH=. python3 -m <module>.main`.
- Metagraph containers are currently **disabled**: the
  `docker compose -f meta-docker-compose.yml up -d` call and its matching
  `wait_for_neo4j $meta_desktop_port` are commented out, as is the metagraph
  port argument in the stage-1 invocation. Metagraphs are parked, not removed.
- Fixed this session: the script previously `cd`'d into
  `.../NCBI_Taxon_Ambiguity_Und_Enzyme_Pipeline$dir_path` — a concatenation
  missing a path separator that pointed at a directory that doesn't exist —
  and sourced a `.env` at that same stale location, which also didn't exist.
  Both now point at the real repo layout (`/home/ubuntu/MicrobiomeKG`), and
  `.env` lives at the repo root (gitignored).
- Only Stage 1 is uncommented and wired to run; stages 2-6 remain commented
  invocations at the bottom of the script, unimplemented beyond their
  pre-existing `docker-compose.yml`/`meta-docker-compose.yml` files.

## Stage 1 — raw graph (the one stage that's different)

Every other stage's container is a stock `neo4j:latest` image waiting to be
filled by host-side Cypher. Stage 1 is the exception: its graph is *produced*
by **BioDWH2**, a Java tool with its own lifecycle (create workspace → add
data sources → update/download → build Neo4j server → start), not something
that starts empty. That lifecycle is what `src/s1_raw_graph/Dockerfile` and
`entry_point.sh` wrap:

- **`Dockerfile`**: `eclipse-temurin:17-jre` base (adjust if BioDWH2 needs a
  different JDK/JRE version), installs `wget` (needed for the compose
  healthcheck), copies both shell scripts in. It no longer `COPY`s the
  BioDWH2 jar — that's bind-mounted at container start instead (see below),
  since `COPY` can only reach files inside the build context
  (`src/s1_raw_graph/`), and the jar lives elsewhere on the host.
- **The BioDWH2 jar is bind-mounted, not baked into the image**:
  `docker-compose.yml` mounts `${RAW_BIODWH2_GRAPH_JAR_PATH}` (a host path,
  set in `.env`) to `/app/BioDWH2-Neo4j-Server-v1.3.2.jar`. This was chosen
  over `COPY` specifically so a freshly-downloaded jar can be dropped in and
  picked up with a container restart, no image rebuild required — matching
  the planned future step of automating the jar download itself.
- **`entry_point.sh`**: only the `--start "$WORKSPACE"` command is active.
  The create/configure-sources/update/create-db steps are written but
  commented out, since for now a pre-built BioDWH2 workspace is supplied
  externally rather than assembled by the container itself.
- **`docker-compose.yml`**: builds that Dockerfile, publishes
  `RAW_GRAPH_DESKTOP_PORT`/`RAW_GRAPH_BOLT_PORT`, and bind-mounts
  `${RAW_GRAPH_DIR}` (the host's pre-built workspace,
  e.g. `/mnt/vdb/benja/TrEMBL_Instance_Node_Mapping`) to
  `/app/workspaces/test_workspace` — exactly the path `entry_point.sh`'s
  `--start` expects.
- The four scripts that automate the *creation* half of BioDWH2's lifecycle
  (`create_workspace.sh`, `update_workspace.sh`, `create_db_from_workspace.sh`,
  `start_db_from_workspace.sh`) exist but live in
  `not_implemented_or_used_yet/` — not wired into the Dockerfile flow yet.

### The workspace-layout gap (found and fixed this session)

A BioDWH2 workspace is a *superset* of what other stages mount — it also
carries `config.json`, per-source raw/parsed dumps under `sources/`, and
`tools/`, none of which are Neo4j data. The actual Neo4j database lives
nested inside it, at `<workspace>/neo4j/neo4j.db/{data,logs}` — not at
`<workspace>/data` the way a plain `neo4j:latest` container's directory is
laid out. `clone_kg()`'s auto-detection only checks one level down
(`<source>/data`), so pointing it at the workspace root silently fails that
check and falls through to copying the *entire workspace* (raw source dumps
included) into stage 2's directory instead of just the database.

Fix applied in `main.py`: only the **source** side of the stage 1→2 clone
needs the BioDWH2-specific nested path; the **target** stays the plain layout
every other stage already expects, since stage 2 onward are back to vanilla
`neo4j:latest`.
```python
clone_kg(raw_graph_dir + "/neo4j/neo4j.db", mapped_graph_dir)
```

### NCBI merged-taxonomy resolution

`main.py`'s primary operation for stage 1: standardizes each configured
database's NCBI taxid property name, then resolves NCBI's *merged* taxonomy
IDs (taxa NCBI has since merged into another ID) against `merged.dmp`,
via `AmbiguityNCBI.py`. `merged.dmp` is already committed at
`src/s1_raw_graph/merged.dmp`; `load_ncbi_taxon_merged.sh` (copied into the
image but not yet invoked from `entry_point.sh`) can (re-)download it from
NCBI's taxdump archive straight into the mounted workspace
(`/app/workspaces/test_workspace/merged.dmp`) so it lands back on the host at
`${RAW_GRAPH_DIR}/merged.dmp`, rather than into the container's own throwaway
filesystem where the host-side `main.py` could never see it.

## Stages 2-6

Unimplemented beyond scaffolding: each has a `docker-compose.yml` (plain
`neo4j:latest` + `data`/`logs`/`conf`/`import` volumes) and
`meta-docker-compose.yml` already in place, matching the naming convention
`${STAGE}_GRAPH_{DESKTOP,BOLT}_PORT` / `${STAGE}_GRAPH_DIR`. Their `main.py`
modules and their invocations in `run_pipeline.sh` are not yet written/enabled.

## Known gaps / open items

- **`.env` values for stages 2-6 are placeholders** (`TODO` markers) — real
  host directories and free ports need to be filled in before uncommenting
  those stages in `run_pipeline.sh`.
- **`RAW_GRAPH_USERNAME`/`RAW_GRAPH_PASSWORD` are unverified** — BioDWH2-Neo4j-Server's
  actual default/configured auth hasn't been confirmed against the real
  workspace; the metagraph containers use `NEO4J_AUTH=none`, but that's a
  stock-image convenience that BioDWH2's own server may not replicate.
- **`RAW_BIODWH2_GRAPH_JAR_PATH` in `.env` must point at a real jar on the
  host** — currently `/mnt/vdb/benja/BioDWH2_Projekts/BioDWH2-Neo4j-Server-v1.3.2.jar`, confirmed
  present. Watch for stray whitespace around `=` in `.env` assignments: a
  `VAR= value` (space before the value) is silently parsed by bash as
  "set `VAR` empty, then execute `value` as a command" — which crashed
  `run_pipeline.sh` (it runs under `set -e`) the one time this slipped in.
- **BioDWH2 source configuration isn't automated** — `entry_point.sh`'s
  create/update block is commented out and, when re-enabled, still needs a
  non-interactive way to declare which databases to pull in (confirm BioDWH2's
  actual mechanism — a `sources.json`-style file or CLI flag — before wiring
  it up).
- **Metagraphs are fully parked** — disabled in both `run_pipeline.sh` and
  `main.py`; re-enabling means uncommenting both, not just one.
- **`clone_kg`'s single-level `data` detection is BioDWH2-blind by design** —
  the fix lives in stage 1's `main.py` call site, not in the shared utility,
  so any future stage with a similarly non-flat source layout will need the
  same treatment at its own call site.
