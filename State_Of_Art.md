# MicrobiomeKG Pipeline — State of the Art

Snapshot of how the pipeline is architected and exactly how far the
implementation currently reaches. Rewritten after replacing the old
per-stage `docker-compose.yml` + `run_pipeline.sh` orchestration with a
single `pipeline-docker-compose.yml`, and getting Stage 1 (raw graph)
running end to end under it. Stages 2-6 are still dormant.

## Architecture in one paragraph

The pipeline used to be "six containerized graph snapshots glued together by
a host-side bash script + host-side Python" (`run_pipeline.sh` cd'ing into
each stage's own `docker-compose.yml`, then running that stage's `main.py`
directly on the host). It is now **one compose file**,
`pipeline-docker-compose.yml` at the repo root, with one service per
pipeline step. Each stage still produces a Neo4j snapshot that the next
stage picks up, but the "glue" — starting the right containers, waiting for
health, running that stage's `main.py` — is now expressed as ordinary
compose `depends_on`/`condition: service_healthy` relationships instead of a
shell script polling ports. `run_pipeline.sh`, its per-stage
`docker-compose.yml`/`Dockerfile`/`entry_point.sh` files, `env_config.md` and
`raw_command_list.md` have all been moved into `residual_code/` — kept for
reference, no longer part of the active flow.

Only Stage 1 is implemented under the new model so far. Stages 3-6 are
explicitly out of scope for now; Stage 2 needs its own `Dockerfile` (not yet
written) mirroring Stage 1's pattern.

## `pipeline-docker-compose.yml`

One `services:` block, split into a co-dependent group (stages that depend
on each other's containers being up) and an independent group (stages that
only need a directory of already-cloned Neo4j data, no other running
container):

```yaml
services:
  #s0_BioDWH2_service:      # placeholder — see below, do not touch
  s1_BioDWH2_neo4j_service:  # implemented
  s1_NCBI_taxonomy_service:  # implemented
  #s2:                       # placeholder — needs its own Dockerfile, not started this round
```

`s0_BioDWH2_service` and `s2` are currently commented out on disk so that
`docker compose` only ever sees the two working Stage 1 services; nothing
about the file's syntax requires that, it's just what's actively being
tested right now.

### `s0_BioDWH2_service` — parked, deliberately untouched

Meant to eventually run BioDWH2's own `--update` step (downloading/refreshing
the source databases that make up the raw graph) as its own service, before
`s1_BioDWH2_neo4j_service` even starts. Not implemented — left as a bare
placeholder key with a comment. Whoever picks this up next should know a
previous step is expected to exist here; the two `s1_*` services below
assume a workspace has *already* been built by the time they run.

### `s1_BioDWH2_neo4j_service` — stock `neo4j:latest`, no build

This one surprised us during setup: it is **not** a custom image running the
BioDWH2 jar. BioDWH2's own Neo4j-Server jar bundles its own embedded Neo4j,
so at first glance it looks like this service needs the same
`eclipse-temurin` + `java -jar BioDWH2-Neo4j-Server*.jar --start` pattern the
old Stage-1 Dockerfile used. It doesn't, because by this point BioDWH2 has
already *built* the workspace's Neo4j store on disk — all this service needs
to do is serve that already-built store, which a plain `neo4j:latest`
container can do directly by mounting the store's `data`/`logs` folders at
its own expected `/data`/`/logs` mount points:

```yaml
  s1_BioDWH2_neo4j_service:
    image: neo4j:latest
    user: "1000:1000"   # matches the host user owning RAW_GRAPH_DIR
    ports:
      - "${RAW_GRAPH_DESKTOP_PORT}:7474"
      - "${RAW_GRAPH_BOLT_PORT}:7687"
    volumes:
      - ${RAW_GRAPH_DIR}/neo4j/neo4j.db/data:/data
      - ${RAW_GRAPH_DIR}/neo4j/neo4j.db/logs:/logs
    environment:
      NEO4J_AUTH: none
```

This mirrors a manually-validated `docker run` command (still sitting at
`/mnt/vdb/benja/mapped_graph/test_daniel_startup.sh` from earlier testing) —
no APOC plugin, no auth, `--user` set to the host uid/gid that already owns
the BioDWH2 workspace files on disk (not the neo4j image's default uid,
`7474`). The nested `neo4j/neo4j.db/data` path (two levels below the
workspace root) is BioDWH2's own layout, not Neo4j's — a plain
`neo4j:latest` container elsewhere in the pipeline expects `data` directly at
its mount root, but here we're reaching two levels into a BioDWH2 workspace
to find it.

**Gotcha confirmed working, but easy to trip over:** the official
`neo4j:latest` image does ship `wget` (verified via
`docker run --rm --entrypoint sh neo4j:latest -c "which wget"`), which is
what the healthcheck below relies on — if a future base image swaps that
out, the healthcheck will silently never pass and anything with
`depends_on: condition: service_healthy` on this service will hang forever
waiting for it.

```yaml
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 40s
```

**Known real conflict to watch for:** a manually-started test container
(`DanielsTest`, from that same `test_daniel_startup.sh`) mounts this exact
same `data`/`logs` pair. Neo4j takes an exclusive lock on its store
directory, so if `DanielsTest` (or any other container) is still holding
those files open, `s1_BioDWH2_neo4j_service` will fail to start. Always
`docker stop DanielsTest` (or whatever else has that store mounted) before
bringing the pipeline compose stack up.

### `s1_NCBI_taxonomy_service` — runs `src/s1_raw_graph/main.py` for real

This service builds a small `python:3.12-slim` image
(`src/s1_raw_graph/ncbi-taxonomy.Dockerfile`) and its entrypoint
(`src/s1_raw_graph/entrypoint.sh`) runs the actual stage-1 pipeline —
`python3 -m src.s1_raw_graph.main` — not a stripped-down script that only
calls `AmbiguityNCBI.py` directly. An earlier draft of this entrypoint did
exactly that (bypassing `main.py` entirely), which meant "every update from
s1 stage" that `main.py` is supposed to run wasn't actually happening; this
was caught and corrected.

```yaml
  s1_NCBI_taxonomy_service:
    image: s1-ncbi-taxonomy-service   # see the naming gotcha below
    build:
      context: /mnt/vdb/benja/MicrobiomeKG          # repo root, not src/s1_raw_graph
      dockerfile: src/s1_raw_graph/ncbi-taxonomy.Dockerfile
    user: "1000:1000"
    depends_on:
      s1_BioDWH2_neo4j_service:
        condition: service_healthy
    volumes:
      - ${RAW_GRAPH_DIR}:${RAW_GRAPH_DIR}:ro
      - ${MAPPED_GRAPH_DIR}:${MAPPED_GRAPH_DIR}
    env_file:
      - .env
    environment:
      RAW_GRAPH_BOLT_URI: bolt://s1_BioDWH2_neo4j_service:7687
```

Running the real `main.py` (rather than a bypass) surfaced two non-obvious
problems, both worth understanding rather than just accepting the fix:

**1. Build context had to move to the repo root.** `main.py` imports
`from src.utils.migrate_metagraph import migrate_metagraph` and
`from src.s1_raw_graph.AmbiguityNCBI import (...)` — these are namespace-package
imports (there's no `__init__.py` anywhere in this repo; Python 3 handles
that fine as long as the package root is on `PYTHONPATH`) that assume the
*whole* `src/` tree is present, exactly like they do when run on the host
via `PYTHONPATH=. python3 -m src.s1_raw_graph.main`. Building from
`src/s1_raw_graph/` alone (the original draft) can't reach `src/utils/` at
all — Docker's build context is a hard boundary, it cannot `COPY` from
outside it. So the Dockerfile now builds from the repo root and copies in
only the specific files that are actually needed
(`src/utils/migrate_metagraph.py`, plus `s1_raw_graph`'s own
`AmbiguityNCBI.py`/`main.py`/`databases.txt`/`merged.dmp`/`entrypoint.sh`),
setting `ENV PYTHONPATH=/app` and `WORKDIR /app` so the import paths resolve
identically to the host invocation.

**2. `main.py`'s own clone step couldn't run inside a container as-is — and
the reason isn't obvious from just "the import failed".** `main.py`'s last
step used to call `src.utils.clone_kg.clone_kg(...)`. That function doesn't
copy files directly in Python — every actual file operation (wipe, copy,
lock cleanup) is delegated to a **brand-new sibling container** it spins up
itself via `subprocess.run(["docker", "run", ...])`, specifically so the copy
runs as uid `7474` (a stock `neo4j:latest` container's default user).
Copying `clone_kg.py` into the image would have fixed the *import* (it only
needs stdlib), but not the underlying problem: calling it from inside a
container requires (a) the `docker` CLI installed in the image, (b)
`/var/run/docker.sock` bind-mounted in so that CLI can reach the *host's*
Docker daemon, and (c) every path handed to `docker run` to be a real,
identical path on the **host** filesystem — because the sibling container is
created by the host's daemon, which has no idea what `/app/input/data`
means inside *our* container. Getting all three right would also mean
granting this container host-level Docker control just to copy a directory.
Given `s1_BioDWH2_neo4j_service` now runs as the host's own uid anyway (not
`7474`), the uid-translation `clone_kg()` existed for doesn't even apply
here. So `main.py`'s call site was changed (with the user's explicit
go-ahead, and `src/utils/clone_kg.py` itself left untouched for whatever
else may still use it) to a new `clone_raw_graph_data()` helper that does a
plain in-process `shutil.copytree` + lock-file cleanup — no subprocess, no
socket, no path-translation puzzle, since both directories are already
bind-mounted straight into the container.

That in turn shaped how the volumes are mounted: `RAW_GRAPH_DIR` and
`MAPPED_GRAPH_DIR` are bind-mounted at their own **literal host paths**
(`${RAW_GRAPH_DIR}:${RAW_GRAPH_DIR}:ro`), not remapped to something like
`/app/input` the way an earlier draft had it. That way `main.py`'s existing
`os.getenv("RAW_GRAPH_DIR")` / `os.getenv("MAPPED_GRAPH_DIR")` calls resolve
correctly with zero path-mapping logic added — the same env var means the
same real directory whether `main.py` runs on the host or in this container.

**Two `.env`/compose mechanics that caused real confusion while wiring this
up, worth remembering for the next stage:**

- `${VAR}` appearing directly in the compose YAML (e.g. in a `volumes:`
  line) is substituted by `docker compose` itself, from `.env`, as plain
  text — *before* any container exists. `s1_BioDWH2_neo4j_service` needs no
  `environment:`/`env_file:` block for `RAW_GRAPH_DIR` for exactly this
  reason: the substitution already happened by the time the container
  starts, and the neo4j process itself never calls `os.getenv(...)`. This is
  a completely different mechanism from `environment:`/`env_file:`, which
  controls what a process *running inside* the container sees via
  `os.getenv(...)`/`$VAR`. `s1_NCBI_taxonomy_service` needs the latter
  (`env_file: - .env`, plus an `environment:` override for
  `RAW_GRAPH_BOLT_URI` specifically, since `.env`'s stored value
  `bolt://localhost:...` is only correct for host-side runs — inside the
  compose network it has to be `bolt://s1_BioDWH2_neo4j_service:7687`,
  the other service's compose service name, not `localhost`) precisely
  because `main.py` genuinely calls `os.getenv("RAW_GRAPH_DIR")` etc. at
  runtime.
- Docker image names must be all-lowercase. When a service has a `build:`
  block but no explicit `image:`, Compose auto-names the built image
  `<project>-<service>`; `s1_NCBI_taxonomy_service` has uppercase letters, so
  the auto-generated name (`microbiomekg-s1_NCBI_taxonomy_service`) is
  invalid and `docker compose up --build` fails on it — even though
  `docker compose config` alone doesn't catch this, since `config` only
  resolves YAML and never needs to actually tag an image. Fixed by adding an
  explicit, valid `image: s1-ncbi-taxonomy-service` — the service *name*
  compose uses internally is unaffected, only what the built image is
  tagged. Keep this in mind for any future stage whose service name (as
  specified by nomenclature already fixed for this pipeline) contains
  uppercase letters.

**Operational notes:**
- `s1_NCBI_taxonomy_service` is a one-shot job, not a long-running server —
  it exits on its own once `main.py` finishes (or errors). That's expected,
  not a crash.
- `docker compose up --rm` is not a valid invocation — `--rm` only exists for
  `docker compose run` (single one-off service), not `up`. Use
  `docker compose -f pipeline-docker-compose.yml up --build`, and
  `docker compose -f pipeline-docker-compose.yml down` to tear down after.
- Verified end-to-end working as of this session.

## `src/s1_raw_graph/main.py`

Still the same three-step shape as before (connect → resolve NCBI merged
taxonomies → clone forward to Stage 2), but the clone step is now
`clone_raw_graph_data()` (in-process `shutil` copy, described above) instead
of `src.utils.clone_kg.clone_kg(...)`. The metagraph section remains
commented out, parked exactly as before.

## Stage 2 onward

Not started this round. `src/s2_mapping/` still only has the old pattern (a
standalone `docker-compose.yml` running plain `neo4j:latest`, meant to be
driven by a host-run `main.py`) — no `Dockerfile` yet. The `s2:` stub already
sketched in `pipeline-docker-compose.yml` is commented out and still points
at a nonexistent `src/s2_graph` directory (should be `src/s2_mapping`) with
volume paths copy-pasted from Stage 1 (`RAW_GRAPH_DIR`-based instead of
`MAPPED_GRAPH_DIR`-based) — none of that has been corrected yet, since Stage
2 was explicitly out of scope this round. The intended shape, agreed but not
yet built: a single Dockerfile that starts Neo4j loaded from
`MAPPED_GRAPH_DIR` in the background and then runs
`s2_mapping`'s pipeline logic (`integrations`/`linking`/`main.py`) against it
in the same container — mirroring the self-contained-service pattern
established for Stage 1, rather than the old split of "container just holds
Neo4j, host runs the Python".

Stages 3-6 are untouched, still only the pre-existing
`docker-compose.yml`/`meta-docker-compose.yml` scaffolding described in the
previous version of this document.

## Reference material (do not modify)

- `NCBI_Taxon_Ambiguity_Und_Enzyme_Pipeline/NCBI_Merged_Taxonomies_Resolver/`
  — a previously-validated example of exactly this "separate resolver
  container talking to an already-running Neo4j over bolt" pattern (uses
  `python:3.12-slim`, pinned `neo4j==6.1.0`/`python-dotenv==1.2.2`, matching
  the root `requirements.txt`). Used as a design reference for
  `s1_NCBI_taxonomy_service`; explicitly off-limits to edit.
- `residual_code/` — the previous generation's `run_pipeline.sh`,
  per-stage `Dockerfile`/`entry_point.sh`, `env_config.md`, and
  `raw_command_list.md`. Superseded by `pipeline-docker-compose.yml`, kept
  only for reference.

## Known gaps / open items

- `s0_BioDWH2_service` is an empty placeholder — `docker compose config` on
  the *uncommented* full file fails validation until it gets a real
  `image`/`build` (confirmed while testing); it's currently commented out on
  disk specifically to keep the file runnable while only Stage 1 is being
  exercised.
- Stage 2's `Dockerfile` and its `pipeline-docker-compose.yml` service block
  still need to be written/corrected (wrong directory name, wrong volume
  source paths, no image tag).
- `.env` values for stages 3-6 are still placeholders (`TODO` markers), same
  as before this round's changes.
- `RAW_GRAPH_USERNAME`/`RAW_GRAPH_PASSWORD` (`neo4j`/empty string) are passed
  through to `s1_NCBI_taxonomy_service` via `env_file: .env`, against a
  `NEO4J_AUTH=none` server — works, but hasn't been swapped for `auth=None`
  to match the style used elsewhere in the codebase for no-auth containers
  (e.g. `s2_mapping/main.py`'s metagraph driver).
- BioDWH2 source configuration (the `s0_BioDWH2_service` step) is still
  entirely unautomated, same open question as before: confirm BioDWH2's
  actual non-interactive mechanism for declaring which databases to pull in
  before implementing that service.
