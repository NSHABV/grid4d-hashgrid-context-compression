> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Mixed spatial storage: measured size and linked quality

24 physical archives, 24 fresh-process standalone spatial decodes and 12 ordinal-0 smoke renders completed. Each archive contains all16 spatial levels, with unchanged dtype on the other15 levels. Quantization was not rerun. This is standard ZIP/NPY storage of frozen representations, not H4/H5 or a specialized entropy coder. Gaussian PLY, temporal tables and MLP are excluded: these files are not complete Grid4D scenes.

Primary rates are actual DEFLATE filesystem bytes; RAW and numerical payload are separate. Quality comes from the previous sealed20-view evaluation after exact restored-xyz and rendering controls, not from new20-view measurement. LPIPS_STANDARD_VGG is primary; LPIPS_LEGACY is retained only as a historical column. No LPIPS reaudit was performed. R0 is shown only as a horizontal quality reference, with no rate point. Scatter points are not interpolated; no BD-rate is calculated.

## bouncingballs

| variant | RAW_file_B | DEFLATE_file_B | PSNR | SSIM | LPIPS_STANDARD_VGG | LPIPS_LEGACY |
| --- | --- | --- | --- | --- | --- | --- |
| R2 | 12202907 | 2079533 | 38.8329849 | 0.994528949 | 0.0206007715 | 0.00972951017 |
| M16 | 13251640 | 2771990 | 39.8820915 | 0.994988561 | 0.0190150421 | 0.00838646851 |
| RESTORE | 15348636 | 5859896 | 39.8818893 | 0.994988263 | 0.0190141443 | 0.00838653184 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus standard LPIPS (внешний артефакт; см. каталог исключённых ссылок)

## hellwarrior

| variant | RAW_file_B | DEFLATE_file_B | PSNR | SSIM | LPIPS_STANDARD_VGG | LPIPS_LEGACY |
| --- | --- | --- | --- | --- | --- | --- |
| R2 | 12202906 | 1766427 | 42.2701874 | 0.989561379 | 0.0243978463 | 0.0169232581 |
| M16 | 13251637 | 3022026 | 42.3481598 | 0.989720523 | 0.0240437835 | 0.0166813396 |
| RESTORE | 15348635 | 5370348 | 42.348175 | 0.989720464 | 0.0240446068 | 0.0166825764 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus standard LPIPS (внешний артефакт; см. каталог исключённых ссылок)

## hook

| variant | RAW_file_B | DEFLATE_file_B | PSNR | SSIM | LPIPS_STANDARD_VGG | LPIPS_LEGACY |
| --- | --- | --- | --- | --- | --- | --- |
| R2 | 12202906 | 1488696 | 37.1369247 | 0.987501264 | 0.0142304776 | 0.0111112483 |
| M16 | 13251637 | 2462919 | 37.3708267 | 0.988036454 | 0.0138372984 | 0.0107094301 |
| RESTORE | 15348635 | 5229863 | 37.3707657 | 0.988036752 | 0.0138381962 | 0.0107095949 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus standard LPIPS (внешний артефакт; см. каталог исключённых ссылок)

## jumpingjacks

| variant | RAW_file_B | DEFLATE_file_B | PSNR | SSIM | LPIPS_STANDARD_VGG | LPIPS_LEGACY |
| --- | --- | --- | --- | --- | --- | --- |
| R2 | 12202906 | 1917515 | 38.417347 | 0.9915241 | 0.0112760505 | 0.00822071172 |
| M16 | 12613819 | 2238995 | 38.5064697 | 0.991618752 | 0.0112086106 | 0.00816281699 |
| RESTORE | 13435181 | 3405090 | 38.5066833 | 0.991618812 | 0.0112091172 | 0.00816166028 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus standard LPIPS (внешний артефакт; см. каталог исключённых ссылок)

## Signed differences

| scene | extra_M16_vs_R2_B | extra_M16_vs_R2_pct | saving_M16_vs_RESTORE_B | saving_M16_vs_RESTORE_pct | PSNR_gain | PSNR_gap_to_restore | SSIM_gain | SSIM_gap_to_restore | LPIPS_STANDARD_VGG_gain | LPIPS_STANDARD_VGG_gap_to_restore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 692457 | 33.2986781 | 3087906 | 52.6955768 | 1.0491066 | -0.000202178955 | 0.000459611416 | -2.98023224e-07 | 0.00158572942 | 8.97794962e-07 |
| hellwarrior | 1255599 | 71.0812844 | 2348322 | 43.7275573 | 0.0779724121 | 1.52587891e-05 | 0.000159144402 | -5.96046448e-08 | 0.000354062766 | -8.23289156e-07 |
| hook | 974223 | 65.4413661 | 2766944 | 52.9066249 | 0.233901978 | -6.10351562e-05 | 0.000535190105 | 2.98023224e-07 | 0.000393179245 | -8.97794962e-07 |
| jumpingjacks | 321480 | 16.765449 | 1166095 | 34.245644 | 0.0891227722 | 0.000213623047 | 9.46521759e-05 | 5.96046448e-08 | 6.74398616e-05 | -5.06639481e-07 |

Gain PSNR/SSIM = M16−R2; LPIPS improvement = R2−M16. Gap = RESTORE−M16 for PSNR/SSIM, M16−RESTORE for LPIPS. Signs are retained without a post-hoc equality threshold.

### Residual difference from R0

| scene | PSNR_M16_minus_R0 | SSIM_M16_minus_R0 | LPIPS_STANDARD_VGG_M16_minus_R0 |
| --- | --- | --- | --- |
| bouncingballs | -2.61014938 | -0.000825166702 | 0.00119699351 |
| hellwarrior | -0.492835999 | -0.00105875731 | 0.00123699568 |
| hook | -1.65325165 | -0.00254774094 | 0.00193630066 |
| jumpingjacks | -0.739387512 | -0.000830233097 | 0.000558143482 |

## Numerical payload and compressed level costs

| scene | variant | numerical_bytes | selected_compressed_member_bytes | metadata_member_bytes | framing_bytes | filesystem_bytes |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | R2 | 12196216 | 183235 | 1172 | 1724 | 2079533 |
| bouncingballs | M16 | 13244792 | 875654 | 1210 | 1724 | 2771990 |
| bouncingballs | RESTORE | 15341944 | 3963583 | 1187 | 1724 | 5859896 |
| hellwarrior | R2 | 12196216 | 318526 | 1172 | 1724 | 1766427 |
| hellwarrior | M16 | 13244792 | 1574095 | 1202 | 1724 | 3022026 |
| hellwarrior | RESTORE | 15341944 | 3922437 | 1182 | 1724 | 5370348 |
| hook | R2 | 12196216 | 232328 | 1173 | 1724 | 1488696 |
| hook | M16 | 13244792 | 1206514 | 1210 | 1724 | 2462919 |
| hook | RESTORE | 15341944 | 3973479 | 1189 | 1724 | 5229863 |
| jumpingjacks | R2 | 12196216 | 58584 | 1170 | 1724 | 1917515 |
| jumpingjacks | M16 | 12606974 | 380029 | 1205 | 1724 | 2238995 |
| jumpingjacks | RESTORE | 13428490 | 1546145 | 1184 | 1724 | 3405090 |

All compressed NPY member bytes include the compressed NPY header and data. They are not pure entropy payload. FILE_SIZES.csv contains RAW/DEFLATE budgets; MEMBER_BUDGETS.csv contains each of408 members, including uncompressed NPY size, numerical bytes, compressed bytes and local/central headers. Sum of the nonoverlapping physical components equals filesystem size exactly for every archive.

### Difference from new R2: exact attribution

| scene | variant | changed_member_delta | metadata_delta | framing_delta | total_delta |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | M16 | 692419 | 38 | 0 | 692457 |
| bouncingballs | RESTORE | 3780348 | 15 | 0 | 3780363 |
| hellwarrior | M16 | 1255569 | 30 | 0 | 1255599 |
| hellwarrior | RESTORE | 3603911 | 10 | 0 | 3603921 |
| hook | M16 | 974186 | 37 | 0 | 974223 |
| hook | RESTORE | 3741151 | 16 | 0 | 3741167 |
| jumpingjacks | M16 | 321445 | 35 | 0 | 321480 |
| jumpingjacks | RESTORE | 1487561 | 14 | 0 | 1487575 |

The unchanged15 levels have bit-identical NPY data and compressed member bytes. Thus the whole-file difference is explained exactly by the selected member, manifest and framing. No historical H4 savings or raw-byte increments are added to old ZLIB8 sizes.

### New R2 versus historical ZLIB8

| scene | old_filesystem_bytes | new_minus_old_bytes | level_delta | metadata_delta | framing_delta | same_level_npy_bytes | same_level_compressed_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 2079708 | -175 | 0 | 163 | -338 | True | True |
| hellwarrior | 1766604 | -177 | 0 | 161 | -338 | True | True |
| hook | 1488870 | -174 | 0 | 164 | -338 | True | True |
| jumpingjacks | 1917692 | -177 | 0 | 161 | -338 | True | True |

Historical NPZ stored metadata first as a uint8 NPY and forced a20-byte ZIP64 local extra per member. New files store direct compact manifest JSON last and disable ZIP64. New metadata contains per-level dtypes/hashes; old metadata includes different provenance/geometry fields. Both retain per-level packing. Historical compressor had omitted level; new explicit6/default strategy was fixed before measurement. Installed sources/runtime are in RUNTIME.json and runtime_snapshot. The measured old/new difference is a format difference, not a mixed-precision gain. Main comparisons use new R2 throughout.

## Interpretation

| scene | M16_dominates_RESTORE_PSNR | M16_dominates_RESTORE_all3 |
| --- | --- | --- |
| bouncingballs | True | False |
| hellwarrior | False | False |
| hook | True | False |
| jumpingjacks | False | False |

**bouncingballs.** M16 costs +692,457 additional DEFLATE B versus R2 (+33.2987%) for +1.049106598 dB PSNR. It saves 3,087,906 B versus RESTORE (52.6956%), with signed PSNR gap -0.000202179 dB and standard LPIPS gap +8.97794962e-07.

**hellwarrior.** M16 costs +1,255,599 additional DEFLATE B versus R2 (+71.0813%) for +0.077972412 dB PSNR. It saves 2,348,322 B versus RESTORE (43.7276%), with signed PSNR gap +0.000015259 dB and standard LPIPS gap -8.23289156e-07.

**hook.** M16 costs +974,223 additional DEFLATE B versus R2 (+65.4414%) for +0.233901978 dB PSNR. It saves 2,766,944 B versus RESTORE (52.9066%), with signed PSNR gap -0.000061035 dB and standard LPIPS gap -8.97794962e-07.

**jumpingjacks.** M16 costs +321,480 additional DEFLATE B versus R2 (+16.7654%) for +0.089122772 dB PSNR. It saves 1,166,095 B versus RESTORE (34.2456%), with signed PSNR gap +0.000213623 dB and standard LPIPS gap -5.06639481e-07.

M16 versus R2 is an exchange of storage for quality, not improved compression at identical quality. M16 versus RESTORE is a separately measured byte saving with the reported signed quality differences. The2:4 raw bytes/scalar ratio does not determine the ratio of compressed member or whole-file sizes. Strict dominance flags above use exact measured mean metrics: PSNR-only and all three metrics are distinguished, without rounding away small gaps. They do not establish statistical significance or general optimality.

The levels were selected from previously analyzed test PSNR. This is exploratory follow-up on the same checkpoints/views, not independent precision-policy validation. Frames are correlated; no scientific novelty or continuous RD curve is claimed. No quality-loss tolerance or total storage budget was specified, so no economic-optimality gate is imposed.

One next research decision: specify an acceptable image-quality loss and spatial-storage budget before conducting one separate, preregistered independent-checkpoint validation of these frozen configurations. This run does not begin a bit-depth/level search or design a specialized mixed codec.

## Correctness and preservation

Synthetic uint8/uint16/FP32 roundtrips, signed zero, malformed metadata, duplicate/missing/unsafe entries, corrupted/truncated data, unknown schema, wrong dtype/endian/shape/offset/quantizer, object/pickle payload and size limits are tested in SYNTHETIC_TESTS.json. All24 files are rebuilt byte-identically. Each decoder is a fresh process reading only its input archive and public code/dependencies. The Python read audit is an implementation-level access check, not an OS security sandbox.

External validation compares every allocated row and channel, exact codes, FP32 bytes and complete xyz with sealed previously rendered states. For12 DEFLATE reconstructions, one ordinal0 frame each has exact PNG, float RGB and GT hashes; loaded xyz is hashed immediately before forward, other weights and all20 camera/time records match. No external frozen source is read by standalone decoder; original model access is confined to separate integration/validation. Quality provenance is in RATE_QUALITY_POINTS.csv. Final previous-file SHA256 count/status and complete artifact seal are in FINAL_VALIDATION.json.

## Resources

| scene | variant | mode | serialization_compression_seconds | rebuild_seconds | cold_decoder_process_seconds | decode_dequantization_seconds | decoder_RSS_peak_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | R2 | RAW | 0.069489267 | 0.011938903 | 2.91148564 | 0.185155039 | 577.179688 |
| bouncingballs | R2 | DEFLATE | 0.768396707 | 0.740892907 | 3.01119849 | 0.175256348 | 703.824219 |
| bouncingballs | M16 | RAW | 0.065085824 | 0.010947423 | 3.05817348 | 0.191567727 | 762.914062 |
| bouncingballs | M16 | DEFLATE | 0.792318465 | 0.78009198 | 2.90743134 | 0.172829317 | 827.375 |
| bouncingballs | RESTORE | RAW | 0.078323332 | 0.016747203 | 2.98174942 | 0.20119298 | 831.953125 |
| bouncingballs | RESTORE | DEFLATE | 0.828379948 | 0.788286419 | 3.07974842 | 0.172213775 | 861.230469 |
| hellwarrior | R2 | RAW | 0.06321495 | 0.011286189 | 2.8565447 | 0.191392491 | 577.898438 |
| hellwarrior | R2 | DEFLATE | 0.603463436 | 0.597591553 | 2.96562836 | 0.145491624 | 704.71875 |
| hellwarrior | M16 | RAW | 0.055411226 | 0.01541204 | 2.82068109 | 0.159939596 | 763.488281 |
| hellwarrior | M16 | DEFLATE | 0.601300658 | 0.572739773 | 2.92005049 | 0.151951808 | 828.269531 |
| hellwarrior | RESTORE | RAW | 0.084635029 | 0.009416507 | 2.8443305 | 0.171317535 | 828.269531 |
| hellwarrior | RESTORE | DEFLATE | 0.604801724 | 0.578929176 | 3.00406723 | 0.1798402 | 852.140625 |
| hook | R2 | RAW | 0.061211409 | 0.011914995 | 3.03342121 | 0.210511318 | 577.671875 |
| hook | R2 | DEFLATE | 0.560397455 | 0.538502134 | 2.86512409 | 0.149495606 | 704.386719 |
| hook | M16 | RAW | 0.061975851 | 0.016555075 | 2.86855293 | 0.175799438 | 762.828125 |
| hook | M16 | DEFLATE | 0.553034994 | 0.531077648 | 2.77130514 | 0.154741535 | 827.378906 |
| hook | RESTORE | RAW | 0.072617215 | 0.020808499 | 2.84424043 | 0.191459181 | 827.378906 |
| hook | RESTORE | DEFLATE | 0.585210172 | 0.564769116 | 2.80048121 | 0.169234858 | 851.964844 |
| jumpingjacks | R2 | RAW | 0.059085893 | 0.011299679 | 2.95110389 | 0.182287334 | 577.144531 |
| jumpingjacks | R2 | DEFLATE | 0.71585467 | 0.699472676 | 2.81316171 | 0.154269587 | 701.386719 |
| jumpingjacks | M16 | RAW | 0.054099998 | 0.011088678 | 2.82761917 | 0.171839381 | 759.304688 |
| jumpingjacks | M16 | DEFLATE | 0.73792573 | 0.712709829 | 2.87484543 | 0.167448632 | 821.988281 |
| jumpingjacks | RESTORE | RAW | 0.063517207 | 0.018798739 | 2.84776443 | 0.169086459 | 826.019531 |
| jumpingjacks | RESTORE | DEFLATE | 0.745225395 | 0.724319187 | 2.91976273 | 0.189395568 | 849.429688 |

Fresh-process elapsed includes imports and output writing; internal decode timing includes ZIP reading, validation and dequantization, after imports. Rebuild timing is a second build, not a controlled cold-cache benchmark.

| scene | variant | seconds | process_wall_seconds | allocated_MiB | reserved_MiB |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | R2 | 0.712876159 | 13.6656993 | 819.761719 | 1062 |
| bouncingballs | M16 | 0.37932801 | 12.7797309 | 819.761719 | 1062 |
| bouncingballs | RESTORE | 0.174665039 | 10.9003224 | 819.761719 | 1062 |
| hellwarrior | R2 | 0.362424429 | 8.08929114 | 253.089355 | 308 |
| hellwarrior | M16 | 0.299783405 | 7.79655153 | 253.089355 | 308 |
| hellwarrior | RESTORE | 0.298582936 | 7.97830386 | 253.089355 | 308 |
| hook | R2 | 0.273987352 | 9.29420804 | 906.549805 | 1202 |
| hook | M16 | 0.566125683 | 9.12417928 | 906.549805 | 1202 |
| hook | RESTORE | 0.440534555 | 9.39492818 | 906.549805 | 1202 |
| jumpingjacks | R2 | 0.171383774 | 11.9417081 | 612.572266 | 806 |
| jumpingjacks | M16 | 0.4483505 | 12.5212112 | 612.572266 | 806 |
| jumpingjacks | RESTORE | 0.411621815 | 12.5076852 | 612.572266 | 806 |

Total guarded CPU+smoke wall = 322.163 s; sampled maximum process-tree RSS = 3.801 GiB. Resource guard never triggered. RSS samples every0.5s may double-count shared pages. GPU is used only by smoke renders; PyTorch allocated/reserved is not whole-device usage. Free device memory is in resource logs. Hash-audit time is separate in INPUT_MANIFEST.json/final integrity. Setup, report construction and pauses are excluded.

## Documented test-only correction

The initial draft run mixed_spatial_storage_20261030_01 stopped during synthetic testing before any scene archive was measured. Its corrupt-member fixture accidentally flipped DOS time in a ZIP local header, leaving every data member unchanged. Minimal read-only diagnosis localized the wrong hardcoded byte offset. The corrected fixture computes the actual member payload offset; all rejection requirements and decoder/dequantizer semantics remain unchanged. The initial scripts, BLOCKED marker, traceback and FIXTURE_DIAGNOSIS.md are preserved and covered by this run's input manifest. This ordinary test-construction correction is not a scientific exactness failure.

## Reproduction and continuation

Use existing WSL audit-env, Python3.10.21, NumPy1.26.4, PyTorch2.7.0+cu128; exact zlib/source versions are pinned in RUNTIME.json. Do not rerun into this completed directory. Copy top-level scripts and launch.sh into a fresh research run, then from project root:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/prepare.py
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh setup
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh pilot
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh remaining
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/report.py
```

Review measurements and plots, then run finalize.py with the same Windows Python. Writes are exclusive. COMPLETE.json and CONTINUATION_SCENES_*.json identify completed scenes; partial scenes require diagnosis. A scientific exactness failure triggers BLOCKED_NEEDS_ULTRA, missing/unverified inputs trigger INPUT_BLOCKED. No subsequent experiment starts automatically.
