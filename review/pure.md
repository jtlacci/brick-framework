# Pure brick semantic policy

Pure bricks inherit every `strict-*` criterion and add the criteria below. The
linter has already rejected declared dependencies and recognizable effects;
these questions cover the stronger semantic claim that output depends only on
typed input.

### pure-1: There are no hidden inputs

Outcomes: pass, block

Configuration, clocks, randomness, mutable globals, or captured state that can
change the result without appearing in `BrickInput` block.

### pure-2: Results are deterministic

Outcomes: pass, advisory, block

The same input produces the same output. Scheduling-only differences are
advisory; result differences block.

### pure-3: Purity is not manufactured by relocation

Outcomes: pass, block

Reading an effect in the runner and passing it into pure-looking private logic
is still an effect and blocks.
