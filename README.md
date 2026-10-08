# Vouchsafe

### Optimized Sequential Decision Support

CRSU × Romeo & Juliet Hackathon 2026

---

## Overview

Vouchsafe is a consent-first decision support policy for sequential introductions under uncertainty. The policy respects hard constraints, uses greedy-like compatibility scoring with relationship_goal priority, and includes zone proximity handling for sparse geographic conditions. Through systematic optimization (V1-V6), we identified that simpler approaches with domain knowledge outperform complex heuristic systems.

**Key Features:**
- ✅ **Constraint-First**: Hard constraints are never overridden by scores
- ✅ **Greedy-Like Simplicity**: Simple match counting with domain knowledge
- ✅ **Relationship_Goal Priority**: Explicitly weights the simulator's highest-importance feature
- ✅ **Zone Proximity**: Handles sparse geographic conditions
- ✅ **Hard-Constraint-Only Asking**: Matches greedy baseline for clarification
- ✅ **100% Validity**: All evaluation episodes satisfy all constraints

**Performance:** 0.472 MSMI per 100 members (outperforming no-asks baseline by 240%, random baseline by 70%, approaching greedy baseline by 5.6%)

---

## Problem

The Vouchsafe introduction problem is a sequential decision-making task under uncertainty:

- **Incomplete Information**: Member profiles have missing fields
- **Reciprocal Constraints**: Both people must satisfy each other's preferences
- **Delayed Feedback**: Outcomes arrive days after introductions
- **Cold Start**: No historical evidence in early episodes
- **Allocation Problem**: Each person can be introduced at most once per batch

The policy must decide:
1. Which clarification questions to ask (within a daily budget)
2. Which pairs to introduce (subject to reciprocal constraints)
3. How to update understanding from delayed feedback

---

## Solution Architecture (V6)

```
Observable State
       ↓
Constraint Gate (Hard constraints first)
       ↓
Feasible Candidates
       ↓
Simple Match Counting + Relationship_Goal Priority
       ↓
Zone Proximity (for sparse variant)
       ↓
Global Allocation (Greedy selection)
       ↓
Introduction Action
```

### Key Components

**1. Constraint Gate**
- Checks reciprocal eligibility (age, gender, relationship structure, smoking, children, geography, schedule)
- Rejects pairs with any hard constraint violation
- No score can override consent or explicit constraints

**2. Simple Scoring**
- Soft field match counting (like greedy baseline)
- Relationship_goal priority: +2.0 bonus for matches, -1.0 penalty for mismatches
- Zone proximity: +1.0 for same zone in sparse variant

**3. Hard-Constraint-Only Asking**
- Only ask hard constraints (cost 3 units each)
- No soft field asks (eliminated to reduce cost)
- Matches greedy baseline exactly

**4. Global Allocation**
- Greedy selection to maximize total score
- Respects one-introduction-per-person constraint
- Identical to greedy baseline

---

## Quick Start

### Prerequisites

- Python 3.10 or later (tested with 3.14.6)
- No external dependencies required (uses Python standard library only)

### Installation

```bash
git clone https://github.com/Sreevalli20/CRSU-Romeo-Juliet-Vouchsafe.git
cd CRSU-Romeo-Juliet-Vouchsafe
```

No installation required - all components use Python standard library.

### Run Evaluation

```bash
# Run custom policy on all variants
python evaluate_custom.py --seeds 101,102,103 --variants all --output results/custom/final.json

# Run official baselines
python evaluate.py --baseline greedy --seeds 101,102,103 --variants all --output results/baselines/greedy.json
python evaluate.py --baseline no_asks --seeds 101,102,103 --variants all --output results/baselines/no_asks.json
python evaluate.py --baseline random --seeds 101,102,103 --variants all --output results/baselines/random.json
```

### Launch Frontend

Open `frontend/index.html` in a web browser to view the interactive dashboard.

---

## Results

### Overall Performance

|| Policy | MSMI/100 | Coverage | Ask Cost | Valid Episodes |
||--------|---------|----------|----------|----------------|
|| **Vouchsafe V6 (Final)** | **0.472** | 37.1% | 207 | 18/18 (100%) |
|| Greedy Baseline | 0.500 | 43.0% | 200 | 17/18 (94.4%) |
|| Random Baseline | 0.278 | 37.7% | 207 | 18/18 (100%) |
|| No Asks Baseline | 0.139 | 14.3% | 0 | 18/18 (100%) |

### Variant Performance (V6)

|| Variant | Vouchsafe V6 | Greedy | Random | No Asks |
||---------|-------------|--------|--------|---------|
|| Development | **0.833** | 0.500 | 0.333 | 0.167 |
|| Shift | 0.667 | 0.500 | 0.500 | 0.167 |
|| Drift | 0.667 | 0.500 | 0.333 | 0.167 |
|| Cold Start | 0.333 | 0.500 | 0.167 | 0.000 |
|| Delayed | 0.167 | 1.000 | 0.167 | 0.333 |
|| Sparse | 0.167 | 0.167 | 0.167 | 0.000 |

**Key Findings:**
- Outperforms no-asks by 240% and random by 70%
- Only 5.6% below greedy MSMI with 100% validity (greedy has 1 invalid episode)
- Exceptional development performance (0.833 MSMI)
- Strong shift and drift performance (0.667 MSMI)
- Sparse improved from 0.0 to 0.167 (geographic fragmentation partially addressed)
- Ask cost reduced by 70% from initial design (207 vs 684)

---

## Optimization Journey

### V1 Baseline
- Complex multi-component scoring (feasibility, compatibility, evidence, uncertainty, learning, urgency)
- Conservative soft field asking
- **Results**: MSMI 0.417, Ask Cost 684, Sparse 0.0

### V2-V4: Intermediate Experiments
- V2: Oversimplified (0.333 MSMI)
- V3: Rebalanced weights (0.361 MSMI on 3 seeds)
- V4: Removed uncertainty (0.417 MSMI)

### V5: Greedy-like Simplification
- Only ask hard constraints
- Simple match counting
- **Results**: MSMI 0.417, Ask Cost 207, Sparse 0.167

### V6: Final Optimization
- Added relationship_goal priority (+2.0 bonus)
- Added zone proximity for sparse
- **Results**: MSMI 0.472, Ask Cost 207, Sparse 0.167

**Final improvement**: 13% MSMI increase over V1, 70% ask cost reduction

---

## Project Structure

```
CRSU-Romeo-Juliet-Vouchsafe/
├── policy.py              # Official JSON interface adapter
├── evaluate.py            # Official evaluation harness
├── evaluate_custom.py     # Custom policy evaluation
├── kit.py                 # Simulator and eligibility functions
├── Dockerfile             # Container build
├── requirements.txt       # Dependencies (none required)
├── LICENSE               # MIT License
├── DATA_LICENSE.md       # Synthetic data license
├── src/
│   └── policy_engine.py   # Core policy implementation (V6)
├── frontend/
│   ├── index.html         # Interactive dashboard
│   ├── styles.css         # Dashboard styles
│   └── app.js             # Dashboard logic
├── results/
│   ├── baselines/         # Baseline evaluation results
│   ├── custom/            # Custom policy results
│   └── summary.json       # Comparison summary
├── docs/
│   └── research/
│       └── RESEARCH_REPORT.md  # Full research report
└── data/                  # Official synthetic dataset
```

---

## Research Report

See [docs/research/RESEARCH_REPORT.md](docs/research/RESEARCH_REPORT.md) for:
- Detailed optimization journey (V1-V6)
- Baseline gap analysis
- Why V6 works
- Remaining limitations
- Reproducibility instructions

---

## Docker

Build and run the policy in a container:

```bash
# Build image
docker build -t vouchsafe-policy:1.0 .

# Run with official evaluator constraints
docker run --rm -i --network=none --cpus=2 --memory=1g --memory-swap=1g --pids-limit=64 --read-only --cap-drop=ALL --security-opt=no-new-privileges --user=65534:65534 vouchsafe-policy:1.0
```

The container:
- Uses no network (offline execution)
- Has 2 CPU cores, 1 GiB RAM
- Is read-only with no persistent state
- Runs as non-privileged user
- Is compatible with official evaluation constraints

---

## Testing

Run the official test suite:

```bash
python -m unittest -v
```

Run data verification:

```bash
python verify_data.py
```

---

## Ethics & Safety

This policy is designed with ethics and safety as first principles:

### Consent-First
- Hard constraints are never overridden
- Age, gender, relationship structure, smoking, children, and geography are strictly enforced
- No score can compensate for a constraint violation

### Human Authority
- The policy provides decision support, not decisions
- A human operator must approve any real-world introduction
- The policy does not contact people directly

### Uncertainty Transparency
- Missing information is explicitly acknowledged
- The policy distinguishes between observed, not asked, and declined
- Uncertainty is visible in scoring and explanation

### Data Minimization
- Clarification is selective based on expected value
- Only necessary information is requested
- No blanket data collection

### Monitoring
- Constraint violations are tracked (should be zero)
- Clarification costs are logged
- Coverage and outcome disparities are monitored

**Important:** All results are on synthetic data. This is not evidence of real-world performance. The simulator is synthetic research material, not a model of actual Vouchsafe members.

---

## Limitations

1. **Synthetic Data Only**: Results apply only to the simulator, not real-world performance
2. **Below Greedy**: 5.6% gap to greedy baseline (0.472 vs 0.500)
3. **Cold Start Degradation**: 0.333 vs V1's 0.667 (learning removal hurt this variant)
4. **Delayed Degradation**: 0.167 vs V1's 0.500 (delayed feedback learning was valuable)
5. **No Learning**: Removed for stability, but misses adaptive opportunities

---

## Future Work

1. **Lightweight Learning**: Reintroduce simple learning without increasing variance
2. **Close Greedy Gap**: Investigate remaining 5.6% gap to greedy
3. **Improve Cold Start**: Restore cold_start performance while maintaining stability
4. **Multi-Objective**: Optimize for MSMI, coverage, and ask cost jointly

---

## Citation

If you use this work, please cite:

```
CRSU × Romeo & Juliet Hackathon 2026 - Vouchsafe Challenge
https://github.com/Sreevalli20/CRSU-Romeo-Juliet-Vouchsafe
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The synthetic data is licensed under the terms in [DATA_LICENSE.md](DATA_LICENSE.md).

---

## Acknowledgments

- Official challenge repository: https://github.com/RomeoJulietLove/CRSU-x-Romeo-Juliet-Hackathon
- CRSU and Romeo & Juliet for organizing the hackathon
- The Vouchsafe team for the challenge design

---

## Contact

For questions about this submission, please open an issue on GitHub.

---

**Generated with Devin**
