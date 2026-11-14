> Публичная копия исторического документа; локальные пути/ссылки адаптированы. Числа и исторические статусы не пересчитаны.

# H4-GEN: hook, xyz L4→L5

# Decision: GO
ΔH4=2922B. Practical4096B target: False. Thresholds fixed before fitting: NO-GO≤0, LIMITED GO(0,1024), GO≥1024, practical≥4096. Engineering, not statistical.
Проверить тот же фиксированный C1/C2 на ещё одном заранее выбранном независимом L5 checkpoint, без изменения merging/quantizer.
No automatic novelty claim: greedy histogram clustering/cost-aware PMF selection are not presented as new. Findings concern post-training Grid4D data, one additional scene/seed, fixed table8 precision and L4→L5. No statement about compression of all Grid4D, temporal grids or L6 transfer. H5 not implemented.

# Actual size breakdown
| mode | total_bytes | pool_rows | fine_payload_bytes | pmf_bytes | mapping_bytes | threshold_bytes | header_bytes | outer_metadata_bytes | coarse_bytes | accepted_merges | candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 152327 | 20 | 97304 | 5720 | 20 | 112 | 22 | 2308 | 46841 | 0 | 0 |
| C1 | 151908 | 18 | 97304 | 5301 | 20 | 112 | 22 | 2308 | 46841 | 0 | 0 |
| C2 | 148986 | 12 | 97376 | 2307 | 20 | 112 | 22 | 2308 | 46841 | 6 | 258 |

Net C2 vs C1 = 2994 model-saving B − 72 payload-penalty B − 0 additional-metadata B = **2922 B**.
C0→C1 sharing=419B; C0→C2 total=3341B. Sharing is not attributed to statistical clustering. Mapping and full coarse prerequisite are physically paid. Negative payload penalty means C2 also reduces payload. Full section sum equals filesystem size.
Predicted=2920.114038B; actual=2922B; actual−predicted=1.885962B. J ideal payload is not actual file size. Range residual is kept as a total difference, not allocated artificially to bins.

| scene | C1_B | C2_B | gain_B | merges | decode |
| --- | --- | --- | --- | --- | --- |
| bouncingballs L5 | 228833 | 225822 | 3011 | 8 | PASS |
| hellwarrior L5 | 155631 | 152691 | 2940 | 6 | PASS |
| hook L5 | 151908 | 148986 | 2922 | 6 | PASS |

All3 standalone decodes and byte-identical repeats PASS; unchanged H4 revision. Checkpoint/source/runtime/quantizer evidence is in adjacent reports and manifests.

## Accepted merges
| left | right | J_before | J_after | ideal_delta_bytes | side_delta_bytes |
| --- | --- | --- | --- | --- | --- |
| [13] | [15] | 105044.38792689168 | 104375.45550592162 | -31.932420970057137 | -637 |
| [4] | [5] | 104375.45550592162 | 103723.00966144315 | -39.44584447846864 | -613 |
| [2] | [3] | 103723.00966144315 | 103184.52148157705 | 95.51182013389189 | -634 |
| [12] | [14] | 103184.52148157705 | 102703.40543512441 | 131.88395354736713 | -613 |
| [17] | [18] | 102703.40543512441 | 102412.77031305179 | -40.635122072621016 | -250 |
| [7] | [8] | 102412.77031305179 | 102124.27388901402 | -41.49642403777398 | -247 |

Each accepted merge has strict lower J under complete serialized side costs; pooled raw counts use smoothing once. These are paid scene-specific results, not held-out CE.
