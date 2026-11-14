> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Spatial correspondence specification (diagnostics, not a codec)

The source is the pinned Grid4D CUDA file, `get_grid_index<3,2>` and `kernel_grid`.
`mapping-validation.json` records the exact upstream helper SHA, 257 CUDA/CPU
vertex-index comparisons per level, and actual HashEncoder output comparisons at
513 normalized coordinates per grid. Tolerances and observed errors are recorded.
No upstream source is edited. The small CUDA probe compiles the exact upstream
helper slice; it is a measurement instrument, not an optimized/new encoder.

For each level use the **saved offsets**, not a shape-based allocation formula.
CUDA receives `torch.log2(saved_float32_per_level_scale)` and evaluates
`scale[d] = exp2f(level*log_q[d])*base[d]-1`. Lookup resolution is
`ceil(scale)+1`. The diagnostic reads these scales/resolutions on GPU.
Allocation and lookup differ at temporal level31: [32,32,16] vs [33,33,16].

Indexing is x-fastest dense linear addressing while the actual stride fits the
table; otherwise uint32 XOR of vertex*[1,2654435761,805459861], then modulo rows.
The continuous point u becomes `floor(u*scale)` plus eight corners; weights are
tensor products of `f*f*(3-2*f)`. OOB continuous queries produce zero upstream.
The analysis only uses normalized [0,1]^3. For temporal grids its axes are
(x,y,t), (y,z,t), (x,z,t); these are encoding coordinates, not world-space units.
Uniform diagnostic times cover the encoding domain, whereas real Grid4D scene
timestamps map to normalized time0.05..0.95. Diagnostic samples therefore do not
represent the scene's actual query distribution or historical coverage.

## Two implemented, checked exploratory correspondences

Both sample **eligible fine vertices**, 0..floor(fine_scale), uniformly without
replacement, or enumerate the entire eligible lattice if small. They exclude
the fractional upper boundary's ceil(scale) vertex as a point representative,
because v/scale would exceed1. These boundary vertices remain in nominal
collision enumeration and can be fetched as interpolation corners.

Target: the actual fine-level table embedding `slot_fine(v)` (both channels),
and its existing table-wise8 symbol. Different vertices can share a target slot.
We therefore measure a vertex-domain distribution, not a table-row distribution.

| Choice | Coarse context | Reproducibility | Collision effect | Metadata / causality |
|---|---|---|---|---|
| A | coarse smoothstep lookup at u=v/fine_scale | same public seed, vertex set and buffers; verified CUDA mapping | many fine vertices may give different contexts for one fine slot; coarse lookup also uses collided weights | public grid metadata plus seed/budget/class rules; 0 per-vertex side bytes **only for this agreed diagnostic schedule**; coarse-first can be causal for these vertex observations |
| B | nearest coarse vertex rint(u*coarse_scale), then actual index lookup | same inputs; NumPy nearest-even rounding is explicit | nearest coarse slot can collide; fine slot ambiguity persists | same public settings and no diagnostic per-pair side data; potentially coarse-first, but not a table codec |

The 16 coarse bins use full coarse-level/channel min/max. Fine q comes from the
existing table8 quantization. The class parameters would need transmitted or
predefined min/max in a future decoder; this analysis does **not** claim that
such metadata is free in an actual bitstream. Dataset/config and all exact pairs
or sufficient statistics are stored for reproducibility.

A diagnostic conditional histogram and an 80/20 deterministic holdout are used
to test hypotheses. The holdout splits sampled vertex observations, **not target
hash slots**. Duplicate targets can occur in both subsets; independence and
generalization are not established. Held-out comparison uses an IID predictor
fitted on the same training subset with the same Laplace smoothing.

**Decoder availability limitation:** these exploratory contexts currently use
the original float32 coarse embeddings. The existing lossy8-bit bitstream cannot
recover those original floats. The present raw-coarse graphs are therefore
**diagnostic/non-causal for that existing8-bit format**. Coarse-first would be
potentially causal if original coarse values were transmitted losslessly, but
their bytes must then be charged. A separate, researcher-chosen analysis using
already dequantized coarse weights would remove this particular dependency; its
bin boundaries must be derived from decoded values or transmitted metadata.
Neither choice resolves multiple fine-vertex contexts for one fine hash slot.

## Unselected alternatives for an actual table code

1. Choose a deterministic canonical representative per fine slot by bounded
   enumeration. Reproducible from resolutions/hash/seed if coverage and tie-break
   rules are public. Unvisited slots need an explicit fallback. No additional
   coordinate bytes only if both ends derive exactly the same representative;
   otherwise transmitting a vertex costs up to sum ceil(log2(R[d])) bits/slot
   before compression, plus presence flags. Cost is an estimate, not measured.
2. Aggregate all coarse contexts of a fine slot's mapped vertices. Enumeration
   may be huge, so define a deterministic bounded domain and weighting. Decoder
   can repeat it using decoded coarse weights; the sampling schedule/seed and
   bounds must be accounted for. This changes the target context and must be
   investigated separately.
3. Restrict diagnostics to collision-free slots proven by full enumeration;
   a full codec still needs a causal fallback for all other slots.

The analysis does not select a winning representative, aggregation, context
probability model, or causal table traversal. Actual inter-level gain and
collision-vs-inter-level prediction/error graphs are **BLOCKED BY RESEARCH DESIGN**.
Valid existing channel context q0->q1 can separately be grouped by collision
multiplicity: it has an unambiguous slot domain and is labelled channel-only.

## Collision multiplicity

`d_i` is the count of **distinct vertices** mapping to slot i. Duplicate visits
are removed. `sum d_i = number of distinct observed vertices`; visited slots
count d>0; colliding slots count d>1; d=0 slots are retained in histograms.
Nominal finite lattice is 0..lookup_resolution-1 in every axis. Small lattices
are fully enumerated. Large lattices use deterministic uniform vertex sampling
without replacement, so observed d and colliding fractions are **lower bounds**
for that finite domain, not extrapolated full-domain estimates. Uniform diagnostic
continuous queries form a separate set of eight corner fetches. They are not
recorded training queries; historical training coverage cannot be recovered.
