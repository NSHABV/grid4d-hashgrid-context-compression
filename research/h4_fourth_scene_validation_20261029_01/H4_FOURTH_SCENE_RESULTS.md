> Публичная копия исторического документа; локальные пути/ссылки адаптированы. Числа и исторические статусы не пересчитаны.

# H4 fourth scene: jumpingjacks
Decision **GO**; actual C1−C2 **3329 B**. Practical4096B target: False. Pre-fixed engineering thresholds: NO-GO≤0; LIMITED GO0..1024; GO≥1024; practical≥4096.
# Physical bitstreams
| mode | total_bytes | coarse_bytes | fine_payload_bytes | pmf_bytes | mapping_bytes | threshold_bytes | header_bytes | outer_metadata_bytes | pool_rows | accepted_merges | candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 172409 | 56148 | 107868 | 5931 | 20 | 112 | 22 | 2308 | 18 | 0 | 0 |
| C1 | 171990 | 56148 | 107868 | 5512 | 20 | 112 | 22 | 2308 | 16 | 0 | 0 |
| C2 | 168661 | 56148 | 108128 | 1923 | 20 | 112 | 22 | 2308 | 6 | 10 | 203 |

Net=3589 B model saving − 260 B payload penalty − 0 B extra overhead = 3329 B.
Full H4PM model includes PMF masses + mapping + thresholds + model header. All external framing and coarse prerequisite are included. C0→C1 sharing 419 B is not attributed to C2.
Predicted J saving 3327.622141 B; actual 3329 B; residual actual−predicted 1.377859 B. Ideal J is not physical range payload.

| scene | C1_B | C2_B | gain_B | gain_percent_C1 |
| --- | --- | --- | --- | --- |
| bouncingballs | 228833 | 225822 | 3011 | 1.315806723680588 |
| hellwarrior | 155631 | 152691 | 2940 | 1.8890837943597356 |
| hook | 151908 | 148986 | 2922 | 1.923532664507465 |
| jumpingjacks | 171990 | 168661 | 3329 | 1.9355776498633641 |

{"mean_B": 3050.5, "min_B": 2922, "max_B": 3329, "positive_scenes": 4}
Actual scene-specific coding, not held-out CE. Four scenes, one seed each; no statistical significance claim. Results only for standalone xyz L4+L5; no full-checkpoint/temporal/L6 inference.

Accepted strict-J merges:
| left | right | J_before | J_after | ideal_delta_bytes | side_delta_bytes |
| --- | --- | --- | --- | --- | --- |
| [3] | [4] | 115819.4448498865 | 115180.86180153424 | -37.58304835225863 | -601 |
| [13] | [14] | 115180.86180153424 | 114548.8877796315 | -36.97402190272987 | -595 |
| [15] | [16] | 114548.8877796315 | 113929.64971735698 | -39.23806227452587 | -580 |
| [5] | [6] | 113929.64971735698 | 113315.20756265202 | -40.44215470495692 | -574 |
| [12] | [13, 14] | 113315.20756265202 | 113220.52813763758 | 98.32057498555514 | -193 |
| [12, 13, 14] | [15, 16] | 113220.52813763758 | 112956.84583444514 | 25.317696807556786 | -289 |
| [2] | [5, 6] | 112956.84583444514 | 112867.85795290061 | 101.01211845547368 | -190 |
| [2, 5, 6] | [3, 4] | 112867.85795290061 | 112604.43905962555 | -4.41889327505487 | -259 |
| [17] | [19] | 112604.43905962555 | 112539.97063583267 | 101.53157620711136 | -166 |
| [7] | [9] | 112539.97063583267 | 112491.82270859124 | 93.85207275857101 | -142 |

Next proposed experiment: Оценить устойчивость фиксированного C1/C2 на втором seed одной заранее выбранной сцены, без изменения H4.
No automatic fifth scene/H5/other levels. No novelty claim for histogram clustering.
