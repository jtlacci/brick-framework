# Semantic review context

The repository linter has already enforced package shape, typed public entries,
declared dependencies, import direction, cycles, recognizable effect placement,
and state ownership. The semantic policy must not repeat those mechanical checks.

Judge only evidence in the supplied diff and documents. A referenced file that is
not shown is unknown, not defective. Files listed as reviewed elsewhere or not
reviewed explain routing; do not infer their contents.

Each policy criterion declares its allowed outcomes. `block` is a merge gate;
`advisory` is a non-blocking improvement; `pass` means the diff contains no
supported concern for that criterion. Prefer a boundary-preserving block when
the shown evidence is genuinely ambiguous about a boundary, but never block on
style, file size, naming, or absent context.

When a previous verdict is supplied, do not block an implementation that follows
its suggestion and do not re-litigate unchanged work. Changed code is still
judged normally.
