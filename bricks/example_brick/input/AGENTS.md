# Input contract

This folder owns typed configuration plus every external-source and sibling boundary for the brick.

- Keep compile-time configuration in `config.bend`. Runtime secrets come from an explicit adapter effect and never from committed source.
- Create one `.bend` file under `adapters/` for each external source or sibling brick.
- An external adapter may call Base effects or a thin paired `.c`/`.js` foreign effect. It does not contain domain decisions.
- A sibling adapter imports `../../../<sibling>/contract.bend` for boundary types and `../../../<sibling>/main.bend` for execution, then calls only `run`.
- Adapters never import or call their own brick's `src/` or `runner/`.
- Put reviewed replay fixtures in `data/<adapter>/<case>.bend` when a brick needs them. Replay never falls through to a live call.
- Do not commit credentials, headers, cookies, tokens, or unredacted sensitive payloads.
