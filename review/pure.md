# The pure lane

Everything in the strict lane applies. Bend has already rejected declared dependencies and extracted external imports. You judge the semantic claim that output depends only on typed input.

## What to judge

Apply the strict criteria, then:

7. **No hidden inputs.** Configuration, clocks, randomness, mutable globals, or captured state that changes the result without appearing in `BrickInput` blocks.

8. **No semantic nondeterminism.** The same input must produce the same output. Scheduling-only differences are advisory; result differences block.

9. **No purity by relocation.** Reading an effect in the runner and passing it into pure-looking private logic is still an effect. Block.

## Severity

Criteria **7 and 9 block**. Criterion 8 blocks when output can differ.
