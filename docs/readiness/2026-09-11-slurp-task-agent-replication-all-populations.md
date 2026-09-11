# SLURP task-agent replication: all populations

All values come from first complete official scores and the frozen paired analysis. Differences are frame minus direct in percentage points. Speaker-cluster CI90 uses 10,000 draws; row-mean F1 and pooled-count micro F1 are different estimands. These are historically exposed exploratory populations.

| Population | Outcome | Direct % | Frame % | Delta pp | Speaker CI90 pp | Equal-scenario delta pp |
|---|---|---:|---:|---:|---|---:|
| NEW500 | Intent | 73.200 | 77.400 | +4.200 | [+2.331, +5.974] | +4.632 |
| NEW500 | Scenario | 81.400 | 84.400 | +3.000 | [+1.205, +4.815] | +3.168 |
| NEW500 | Action | 75.200 | 79.200 | +4.000 | [+2.141, +5.829] | +4.396 |
| NEW500 | Mean row SLU F1 | 20.114 | 23.224 | +3.110 | [+1.737, +4.459] | +3.445 |
| NEW500 | Official micro SLU F1 | 36.511 | 39.502 | +2.991 | [+1.056, +4.905] | +3.579 |
| OLD500 | Intent | 71.000 | 73.000 | +2.000 | [+0.233, +3.661] | +1.984 |
| OLD500 | Scenario | 80.200 | 82.400 | +2.200 | [+0.220, +4.102] | +2.190 |
| OLD500 | Action | 73.800 | 75.200 | +1.400 | [-0.427, +3.297] | +1.382 |
| OLD500 | Mean row SLU F1 | 17.622 | 19.768 | +2.145 | [+0.714, +3.559] | +2.163 |
| OLD500 | Official micro SLU F1 | 33.953 | 35.987 | +2.034 | [-0.219, +4.321] | +3.515 |
| DEV1000 | Intent | 72.100 | 75.200 | +3.100 | [+1.899, +4.310] | +3.103 |
| DEV1000 | Scenario | 80.800 | 83.400 | +2.600 | [+1.377, +3.850] | +2.710 |
| DEV1000 | Action | 74.500 | 77.200 | +2.700 | [+1.542, +3.941] | +2.652 |
| DEV1000 | Mean row SLU F1 | 18.868 | 21.496 | +2.628 | [+1.592, +3.672] | +2.638 |
| DEV1000 | Official micro SLU F1 | 35.260 | 37.784 | +2.523 | [+0.987, +4.102] | +4.213 |

Source: DATA analysis/SAEA-SLURP-TASK-AGENT-REPLICATION-PAIRED-ANALYSIS-V1/paired-analysis.result-v1.json, SHA256 b7efdf5f8ea4bd8d76bff5949c8b9c2ce456595121ab9dfe0fae7628a78de0eb.
All 915 independently recomputed population/scenario/weighting points agree; 270 scenario-metric rows are retained in all-population-scenario-metrics-v1.csv, SHA256 1b5d90f9db1e6f24559e8cfb4be636050ac5d7b38e24cd8fca5adf15765dde89.
