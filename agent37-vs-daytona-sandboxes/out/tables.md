# Agent37 vs Daytona: generated tables

## Lifecycle (seconds, median [95% CI])

| Provider | Type | Shape | create → API returns | first command | exec round trip | create errors |
|---|---|---|---|---|---|---|
| agent37 | default | large | 1.18 [1.01–1.335] (n=48) | 0.288 [0.245–0.34] (n=48) | 0.151 [0.145–0.177] (n=48) | 0/48 |
| agent37 | default | medium | 1.28 [1.06–1.52] (n=48) | 0.324 [0.271–0.351] (n=48) | 0.157 [0.132–0.215] (n=48) | 0/48 |
| agent37 | performance | large | 1.265 [1.14–1.445] (n=48) | 0.292 [0.26–0.317] (n=48) | 0.173 [0.166–0.189] (n=48) | 0/48 |
| agent37 | performance | medium | 1.17 [1.02–1.385] (n=48) | 0.279 [0.244–0.311] (n=48) | 0.183 [0.161–0.193] (n=48) | 0/48 |
| agent37 | vm | large | 1.175 [1.08–1.375] (n=48) | 0.442 [0.398–0.478] (n=48) | 0.323 [0.308–0.341] (n=48) | 0/48 |
| agent37 | vm | medium | 1.24 [1.09–1.46] (n=48) | 0.458 [0.381–0.496] (n=47) | 0.316 [0.305–0.34] (n=47) | 0/48 |
| daytona | default | large | 0.26 [0.23–0.29] (n=48) | 0.364 [0.325–0.41] (n=48) | 0.144 [0.129–0.206] (n=48) | 0/48 |
| daytona | default | medium | 0.22 [0.19–0.25] (n=48) | 0.344 [0.254–0.394] (n=48) | 0.137 [0.131–0.169] (n=48) | 0/48 |

## CPU under 180 s sustained all-core load (sha256 rounds per 5 s window, all cores)

| Provider | Type | Shape | first window | last window | min/max ratio |
|---|---|---|---|---|---|
| agent37 | default | large | 10776498.5 [6940496.0–12086219.5] (n=10) | 9041154.0 [7053702.0–9269010.0] (n=10) | 0.675 [0.58–0.729] (n=10) |
| agent37 | default | medium | 4453071.0 [3812673.5–5594451.0] (n=10) | 4479043.5 [3496958.0–5900231.0] (n=10) | 0.625 [0.547–0.711] (n=10) |
| agent37 | performance | large | 11605555.5 [10706106.0–12070384.5] (n=10) | 11410084.0 [10249399.0–12053943.0] (n=10) | 0.888 [0.853–0.944] (n=10) |
| agent37 | performance | medium | 6168133.5 [5809031.0–6396755.5] (n=10) | 6014550.0 [5708252.5–6411911.0] (n=10) | 0.93 [0.864–0.974] (n=10) |
| agent37 | vm | large | 10736793.0 [9168136.0–12155612.0] (n=10) | 10950371.5 [10200934.0–11482879.0] (n=10) | 0.76 [0.702–0.824] (n=10) |
| agent37 | vm | medium | 5463985 [5328414–6105104] (n=9) | 4137501 [2521752–5606476] (n=9) | 0.694 [0.344–0.796] (n=9) |
| daytona | default | large | 10517582.5 [10172301.5–11030844.5] (n=10) | 10526042.5 [10035012.0–11080439.5] (n=10) | 0.934 [0.841–0.946] (n=10) |
| daytona | default | medium | 5135622.0 [4930852.0–5762515.5] (n=10) | 5336495.5 [5139082.5–5733184.0] (n=10) | 0.931 [0.845–0.947] (n=10) |

## git clone (wall seconds; Mbit/s received)

| Provider | Type | Shape | Repo | Mode | seconds | Mbit/s | failures |
|---|---|---|---|---|---|---|---|
| agent37 | default | large | next.js | full | 133.1 [84.65–394.0] (n=5) | 162.4 [55.4–254.6] (n=5) | 0/5 |
| agent37 | default | large | next.js | shallow | 26.9 [4.86–31.33] (n=5) | 14.7 [12.6–80.9] (n=5) | 0/5 |
| agent37 | default | large | pytorch | full | 103.48 [94.6–763.4] (n=5) | 133.5 [18.2–145.8] (n=5) | 0/5 |
| agent37 | default | large | pytorch | shallow | 36.81 [16.14–49.58] (n=5) | 18.9 [14.1–43.2] (n=5) | 0/5 |
| agent37 | default | large | kubernetes | full | 153.37 [89.08–719.27] (n=5) | 71.7 [15.4–123.3] (n=5) | 0/5 |
| agent37 | default | large | kubernetes | shallow | 41.86 [6.35–75.1] (n=5) | 9.3 [5.2–60.7] (n=5) | 0/5 |
| agent37 | default | medium | next.js | full | 135.41 [128.92–342.55] (n=5) | 159.4 [63.7–167.5] (n=5) | 0/5 |
| agent37 | default | medium | next.js | shallow | 23.68 [9.46–31.89] (n=5) | 16.7 [12.3–41.7] (n=5) | 0/5 |
| agent37 | default | medium | pytorch | full | 610.29 [136.33–990.13] (n=5) | 22.7 [14.0–101.1] (n=5) | 0/5 |
| agent37 | default | medium | pytorch | shallow | 42.03 [18.2–89.15] (n=5) | 16.6 [7.8–38.3] (n=5) | 0/5 |
| agent37 | default | medium | kubernetes | full | 125.75 [97.02–195.63] (n=5) | 87.2 [56.1–113.0] (n=5) | 0/5 |
| agent37 | default | medium | kubernetes | shallow | 26.88 [6.08–41.63] (n=5) | 14.4 [9.3–63.4] (n=5) | 0/5 |
| agent37 | performance | large | next.js | full | 98.03 [77.16–1137.46] (n=5) | 229.9 [20.0–291.5] (n=5) | 0/5 |
| agent37 | performance | large | next.js | shallow | 27.27 [23.02–56.59] (n=5) | 15.1 [7.3–17.8] (n=5) | 0/5 |
| agent37 | performance | large | pytorch | full | 96.39 [89.66–659.69] (n=5) | 149.5 [21.9–160.5] (n=5) | 0/5 |
| agent37 | performance | large | pytorch | shallow | 15.56 [11.85–37.25] (n=5) | 46.7 [19.5–61.2] (n=5) | 0/5 |
| agent37 | performance | large | kubernetes | full | 64.7 [58.82–79.11] (n=5) | 177.1 [144.8–194.5] (n=5) | 0/5 |
| agent37 | performance | large | kubernetes | shallow | 10.92 [10.64–27.4] (n=5) | 36.9 [14.7–37.9] (n=5) | 0/5 |
| agent37 | performance | medium | next.js | full | 104.1 [90.46–1082.11] (n=5) | 216.4 [20.9–248.7] (n=5) | 0/5 |
| agent37 | performance | medium | next.js | shallow | 23.04 [2.84–29.29] (n=5) | 17.8 [14.0–144.2] (n=5) | 0/5 |
| agent37 | performance | medium | pytorch | full | 358.32 [104.04–528.88] (n=5) | 41.1 [27.3–138.6] (n=5) | 0/5 |
| agent37 | performance | medium | pytorch | shallow | 31.53 [15.13–88.83] (n=5) | 23.1 [8.2–48.0] (n=5) | 0/5 |
| agent37 | performance | medium | kubernetes | full | 75.51 [73.45–638.63] (n=5) | 151.7 [18.0–155.7] (n=5) | 0/5 |
| agent37 | performance | medium | kubernetes | shallow | 30.41 [10.17–30.57] (n=5) | 13.3 [13.2–39.7] (n=5) | 0/5 |
| agent37 | vm | large | next.js | full | 702.72 [522.5–1289.36] (n=4) | 32.25 [17.6–43.5] (n=4) | 1/5 |
| agent37 | vm | large | next.js | shallow | 21.25 [6.02–27.85] (n=5) | 19.3 [14.8–68.1] (n=5) | 0/5 |
| agent37 | vm | large | pytorch | full | 537.93 [88.95–822.45] (n=5) | 27.4 [17.6–162.1] (n=5) | 0/5 |
| agent37 | vm | large | pytorch | shallow | 40.17 [12.65–101.33] (n=5) | 18.1 [7.2–57.4] (n=5) | 0/5 |
| agent37 | vm | large | kubernetes | full | 672.3 [77.34–1177.13] (n=5) | 17.1 [9.8–148.1] (n=5) | 0/5 |
| agent37 | vm | large | kubernetes | shallow | 21.55 [11.67–45.87] (n=5) | 18.7 [8.8–34.6] (n=5) | 0/5 |
| agent37 | vm | medium | next.js | full | 806.13 [104.12–1354.28] (n=5) | 28.2 [16.8–216.0] (n=5) | 0/5 |
| agent37 | vm | medium | next.js | shallow | 23.69 [7.36–36.61] (n=5) | 17.4 [11.2–55.9] (n=5) | 0/5 |
| agent37 | vm | medium | pytorch | full | 663.26 [419.64–941.67] (n=4) | 22.9 [15.3–35.1] (n=4) | 1/5 |
| agent37 | vm | medium | pytorch | shallow | 73.89 [31.68–112.07] (n=5) | 9.8 [6.5–23.0] (n=5) | 0/5 |
| agent37 | vm | medium | kubernetes | full | 597.85 [311.77–794.18] (n=5) | 19.2 [14.5–36.9] (n=5) | 0/5 |
| agent37 | vm | medium | kubernetes | shallow | 27.26 [10.94–52.19] (n=5) | 14.8 [7.7–36.9] (n=5) | 0/5 |
| daytona | default | large | next.js | full | 588.07 [99.61–870.99] (n=5) | 37.0 [25.0–216.5] (n=5) | 0/5 |
| daytona | default | large | next.js | shallow | 17.28 [8.2–37.69] (n=5) | 22.8 [10.5–48.0] (n=5) | 0/5 |
| daytona | default | large | pytorch | full | 579.06 [396.58–883.82] (n=5) | 23.9 [15.7–34.9] (n=5) | 0/5 |
| daytona | default | large | pytorch | shallow | 33.08 [16.47–57.03] (n=5) | 21.2 [12.2–42.3] (n=5) | 0/5 |
| daytona | default | large | kubernetes | full | 210.31 [97.22–484.75] (n=4) | 65.7 [22.7–113.0] (n=4) | 1/5 |
| daytona | default | large | kubernetes | shallow | 40.58 [24.14–67.13] (n=5) | 9.5 [5.8–16.1] (n=5) | 0/5 |
| daytona | default | medium | next.js | full | 644.64 [221.46–1023.32] (n=5) | 33.8 [21.4–99.0] (n=5) | 0/5 |
| daytona | default | medium | next.js | shallow | 29.22 [28.32–40.64] (n=5) | 13.5 [9.7–14.0] (n=5) | 0/5 |
| daytona | default | medium | pytorch | full | 472.27 [185.4–628.38] (n=5) | 29.3 [22.1–75.7] (n=5) | 0/5 |
| daytona | default | medium | pytorch | shallow | 51.65 [17.19–114.57] (n=5) | 13.6 [6.1–41.3] (n=5) | 0/5 |
| daytona | default | medium | kubernetes | full | 605.03 [149.59–1095.53] (n=5) | 18.2 [10.1–74.6] (n=5) | 0/5 |
| daytona | default | medium | kubernetes | shallow | 38.82 [30.15–41.68] (n=5) | 10.0 [9.3–12.8] (n=5) | 0/5 |

## git clone summary per cell (all three repos pooled)

| Provider | Type | Shape | Mode | runs | failed (clone >25 min or error) | median s | median Mbit/s |
|---|---|---|---|---|---|---|---|
| agent37 | default | large | full | 15 | 0 | 121.11 [98.24–324.94] (n=15) | 123.3 [71.7–140.6] (n=15) |
| agent37 | default | large | shallow | 15 | 0 | 31.33 [22.69–41.86] (n=15) | 14.7 [12.6–24.6] (n=15) |
| agent37 | default | medium | full | 15 | 0 | 174.35 [128.92–498.56] (n=15) | 87.2 [27.8–101.1] (n=15) |
| agent37 | default | medium | shallow | 15 | 0 | 26.1 [18.2–40.03] (n=15) | 16.6 [10.4–38.3] (n=15) |
| agent37 | performance | large | full | 15 | 0 | 89.66 [69.78–98.03] (n=15) | 164.1 [144.8–194.5] (n=15) |
| agent37 | performance | large | shallow | 15 | 0 | 23.02 [11.85–29.25] (n=15) | 20.4 [15.9–37.8] (n=15) |
| agent37 | performance | medium | full | 15 | 0 | 104.1 [79.32–437.32] (n=15) | 138.6 [33.0–155.7] (n=15) |
| agent37 | performance | medium | shallow | 15 | 0 | 28.95 [15.13–30.57] (n=15) | 17.8 [14.0–37.1] (n=15) |
| agent37 | vm | large | full | 15 | 1 | 674.085 [102.45–817.32] (n=14) | 29.25 [17.6–119.6] (n=14) |
| agent37 | vm | large | shallow | 15 | 0 | 25.74 [16.14–40.17] (n=15) | 18.7 [15.6–25.5] (n=15) |
| agent37 | vm | medium | full | 15 | 1 | 676.9 [457.48–810.17] (n=14) | 27.5 [17.8–31.9] (n=14) |
| agent37 | vm | medium | shallow | 15 | 0 | 31.68 [23.69–52.19] (n=15) | 15.8 [10.6–17.4] (n=15) |
| daytona | default | large | full | 15 | 1 | 526.755 [303.28–746.32] (n=14) | 32.25 [23.9–38.3] (n=14) |
| daytona | default | large | shallow | 15 | 0 | 33.08 [19.27–40.86] (n=15) | 16.1 [10.5–25.0] (n=15) |
| daytona | default | medium | full | 15 | 0 | 509.95 [253.8–745.67] (n=15) | 29.3 [22.1–74.6] (n=15) |
| daytona | default | medium | shallow | 15 | 0 | 35.43 [29.22–41.68] (n=15) | 12.0 [10.0–13.6] (n=15) |

## Published price per sandbox-hour (USD)

| Provider | Type | Medium 2/4/8 | Large 4/8/10 |
|---|---|---|---|
| daytona | default | 0.16592 | 0.33174 |
| agent37 | default | 0.00701 | 0.01329 |
| agent37 | vm | 0.01605 | 0.03137 |
| agent37 | performance | 0.02510 | 0.04945 |

## Memory: allocate and touch 128 MB steps up to 2x the shape

GiB reached = last step the probe logged before it stopped (read from its progress file afterwards).

| Provider | Type | Shape | RAM GiB | GiB reached (median [CI]) | how it stopped | sandbox answered 5 s later |
|---|---|---|---|---|---|---|
| agent37 | default | large | 8 | 8.875 [8.875–8.875] (n=4) | {'process OOM-killed (137)': 4, 'whole sandbox restarted (instance not running, /tmp wiped)': 1} | 5/5 |
| agent37 | default | medium | 4 | 4.375 [4.375–4.375] (n=1) | {'whole sandbox restarted (instance not running, /tmp wiped)': 4, 'process OOM-killed (137)': 1} | 3/5 |
| agent37 | performance | large | 8 | 7.5 [7.375–7.5] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |
| agent37 | performance | medium | 4 | 3.625 [3.625–3.625] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |
| agent37 | vm | large | 8 | 7.25 [7.25–7.25] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |
| agent37 | vm | medium | 4 | 3.375 [3.375–3.375] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |
| daytona | default | large | 8 | 7.875 [7.875–7.875] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |
| daytona | default | medium | 4 | 3.875 [3.875–3.875] (n=5) | {'process OOM-killed (137)': 5} | 5/5 |

## Disk: write until ENOSPC (GB written; MB/s)

| Provider | Type | Shape | home volume GB | home MB/s | OS layer GB |
|---|---|---|---|---|---|
| agent37 | default | large | 10.736 [10.736–10.736] (n=3) | 1239.9 [952.8–1325.7] (n=3) | 10.736 [10.736–10.736] (n=3) |
| agent37 | default | medium | 8.589 [8.589–8.589] (n=3) | 1292.8 [92.1–1346.8] (n=3) | 10.736 [10.736–10.736] (n=3) |
| agent37 | performance | large | 10.445 [10.445–10.445] (n=3) | 929.8 [578.4–1041.3] (n=3) | 10.444 [10.444–10.444] (n=3) |
| agent37 | performance | medium | 8.331 [8.331–8.331] (n=3) | 811.5 [467.0–860.7] (n=3) | 10.444 [10.444–10.444] (n=3) |
| agent37 | vm | large | 10.439 [10.439–10.439] (n=3) | 817.9 [753.6–1093.9] (n=3) | 10.439 [10.439–10.439] (n=3) |
| agent37 | vm | medium | 10.439 [10.439–10.439] (n=3) | 790.7 [761.7–934.8] (n=3) | 10.439 [10.439–10.439] (n=3) |
| daytona | default | large | 10.736 [10.736–10.736] (n=3) | 807.5 [486.2–1200.1] (n=3) | 10.736 [10.736–10.736] (n=3) |
| daytona | default | medium | 8.589 [8.589–8.589] (n=3) | 932.9 [624.0–2247.6] (n=3) | 8.589 [8.589–8.59] (n=3) |

## Burst creation (all creates fired at once)

| Provider | N | wave | succeeded | errors | create s median [CI] | p95 | wall s |
|---|---|---|---|---|---|---|---|
| agent37 | 10 | a | 10/10 | {} | 3.64 [1.48–4.065] (n=10) | 4.33 | 7.92 |
| agent37 | 10 | b | 10/10 | {} | 1.265 [1.04–1.465] (n=10) | 1.5 | 2.32 |
| agent37 | 25 | a | 25/25 | {} | 1.6 [1.4–3.21] (n=25) | 4.01 | 4.67 |
| agent37 | 25 | b | 25/25 | {} | 1.55 [1.26–3.11] (n=25) | 3.76 | 5.3 |
| agent37 | 45 | a | 45/45 | {} | 1.97 [1.65–2.52] (n=45) | 4.9 | 7.99 |
| agent37 | 45 | b | 45/45 | {} | 1.8 [1.6–2.73] (n=45) | 4.09 | 7.88 |
| agent37 | 55 | overlimit | 52/55 | {'instance_limit_reached': 3} | 3.735 [2.52–4.42] (n=52) | 8.27 | 9.35 |
| daytona | 10 | a | 10/10 | {} | 0.305 [0.225–0.355] (n=10) | 0.38 | 0.83 |
| daytona | 10 | b | 10/10 | {} | 0.23 [0.22–0.32] (n=10) | 0.35 | 0.79 |
| daytona | 25 | a | 25/25 | {} | 0.31 [0.3–0.34] (n=25) | 0.37 | 0.9 |
| daytona | 25 | b | 25/25 | {} | 0.47 [0.41–0.51] (n=25) | 1.47 | 2.78 |
| daytona | 45 | a | 45/45 | {} | 0.36 [0.3–1.24] (n=45) | 2.25 | 2.88 |
| daytona | 45 | b | 45/45 | {} | 0.42 [0.41–1.41] (n=45) | 1.82 | 2.57 |

## Sleep/wake and persistence (5 cycles: sleep, 120 s idle, first command)

A background counter (one increment per second) is started over exec before the first sleep. "Process kept" = the counter advanced between one wake and the next sleep (pgrep was not used: it matches its own command line).

| Provider | cycles | wake → first command s (median [CI]) | file kept | background process kept |
|---|---|---|---|---|
| agent37 | 15 | 0.56 [0.45–0.57] (n=15) | 15/15 | 0/12 |
| daytona | 15 | 1.38 [1.26–1.58] (n=15) | 15/15 | 0/12 |

## 24 h soak (M10): one Medium instance per provider, slept/stopped, woken every 30 min with `cat marker`

The harness box was paused overnight, so two gaps of 11-12 h and 3.5-4.5 h had no wake attempts; the instances sat asleep/stopped through them. Idle cost is modeled at each provider's published parked rate (disk only: Agent37 $0.09/GB-month on 8 GB; Daytona $0.000108/GB-h on the 3 GB above its 5 GB free) against the always-on rate for the same life.

| Provider | life h | wake attempts | woke and file kept | failed wakes | sleep/stop errors | wake s median [CI] | min-max | longest idle h | modeled parked $ | always-on $ | deleted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| agent37 | 24.52 | 17 | 16/16 | 1 | 2 | 0.785 [0.73–0.88] (n=16) | 0.59-1.09 | 12.5 | 0.0242 | 0.172 | True |
| daytona | 24.54 | 16 | 11/11 | 5 | 2 | 1.47 [1.27–1.52] (n=11) | 1.18-1.6 | 11.6 | 0.008 | 4.071 | True |

## Harness failures (kept in results/runs_full_harness_failed/, rerun, not counted above)

| Provider | cause | attempts |
|---|---|---|
| agent37 | harness: synchronous exec connection dropped | 33 |
| daytona | harness: SDK re-sent dropped exec | 28 |

## Modeled sandbox cost of this grid

| Provider | Type | Shape | sandboxes | sandbox-hours | modeled $ (exact) | modeled $ (whole minutes) |
|---|---|---|---|---|---|---|
| agent37 | default | large | 48 | 1.91 | 0.0254 | 0.0312 |
| agent37 | default | medium | 48 | 2.41 | 0.0169 | 0.0199 |
| agent37 | performance | large | 48 | 1.6 | 0.079 | 0.1014 |
| agent37 | performance | medium | 48 | 2.24 | 0.0561 | 0.0673 |
| agent37 | vm | large | 48 | 3.58 | 0.1123 | 0.125 |
| agent37 | vm | medium | 48 | 4.06 | 0.0652 | 0.072 |
| daytona | default | large | 48 | 3.15 | 1.0434 | 1.1998 |
| daytona | default | medium | 48 | 2.99 | 0.4969 | 0.5752 |
