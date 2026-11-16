# Failure modes

This file is about what the offline checks can and cannot show. The fractions in the README `IDENTIFIABILITY` block are recomputed by `make check`. They are properties of the simulator below, not of the manuscript.

## The simulator favors the analysis

`identifiability.py` plants three mechanisms and asks whether `cc_full_experiment.wilcoxon` on final-round ECE, read with the rule in that file, recovers the plant.

The plants are built so the contrasts the rule looks at actually move:

- Temporal drift adds `0.03` confidence per round and ignores `sync` and the seeded agent. C1 and C3 share T=10, so they stay close. C2 and C4 run to T=20, so their final ECE is higher. The rule calls that pattern `temporal` only when C3 is not significantly above C1.
- Contagion puts a seed agent near confidence `0.90` and, on later sync rounds, pulls other agents toward that seed with weight `0.75`. C3 is the T=10 sync cell, which is exactly the contrast the rule treats as `contagion`.
- The null keeps confidence near the accuracy rate `0.55` in every condition.

Other choices that make a miss less likely than it would be on live traces:

- Accuracy is an independent coin flip. Confidence and correctness do not share a latent, and accuracy does not fall over rounds. Real calibration fatigue could move both.
- Each agent-round has 40 trials. The live harness uses `N_Q = 5`, so its ECE estimates are much noisier than the ones this study labels.
- The contagion pull is toward the seed's previous-round mean confidence. The live harness sends a per-question text message, which this simulator does not implement.
- Effects are large relative to the `0.03` noise. A weaker drift or a weaker pull could fall into the `other` bin or be swapped.
- The rule is uncorrected across three Wilcoxon tests, because `cc_full_experiment.py` prints those p-values without a correction. With effects this large the temporal and contagion plants still separate; under the null, one of 40 seeds was labeled `other` and none were given a mechanism name.
- Calling C3-versus-C1 "contagion" overclaims what that cell identifies. C3 also changes N from 3 to 5 and turns on the seeded agent. An N-only plant was not included. It would be labeled `contagion` by this rule. The study therefore does not show that the factorial isolates peer copying.

One temporal seed in this draw was labeled `contagion` (C3 cleared p < 0.05 by chance). That miss is part of the reported rate. Do not read 39/40 as confirmation of the manuscript's mechanism.

## Live API calls are not deterministic

`api()` in the experiment scripts posts to a hosted chat endpoint with a per-call temperature. There is no seed on the model output. A second live run is a new sample, not a bit-check of a published table. `--dry-run` is the exception: it replaces the HTTP client with `mock_llm`, which is a SHA-256 of the prompt. That stub is deterministic and offline. It is not a model of drift or contagion, and its ECE is not a result.

Retries sleep and then raise. A 403 after more than 500 calls saves finished reps and aborts. Failed calls that are not that rate-limit path are stored as confidence 0.5 and accuracy 0, which is a real bias if a live run hits errors and continues.

## The manuscript's raw data is not here

No result JSON, checkpoint, or figure from the paper runs is committed. The stated 100,500 API calls cannot be recomputed from this tree. `cc_analysis_figures.py` will draw Fig 1 and Fig 2 from whatever JSON it is given, including the synthetic file `make check` writes under a temp directory. Fig 3 does not read that JSON. The function body labels those curves as a schematic. A PDF from Fig 3 is not evidence of calibration.

`make check` fails if the README block or the headline fractions disagree with a fresh study. It does not, and cannot, fail when a manuscript number is wrong, because those numbers are not inputs to the check.
