> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Training report: standup

Status: **PASS**. One fresh seed0 full run, fixed completed iteration50000. Pilot is separate; no quality-based checkpoint selection or reuse of pilot optimizer state.

Pinned Grid4D commit: `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`. Official standup config is byte-identical to prior mutant config; no capacity/optimizer/schedule changes.

Full supervisor active/wall time: 4550.099647 s (budget10800s). GPU sampling and process-tree RSS are in supervisor-final.json/telemetry.jsonl. Worker CUDA allocation/reservation and timing phases are in worker-final.json.

Actual loader: all official train observations only. Full per-step image/time journal and camera/image checks: full/model/TRAIN_LOADER.json and train_views.csv. Phase datasets contain no val/test images and empty transforms_test.json; test_iterations=[-1].

The original upstream final-iteration saving/optimizer convention is preserved: completion proves50000 executed training bodies/backwards; no alternative checkpoint selected.

Checkpoint SHA256: `1eea264e8b8af42c020d42e5b60ef0b49fe3128b3f452d9c536e3812adea20a7`. Gaussian/config/bundle hashes: CHECKPOINT_MANIFEST.json. Full model hash differs from all five development checkpoints.

No disk optimizer/RNG resume asserted. No new training run is permitted by this result. Evaluation uses this fixed bundle only.
