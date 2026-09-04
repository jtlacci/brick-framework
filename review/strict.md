# The strict lane

The regular brick. Every rule in `bricks/AGENTS.md` applies and the linter has
checked its mechanical half. You judge the meaning.

## What to judge

1. **The door is one operation.** `run` takes one typed input and returns one
   typed output. A diff that grows `run` into a dispatcher — a mode string, a
   `kind` field, an `action` switch — is the repository's split signal being
   ignored. Advisory, unless the dispatch hides a second sibling dependency the
   contract does not declare, which blocks.

2. **Mode discipline in adapters.** Each adapter owns saved, fresh and save
   behaviour. On the default path it replays the named example and a missing or
   mismatched example is an error, never an implicit live call. `save` implies
   fresh, redacts, validates, and replaces atomically. A diff on which the
   default path can reach a real source, or on which a sibling call forwards
   `fresh` or `save`, blocks.

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

6. **Evidence is safe to commit.** Saved examples and run records are tracked
   in Git. A diff whose example carries a credential, a cookie, a personal
   record, or an unbounded payload blocks; the linter's redaction list is a
   floor, not the definition of sensitive.

7. **Simplicity and duplication.** Is there a materially simpler construction
   with the same behaviour? Does this reimplement something the brick, or a
   sibling's `run`, already provides? Name it concretely; "could be cleaner" is
   not a finding. Advisory.

8. **Tests that earn their keep.** A focused `src/` test that restates the
   implementation, asserts on a private helper's shape, or cannot fail reads as
   coverage without being any. Advisory.

## Severity

Criteria **2, 4, 5 and 6 block**, and criterion 3 blocks when the foreign type
reaches `src/`. Criteria 1, 7 and 8 are advisory — except where such a finding
names a concrete path by which the boundary stops holding, which is one of the
blocking criteria wearing another label.
