# The strict lane

The regular Bend brick. Every rule in `bricks/AGENTS.md` applies and the linter has checked its mechanical half. You judge meaning.

## What to judge

1. **The door is one operation.** `run` takes one typed input and returns one typed output inside `IO`. A change that grows it into an action dispatcher is the split signal being ignored. Advisory, unless dispatch hides a sibling dependency the contract does not declare, which blocks.

2. **Effects stay explicit and thin.** An adapter owns one external or sibling boundary. Foreign C/JS performs only the host effect; normalization, validation, retry policy, and domain decisions stay in Bend. If replay fixtures exist, a missing fixture fails explicitly and never falls through to a live call. A hidden effect, implicit live fallback, or business logic in a foreign blocks.

3. **Translation happens at the boundary.** A sibling adapter imports the sibling contract only to construct its input and translate its result back into owning-brick types. A sibling constructor or field crossing into `src/` couples both domains. Block when the foreign type crosses into `src/`; advisory when it leaks only into a name.

4. **The consistency policy is true.** `Eventual{}` accepts lag. `Orchestrated{}` means this brick sequences and compensates. Treating an eventual value as current, or declaring orchestration without implementing its sequencing/failure behavior, blocks.

5. **Writes land on owned state.** `owned_state()` names what this brick may mutate. Any write, delete, or migration against an undeclared resource blocks.

6. **The laws still express the intent.** A change that weakens, deletes, bypasses, or makes a law vacuous in order to fit the implementation blocks. New behavior that can violate an existing domain invariant must update the law and its proof together. A proof that succeeds only because the relevant value is erased or the claim no longer observes the behavior blocks.

7. **Bend's execution model is respected.** Parallel calls must be independent and roughly balanced; affine values must not be cloned merely to preserve an imperative design; effects must not be pulled into a pure function. Concrete performance or ownership mistakes are advisory unless they create a boundary or correctness defect covered above.

8. **Checks earn their keep.** A law that restates a definition without capturing intent, or a smoke program that cannot fail, creates the appearance of evidence. Advisory unless criterion 6 applies.

## Severity

Criteria **2, 4, 5, and 6 block**, and criterion 3 blocks when a sibling type reaches `src/`. Criteria 1, 7, and 8 are advisory unless they identify a concrete path to one of the blocking defects.
