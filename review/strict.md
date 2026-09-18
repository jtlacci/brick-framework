# The strict lane

The regular host-language brick. Bend has checked its structural boundary; you judge meaning.

## What to judge

1. **The door is one operation.** `run` represents one coherent domain capability rather than an action dispatcher. Advisory unless dispatch hides a dependency.

2. **Effects stay explicit and thin.** Each adapter owns one external or sibling boundary. Normalization and domain decisions remain in host-language domain code. Hidden effects and implicit live fallbacks block.

3. **Translation happens at the boundary.** Sibling values are translated into the owning brick's types before reaching private logic. Cross-domain types in `src/` block.

4. **The consistency policy is true.** `eventual` accepts lag; `orchestrated` means the brick actually owns sequencing and failure handling. A false declaration blocks.

5. **Writes land on owned state.** Writes, deletes, and migrations against undeclared state block.

6. **Behavioral tests remain host-language tests.** Important domain behavior needs ordinary tests near the implementation. Do not introduce package-local Bend laws or runtime code. Missing high-value coverage is advisory; moving behavior into Bend blocks.

## Severity

Criteria **2–5 block**. Criteria 1 and 6 are advisory unless they expose a boundary violation.
