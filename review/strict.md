# The strict lane

The regular brick. Every rule in `bricks/AGENTS.md` applies and the linter has
checked its mechanical half. You judge the meaning.

## What to judge

1. **The door is one operation.** `run` takes one typed input and returns one
   typed output. A diff that grows `run` into a dispatcher — a mode string, a
   `kind` field, an `action` switch — is the repository's split signal being
   ignored. Advisory, unless the dispatch hides a second sibling dependency the
   contract does not declare, which blocks.

2. **All io goes through the run context.** Every external call is
   `ctx["io"].external(...)` and every sibling call is `ctx["io"].sibling(...)`
   with the sibling's `run` passed, not called. That is what lets production
   record the call and evaluation replay it. A diff that reaches a source any
   other way — a client stored at module level, a call made before or after the
   io call, a branch on an environment variable or a "mode" — makes the brick
   behave differently in evaluation than in production, and blocks.

3. **Translation at the boundary.** A sibling adapter imports the sibling's
   `run` and translates its output into this brick's own types. A diff that
   passes a sibling's `BrickOutput` (or its field names) straight through into
   `src/` has moved the sibling's contract inside this brick; when that type
   later changes, two bricks break where one should. Block when the foreign type
   crosses into `src/`; advisory when it merely leaks into a name.

4. **The consistency policy is true.** `eventual` accepts lag; `orchestrated`
   means this brick sequences and compensates. A diff that reads an `eventual`
   sibling and then acts as if the result were current — a balance, a lock, a
   latest-record read followed by a write that assumes it — blocks. A diff that
   declares `orchestrated` and implements no sequencing or compensation blocks.

5. **Writes land on owned state.** `OWNED_STATE` names what this brick may
   change. The linter compares declarations; it cannot see a write. A diff that
   writes, deletes or migrates a resource the contract does not own — through an
   adapter or otherwise — blocks.

6. **Captured data is safe to keep.** The runtime records every brick input,
   output, request and response. A diff that puts a credential, a token, a
   cookie or a personal record into one of them — a header in a request, a key
   in an input — blocks. Authentication belongs inside the adapter's live call,
   after the io records the request.

7. **Simplicity and duplication.** Is there a materially simpler construction
   with the same behaviour? Does this reimplement something the brick, or a
   sibling's `run`, already provides? Name it concretely; "could be cleaner" is
   not a finding. Advisory.

8. **Determinism is declared truthfully.** `DETERMINISTIC = True` tells the
   runtime to keep only a hash of each output, because a replay can compute it
   again. A diff that sets it on a brick that samples, calls a model, reads a
   clock or keeps state across calls loses data that cannot be recovered.
   Blocks.

## Severity

Criteria **2, 4, 5, 6 and 8 block**, and criterion 3 blocks when the foreign
type reaches `src/`. Criteria 1 and 7 are advisory — except where such a finding
names a concrete path by which the boundary stops holding, which is one of the
blocking criteria wearing another label.
