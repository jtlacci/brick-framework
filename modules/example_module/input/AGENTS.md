# Input contract

This folder owns every external boundary for the module.

## Configuration

- Keep module configuration in `config.yml`.
- Keep run and adapter-call retention limits in that file.
- Never store credentials or secrets in committed configuration or saved data.

## Adapters

- Create one Python file under `adapters/` for each external source.
- APIs, databases, filesystems, queues, clocks, services, and other modules are external sources.
- An adapter fetches or sends data; it does not contain domain logic.
- Calls to another module must use that module's public `run` function.

## Saved data

- Store adapter results under `data/` with the owning run ID.
- A saved result should identify the adapter, request, response or error, and capture time.
- Default smoke runs use saved data. If a test pins a saved run ID, use it; otherwise use the latest matching saved result.
- `--FRESH` means call the real adapter and save the new result. Never silently fall back to a real call.
- Retain only the configured number of recent adapter calls.
- Saved data is intentionally tracked in Git for system understanding.
