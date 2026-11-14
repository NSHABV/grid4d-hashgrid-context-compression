> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Mutant training

Fixed seed0, official config,50000 schedule and final iteration50000 selected without quality. Pilot5000 separate; final started fresh, no optimizer resume claimed. Train-only phase copies contain150 original train frames and empty test metadata; test_iterations=[-1]; all50000 actually sampled views verified against train identities.

Full wall 9739.018s; sampled total GPU peak 4353.0MiB; RSS peak 5.442GiB. Model SHA256 376d0d19d1c01241c3f4972244c043d675e37ce1abbfe09ab2cd953d1b0f3480. Original model save is pre-optimizer at official iteration50000. All checkpoints/logs/actual-view CSV retained. Pilot's short-run forecast is not the actual runtime.

First pilot failed before step1 on a guard rejecting an empty list used only for camera-count logging. Isolated guard corrected to reject nonempty test cameras. No model math/forward changes; details PILOT_LAUNCHER_CORRECTION.json. Concurrent auxiliary CPU setup was deferred before tests by RAM preflight and then run sequentially.

User-requested pause near iteration42789: same live worker/model/optimizer/RNG retained, then SIGCONT under replacement external watchdog. No disk optimizer resume/restart. Reported full wall is conservatively charged active time excluding the user pause; raw worker elapsed includes pause. Details PAUSED_STATE.json,RESUME_LAUNCH.json,RESUME_VALIDATION.json. Adopted-worker exit code is unavailable; completion requires50000 completed bodies/backwards,finite losses and worker-final status.
