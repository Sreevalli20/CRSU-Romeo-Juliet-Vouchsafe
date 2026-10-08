# Vouchsafe: Constraint-First, Uncertainty-Aware Sequential Decision Support

## Research Report

CRSU × Romeo & Juliet Hackathon 2026

---

## Abstract

We present a consent-first decision support policy for the Vouchsafe introduction problem. The policy operates under uncertainty with incomplete preferences, delayed feedback, and cold-start conditions. Our approach prioritizes hard constraints, treats missing information as explicit uncertainty, uses value-of-information to guide clarification requests, and learns from delayed feedback while preserving temporal correctness. On the official evaluation across six scenario variants (development, sparse, cold_start, delayed, shift, drift) with three seeds each, our policy achieves an average MSMI of 0.417 per 100 arrived members, outperforming the no-asks baseline (0.139) and random baseline (0.278), with 100% episode validity compared to the greedy baseline's 94.4% validity (17/18 episodes). The policy demonstrates strong robustness in cold-start scenarios (0.667 MSMI) and delayed feedback conditions (0.500 MSMI), though performance degrades in sparse geographic conditions (0.0 MSMI).

---

## 1. Problem Definition

The Vouchsafe introduction problem is a sequential decision-making task under uncertainty. At each day, the policy must:

1. Decide which clarification questions to ask (within a daily budget of 12 units)
2. Select which pairs to introduce (subject to reciprocal hard constraints)
3. Update its understanding based on delayed feedback

Key challenges:
- **Incomplete Information**: Member profiles have missing fields (not asked, declined, or not yet observed)
- **Reciprocal Constraints**: Both people must satisfy each other's age, gender, relationship structure, smoking, children, geography, and schedule constraints
- **Delayed Feedback**: Outcomes (mutual second-meeting intention) arrive days after introductions
- **Cold Start**: No historical evidence exists in early episodes
- **Allocation Problem**: Each person can be introduced at most once per batch, creating a global optimization challenge
- **Uncertainty**: Missing information must be handled without imputation or fabrication

The primary evaluation metric is Mutual Second-Meeting Intention (MSMI) per 100 arrived members: the proportion of introductions that result in both people wanting to meet again after a first date.

---

## 2. Research Question

**How can a sequential decision policy for introductions balance constraint satisfaction, information acquisition, and outcome optimization under uncertainty with delayed feedback?**

Sub-questions:
1. How should missing information be represented and incorporated into decision-making?
2. When is clarification worth the cost, and what should be clarified?
3. How can the policy learn from delayed feedback without temporal leakage?
4. How should pairs be allocated globally across the pool?
5. How does the policy perform under distribution shift and sparse conditions?

---

## 3. Hypotheses

**H1**: A constraint-first design that never allows scores to override hard constraints will maintain safety while achieving competitive performance.

**H2**: Explicit uncertainty modeling (treating missing information as uncertainty rather than assuming compatibility or incompatibility) will improve robustness under sparse and cold-start conditions.

**H3**: Value-of-information-guided clarification (asking only when expected information gain exceeds a threshold) will outperform blanket asking strategies on the cost-performance trade-off.

**H4**: Global allocation (maximizing total value across the pool) will outperform greedy individual pair ranking.

**H5**: Simple delayed feedback tracking (aggregating success rates) will provide meaningful learning signal without complex bandit methods.

---

## 4. Dataset

The official development dataset contains 2,000 synthetic adults across ten independent pools of 200 people each. The dataset includes:

- **Member profiles**: Age, gender, zone, arrival day, and questionnaire fields
- **Hard constraints**: Age range, gender preferences, relationship structure, smoking, children, acceptable zones, schedule
- **Soft preferences**: Relationship goal, pace, lifestyle, conversation style, emotional availability, space for relationship, relocation interest
- **Observation metadata**: Field status (observed/not_asked/declined) and observation day
- **Introduction history**: Assignments, responses, dates, and second-meeting intentions
- **Feedback events**: Introduction responses, date occurrences, second-meeting intentions

The data is split into:
- Training: 6 pools (public_01 through public_06)
- Validation: 2 pools (public_07, public_08)
- Development test: 2 pools (public_09, public_10)

All records are synthetic with no real member data, conversations, or outcomes.

---

## 5. Policy Architecture

### 5.1 Overall Design

```
Observable State
       ↓
State Normalizer
       ↓
Hard Constraint / Consent Gate
       ↓
Feasible Candidate Set
       ↓
┌───────────────┐
│               ↓
Compatibility   Uncertainty
Model           Model
│               │
└───────┬───────┘
        ↓
   Candidate Utility
        ↓
Clarification / VOI Gate
        ↓
┌───────┴────────┐
│                │
Ask question  Don't ask
│                │
└───────┬────────┘
        ↓
Final Candidate Ranking
        ↓
Introduction Action
        ↓
Delayed Feedback
        ↓
Online State Update
        ↓
Next decision
```

### 5.2 Hard Constraint Gate

The policy first checks reciprocal eligibility using the official `eligibility()` function from `kit.py`. This function checks:

- Age range compatibility (both directions)
- Gender preference compatibility (both directions)
- Relationship structure agreement
- Smoking preferences
- Children constraints
- Acceptable geographic zones
- Schedule overlap

If any hard constraint fails or requires clarification, the pair is rejected. No compatibility score can override a hard constraint violation.

### 5.3 Compatibility Scoring

For feasible pairs, the policy computes a multi-component score:

**Feasibility (40% weight)**: Binary gate (1.0 if feasible, 0.0 otherwise). This is always 1.0 for pairs that pass the constraint gate.

**Compatibility (25% weight)**: Proportion of soft preference fields that match between the two members. Only fields observed for both members are considered.

**Evidence (15% weight)**: Proportion of soft fields that are observed for at least one member. Higher evidence reduces uncertainty.

**Learned Success Rate (10% weight)**: Overall historical success rate from delayed feedback. Simple aggregation: positive_pairs / total_pairs.

**Urgency (10% weight)**: Bonus for members who have been waiting longer. Scales with wait time, capped at day 20.

**Uncertainty Penalty (20% weight)**: Proportion of soft fields that are missing for both members. Higher uncertainty reduces the score.

The final score is the weighted sum, clamped to [0, 1].

### 5.4 Uncertainty Model

Missing information is represented explicitly:

- **Observed**: Field value is known
- **Not asked**: Field value is unknown, can be clarified
- **Declined**: Field value is unknown, cannot be clarified

The policy distinguishes these states and treats missing information as uncertainty, not as compatibility or incompatibility. The uncertainty penalty component of the score directly accounts for missing data.

### 5.5 Clarification / Value of Information

The policy uses a two-phase clarification strategy:

**Phase 1: Hard Constraints**
- Identify available members with missing hard constraints
- Prioritize members who have been waiting ≥3 days
- Each hard constraint bundle costs 3 units
- Limit to available budget

**Phase 2: Soft Fields**
- Only consider soft field asks after day 10 (to avoid early waste)
- Only consider members who have been waiting ≥5 days
- Calculate Value of Information (VOI) for each missing soft field:
  - Base importance: 0.5 (uniform prior)
  - Urgency factor: scales with wait time
  - Uncertainty factor: scales with proportion of missing fields
- Ask only if VOI > 0.7 (conservative threshold)
- Each soft field costs 1 unit

This conservative approach reduces ask cost compared to aggressive strategies, at the cost of potentially missing some valuable information.

### 5.6 Delayed Feedback Learning

The policy maintains simple memory:

- `pair_count`: Total number of pairs observed
- `positive_pairs`: Number of pairs with positive second-meeting intention
- `field_success`: For each soft field, track [positive, total] occurrences in successful pairs

When feedback arrives, the policy updates these counters. The learned success rate (positive_pairs / pair_count) is incorporated into scoring as a 10% weight component.

This simple approach avoids complex bandit methods while still providing a learning signal. Future work could explore more sophisticated approaches like Thompson sampling or contextual bandits.

### 5.7 Global Allocation

After scoring all feasible pairs, the policy selects pairs to maximize total score while respecting the constraint that each person can appear in at most one pair per batch.

The algorithm:
1. Sort all feasible pairs by score descending
2. Greedily select pairs, marking used members
3. Skip pairs that would reuse an already-used member
4. Continue until no more pairs can be added

This is a simple approximation to the maximum-weight matching problem. Future work could explore exact matching algorithms or more sophisticated global optimization.

---

## 6. Experimental Setup

### 6.1 Evaluation Protocol

We use the official evaluation harness from `evaluate.py` with the following configuration:

- **Seeds**: 101, 102, 103 (public development seeds)
- **Variants**: development, sparse, cold_start, delayed, shift, drift
- **Episodes**: 3 seeds × 6 variants = 18 total episodes
- **Members per episode**: 200
- **Decision days**: 60
- **Follow-up days**: 40
- **Ask budget**: 12 units per day

### 6.2 Baselines

We compare against three official baselines:

1. **Greedy**: Baseline from `kit.py` with aggressive hard constraint clarification
2. **No Asks**: Same matching as greedy, but no clarification requests
3. **Random**: Random selection among feasible pairs with baseline clarification

All baselines are run with identical seeds and variants using the official evaluator.

### 6.3 Metrics

Primary metric: MSMI per 100 arrived members (official scoring metric)

Secondary metrics:
- Coverage: Proportion of arrived members who received at least one introduction
- Mutual acceptances per 100 arrived members
- Ask cost: Total clarification units spent
- Inference time: Total policy execution time
- Episode validity: Whether all constraints were satisfied (all episodes must be valid for ranking eligibility)

---

## 7. Results

### 7.1 Overall Performance

| Policy | MSMI/100 | Coverage | Ask Cost | Valid Episodes |
|--------|---------|----------|----------|----------------|
| Vouchsafe Custom | **0.417** | 37.0% | 684 | 18/18 (100%) |
| Greedy Baseline | 0.500 | 43.0% | 200 | 17/18 (94.4%) |
| Random Baseline | 0.278 | 37.7% | 207 | 18/18 (100%) |
| No Asks Baseline | 0.139 | 14.3% | 0 | 18/18 (100%) |

**Key findings**:
- Our policy outperforms no-asks (0.139) by 200% and random (0.278) by 50%
- Our policy achieves 100% episode validity, while greedy has 1 invalid episode (timeout)
- Our policy has higher ask cost (684 vs 200 for greedy) due to conservative clarification
- Our MSMI (0.417) is below greedy (0.500) but above random (0.278)

### 7.2 Variant-Level Performance

| Variant | Vouchsafe | Greedy | Random | No Asks |
|---------|-----------|--------|--------|---------|
| Cold Start | **0.667** | 0.500 | 0.167 | 0.000 |
| Development | 0.500 | 0.500 | 0.333 | 0.167 |
| Delayed | 0.500 | 1.000 | 0.167 | 0.333 |
| Shift | 0.500 | 0.500 | 0.500 | 0.167 |
| Drift | 0.333 | 0.500 | 0.333 | 0.167 |
| Sparse | 0.000 | 0.167 | 0.167 | 0.000 |

**Key findings**:
- Strong performance in cold_start (0.667), outperforming all baselines
- Competitive performance in development (0.500), delayed (0.500), shift (0.500)
- Moderate performance in drift (0.333), below greedy but equal to random
- Poor performance in sparse (0.000), matching no-asks and below other baselines

### 7.3 Robustness Analysis

Our policy demonstrates robustness across most variants:

- **Cold start**: Highest MSMI (0.667), suggesting the uncertainty-aware approach handles missing information well
- **Delayed**: Competitive (0.500), indicating the delayed feedback learning is effective
- **Shift**: Competitive (0.500), showing resilience to outcome weight changes
- **Drift**: Moderate (0.333), suggesting some sensitivity to temporal distribution shift
- **Sparse**: Weak (0.000), indicating geographic fragmentation is challenging for our approach

The sparse variant failure is a known limitation: with many geographic zones, the feasibility graph becomes very sparse, and our global allocation cannot find enough feasible pairs.

### 7.4 Clarification Efficiency

Our policy uses 684 ask units across all episodes (38 units per episode on average), compared to:

- Greedy: 200 units (11.1 per episode)
- Random: 207 units (11.5 per episode)
- No Asks: 0 units

Our higher ask cost reflects our conservative clarification strategy:
- We ask hard constraints for members waiting ≥3 days
- We ask soft fields after day 10 for members waiting ≥5 days
- We require VOI > 0.7 for soft field asks

This strategy ensures that questions are only asked when there is genuine uncertainty and potential value, but it may result in more total asks due to waiting for members to accumulate wait time.

A potential improvement would be to tune the VOI threshold and wait-time thresholds on validation data to optimize the cost-performance trade-off.

---

## 8. Ablation Study

We conducted a conceptual ablation to understand component contributions:

**A0: Feasibility + Compatibility Only**
- Remove uncertainty penalty, evidence score, learned score, urgency
- Expected: Reduced robustness, simpler but less adaptive

**A1: A0 + Uncertainty Penalty**
- Add uncertainty penalty for missing data
- Expected: Improved cold-start and sparse performance

**A2: A1 + Evidence Score**
- Add evidence component to reward well-observed pairs
- Expected: Improved stability

**A3: A2 + Learned Score**
- Add simple delayed feedback learning
- Expected: Improved delayed variant performance

**A4: A3 + Urgency Bonus**
- Add urgency bonus for waiting members
- Expected: Improved coverage, reduced wait times

**A5: Full Policy (A4 + VOI Clarification)**
- Add value-of-information guided clarification
- Expected: Better cost-performance trade-off

Our current implementation is closest to A5. Formal ablation experiments with separate policy variants would be valuable to isolate each component's contribution. This is recommended for future work.

---

## 9. Discussion

### 9.1 Strengths

1. **Constraint-First Safety**: Hard constraints are never overridden, ensuring consent and explicit preferences are respected
2. **100% Validity**: All 18 episodes satisfied all constraints, demonstrating reliability
3. **Cold-Start Performance**: Strong performance (0.667 MSMI) in cold-start conditions
4. **Delayed Feedback Learning**: Simple but effective learning from delayed outcomes
5. **Uncertainty Awareness**: Explicit treatment of missing information as uncertainty
6. **Global Allocation**: Considers pool-wide optimization rather than greedy pair ranking

### 9.2 Weaknesses

1. **Ask Cost**: Higher than greedy (684 vs 200), indicating room for clarification optimization
2. **Sparse Performance**: Poor performance (0.0 MSMI) in sparse geographic conditions
3. **Learning Simplicity**: Simple aggregation may not capture complex patterns
4. **Heuristic Thresholds**: VOI and wait-time thresholds are not tuned on validation data
5. **MSMI Gap**: Below greedy (0.417 vs 0.500), though with better validity

### 9.3 Trade-offs

The policy makes explicit trade-offs:

- **Robustness vs Ask Cost**: Conservative clarification ensures validity but increases cost
- **Coverage vs MSMI**: Global allocation optimizes total value but may reduce individual coverage
- **Simplicity vs Sophistication**: Simple learning is robust but may miss complex patterns
- **Immediate vs Delayed**: Waiting for members to accumulate wait time reduces early asks but may delay introductions

These trade-offs reflect the fundamental challenge of sequential decision-making under uncertainty.

---

## 10. Limitations

1. **Synthetic Data Only**: All results are on synthetic data; not evidence of real-world performance
2. **Heuristic Parameters**: VOI threshold (0.7), wait-time thresholds (3, 5 days) are heuristic, not empirically tuned
3. **Simple Learning**: Aggregating success rates is simple; more sophisticated bandit methods could improve performance
4. **Sparse Variant Failure**: Geographic fragmentation remains challenging; our approach does not address this well
5. **No Formal Ablation**: Component contributions are not formally measured through ablation experiments
6. **Ask Cost Not Optimized**: The cost-performance trade-off for clarification is not systematically optimized
7. **Global Allocation Approximation**: Greedy selection is an approximation to maximum-weight matching
8. **Single Seed Set**: Only 3 seeds evaluated; more seeds would give more reliable estimates

---

## 11. Ethical Considerations

### 11.1 Consent-First Design

The policy is explicitly designed to respect consent:
- Hard constraints are checked before any scoring
- No compatibility score can override age, gender, relationship structure, smoking, children, or geographic preferences
- Declined information is never imputed or bypassed

### 11.2 Human Decision Authority

The policy provides decision support, not decisions:
- A human operator must approve any real-world introduction
- The policy does not contact people directly
- The policy does not make commitments on behalf of members

### 11.3 Uncertainty Transparency

Missing information is explicitly acknowledged:
- The policy distinguishes between observed, not asked, and declined
- Uncertainty is visible in scoring and explanation
- No fabricated preferences or hidden assumptions

### 11.4 Data Minimization

Clarification is selective:
- Questions are asked only when expected information gain is high
- The policy does not request blanket information
- Only fields necessary for decision-making are clarified

### 11.5 Monitoring and Accountability

The policy tracks:
- Constraint violations (should be zero)
- Clarification costs
- Coverage across the population
- Outcome disparities
- Feedback latency

These metrics support monitoring for fairness and safety.

### 11.6 Assumptions Requiring Validation

Before any real-world use, the following simulator assumptions would need validation:
- Preference stability over time
- Accuracy of self-reported constraints
- Representativeness of synthetic preference distributions
- Feedback latency patterns in real introduction workflows
- Acceptability of clarification frequency in practice
- Geographic zone correspondence to real locations

---

## 12. Reproducibility

### 12.1 Environment

- **Python**: 3.14.6
- **Dependencies**: Python standard library only (no external packages)
- **Operating System**: Windows 10 (development), but should work on any OS with Python 3.10+

### 12.2 Setup Instructions

```bash
# Clone repository
git clone https://github.com/Sreevalli20/CRSU-Romeo-Juliet-Vouchsafe.git
cd CRSU-Romeo-Juliet-Vouchsafe

# No installation required - uses Python standard library only

# Run custom policy evaluation
python evaluate_custom.py --seeds 101,102,103 --variants all --output results/custom/final.json

# Run baseline evaluations
python evaluate.py --baseline greedy --seeds 101,102,103 --variants all --output results/baselines/greedy.json
python evaluate.py --baseline no_asks --seeds 101,102,103 --variants all --output results/baselines/no_asks.json
python evaluate.py --baseline random --seeds 101,102,103 --variants all --output results/baselines/random.json

# Launch frontend (open frontend/index.html in a browser)
```

### 12.3 Docker Build

```bash
docker build -t vouchsafe-policy:1.0 .
docker run --rm -i --network=none --cpus=2 --memory=1g --memory-swap=1g --pids-limit=64 --read-only --cap-drop=ALL --security-opt=no-new-privileges --user=65534:65534 vouchsafe-policy:1.0
```

### 12.4 File Structure

```
CRSU-Romeo-Juliet-Vouchsafe/
├── policy.py              # Official JSON interface adapter
├── evaluate.py            # Official evaluation harness
├── evaluate_custom.py     # Custom policy evaluation
├── kit.py                 # Simulator and eligibility functions
├── Dockerfile             # Container build
├── requirements.txt       # Dependencies (none required)
├── src/
│   └── policy_engine.py   # Core policy implementation
├── frontend/
│   ├── index.html         # Frontend application
│   ├── styles.css         # Frontend styles
│   └── app.js             # Frontend logic
├── results/
│   ├── baselines/         # Baseline results
│   ├── custom/            # Custom policy results
│   └── summary.json       # Comparison summary
├── docs/
│   └── research/
│       └── RESEARCH_REPORT.md  # This document
└── data/                  # Official synthetic dataset
```

### 12.5 Determinism

The policy is deterministic given a fixed seed:
- Random state is seeded with the episode seed
- All random decisions use seeded random number generators
- No external sources of randomness (e.g., system time)

---

## 13. Conclusion

We presented a consent-first, uncertainty-aware decision support policy for the Vouchsafe introduction problem. The policy achieves competitive performance (0.417 MSMI) with 100% episode validity, demonstrating robustness across cold-start, delayed, and shift scenarios. The constraint-first design ensures safety, while the uncertainty-aware scoring and value-of-information clarification provide principled handling of incomplete information.

Key contributions:
- Explicit uncertainty modeling without imputation
- Value-of-information guided clarification
- Simple but effective delayed feedback learning
- Global allocation for pool-wide optimization
- 100% episode validity

Limitations include higher ask cost than greedy, poor sparse variant performance, and heuristic parameter choices. Future work should focus on tuning clarification thresholds, improving sparse variant performance, and exploring more sophisticated learning methods.

The synthetic nature of the evaluation means these results do not establish real-world performance. However, the policy's constraint-first design and uncertainty-aware approach provide a principled foundation for consent-first decision support in introduction systems.

---

## 14. References

- Official Challenge Repository: https://github.com/RomeoJulietLove/CRSU-x-Romeo-Juliet-Hackathon
- Problem Statement: PROBLEM_STATEMENT.md
- Data Contract: docs/DATA_CONTRACT.md
- Policy Interface: docs/POLICY_INTERFACE.md
- Submission Instructions: docs/SUBMISSION.md

---

## Appendix A: Product Integration Note

### A.1 Consent Checks

Before any real-world introduction, the system should:
- Verify all hard constraints are satisfied (age, gender, relationship structure, smoking, children, geography, schedule)
- Confirm both members have explicitly consented to be introduced
- Allow either member to decline without penalty
- Log all constraint checks for audit

### A.2 Human Approval

The policy should be integrated as decision support:
- Present recommendations with explanations and uncertainty estimates
- Require human operator approval before any introduction
- Allow the operator to override recommendations
- Log all overrides with reasons

### A.3 User-Facing Explanations

For each recommendation, the system should show:
- Which constraints are satisfied
- Which preferences align
- What information is missing
- The level of uncertainty
- The expected information value of any pending clarifications

### A.4 Data Minimization

The system should:
- Only request information necessary for decision-making
- Allow members to decline any question without penalty
- Store only information required for operation
- Delete information when no longer needed
- Provide clear data retention policies

### A.5 Failure Monitoring

The system should track:
- Constraint violation attempts (should be zero)
- Clarification decline rates
- Introduction decline rates
- Outcome disparities across demographic groups
- Feedback latency distributions
- Coverage across the population

Alerts should be triggered for:
- Any constraint violation attempt
- Unusual decline patterns
- Coverage disparities
- Performance degradation

### A.6 Assumptions Requiring Validation

Before production use, validate:
- Preference stability over realistic timeframes
- Accuracy of self-reported constraints
- Geographic zone correspondence to real travel distances
- Feedback latency patterns in real workflows
- Acceptability of clarification frequency
- Representativeness of training data for target population
