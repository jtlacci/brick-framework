# Visible Modules

Visible Modules is a small convention for codebases built by humans and agents. A module may be complicated internally, but its boundary must remain easy to inspect:

- `input/` shows configuration, external sources, and recent source responses.
- `runner/` provides the module's only public function and keeps recent runs.
- `src/` contains the domain logic and cannot perform I/O.

The framework is intentionally just folders, JSON records, and a few Node.js scripts.

## Module shape

```text
modules/<name>/
├── index.js                    # re-exports only run()
├── input/
│   ├── config.yml
│   ├── adapters/               # one file per external source
│   ├── create-adapters.js      # recording/replay wrapper
│   └── data/
│       └── <source>/
│           ├── samples/        # latest committed response per request key
│           └── calls/          # bounded fresh-call history
├── runner/
│   ├── run.js                  # the public boundary
│   ├── rng.js                  # run ID creation
│   ├── runs/                   # bounded run history, including tests
│   └── tests/                  # one JSON input per smoke test
└── src/
    └── index.js                # domain logic
```

## The contract

The only public module API is:

```js
const { runId, result } = await run(input, {
  mode: "replay",              // or "fresh"
  parentRunId: undefined,       // set by module-to-module adapters
});
```

`runner/run.js` creates the run ID, loads `input/config.yml`, wraps the adapters, calls `src/index.js`, and writes `runner/runs/<run-id>.json`. It records successful and failed runs. A run record contains the exact input, adapter provenance, returned result or error, mode, parent run, and timing.

`src/index.js` exports `execute()` only for its runner. It receives wrapped adapters as arguments. It may import local source files and pure libraries listed in `config.yml` under `srcLibraries`, but it may not import filesystem, network, process, runner, input, or another module code. The boundary checker rejects direct I/O imports and common I/O globals; reviewing an allowed library as genuinely I/O-free remains a human responsibility.

An adapter owns one external boundary: an HTTP API, database, filesystem, clock, queue, or another module. Each adapter supplies `fetch(args)` and may supply a stable `key(args)`. The framework wrapper, not the adapter author, owns recording and replay.

### Replay and fresh modes

- `replay` is the default. It reads `input/data/<source>/samples/<key>.json`. A missing sample is an error with instructions to run fresh. It never falls through to the live source.
- `fresh` calls the adapter. The response or error is written under `calls/` with the run ID and call ID. A successful response also replaces the stable sample for that key.

Samples are current fixtures, not history, so they are not pruned. Fresh-call files and run files are histories and are capped by `retention.adapterCalls` and `retention.runs` in `config.yml`. Test and manual runs share the same run cap, so frequent smoke tests can evict older manual runs. These JSON artifacts are deliberately tracked by Git. The framework writes them but does not run Git commands for you. Commit a fresh run's updated samples, adapter calls, and run records together so the run record explains why a fixture changed.

### Module-to-module calls

An adapter may import another module's public `run()` function. Call it with the outer run ID as `parentRunId`:

```js
export default {
  name: "other-module",
  async fetch(args, context) {
    return otherModuleRun(args, {
      mode: context.mode,
      parentRunId: context.runId,
    });
  },
};
```

The inner module keeps its own run record. The outer adapter snapshot stores the returned data, so both sides remain visible. Propagating `context.mode` means a fresh outer run is fresh end-to-end; use that mode deliberately because it can fan out to several real sources. The boundary checker permits imports of another module's `index.js` but rejects reaching into its `src/`, `input/`, or `runner/` folders.

## Commands

```sh
npm install
npm test                 # boundary checks + replay smoke tests
npm run test:fresh       # boundary checks + real adapter calls
npm run module:new -- orders
```

`npm test` discovers every JSON file under every module's `runner/tests/` and passes it directly to that module's `run()` function. These are intentionally broad smoke tests, not a large unit-test suite. `--FRESH` is uppercase and explicit because it may contact real systems and update committed samples.

New modules are copied from `templates/module`. Start by naming the domain, adding one adapter per external source, and keeping orchestration in `runner/run.js` rather than hiding it in `src/`.
