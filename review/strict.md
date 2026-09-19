# Strict brick semantic policy

### strict-1: The public door is one coherent operation

Outcomes: pass, advisory, block

`run` represents one domain capability, not a generic action dispatcher. A
dispatcher is advisory when it only muddies the API and blocking when it hides
a dependency or boundary.

### strict-2: Effects are explicit and thin

Outcomes: pass, block

Each adapter owns one external or sibling boundary. Normalization and domain
decisions remain in domain code. Hidden effects and implicit live fallbacks are
blocking boundary defects.

### strict-3: Translation happens at the boundary

Outcomes: pass, block

Sibling values are translated into the owning brick's types before reaching
private logic. Cross-domain types leaking into private domain code block.

### strict-4: The consistency policy describes reality

Outcomes: pass, block

`eventual` accepts lag. `orchestrated` means this brick actually owns sequencing
and failure handling. A false declaration blocks.

### strict-5: Writes land on state owned by this brick

Outcomes: pass, block

Writes, deletes, and migrations against state that the brick does not own block.

### strict-6: Important behavior has host-language evidence

Outcomes: pass, advisory

Important domain behavior should have ordinary tests near its implementation.
Missing high-value coverage is advisory.
