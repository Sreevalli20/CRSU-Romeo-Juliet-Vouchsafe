# Vouchsafe: Optimized Sequential Decision Support

## Research Report

CRSU × Romeo & Juliet Hackathon 2026

---

## Abstract

We present a consent-first decision support policy for the Vouchsafe introduction problem. The policy operates under uncertainty with incomplete preferences, delayed feedback, and cold-start conditions. Our approach prioritizes hard constraints, uses greedy-like compatibility scoring with relationship_goal priority weighting, and includes zone proximity handling for sparse geographic conditions. Through systematic optimization across multiple policy versions (V1-V6), we identified that simplifying the approach and removing uncertainty penalties yields better performance. Our final V6 policy achieves an average MSMI of 0.472 per 100 arrived members across six scenario variants (development, sparse, cold_start, delayed, shift, drift) with three seeds each, outperforming the no-asks baseline (0.139) and random baseline (0.278), and approaching the greedy baseline (0.500). The policy achieves 100% episode validity (18/18) compared to the greedy baseline's 94.4% validity (17/18 episodes), with significantly reduced ask cost (207 vs 684 in the initial V1 design).

---

## 1. Optimization Journey

### 1.1 V1 Baseline

The initial V1 policy featured:
- Complex multi-component scoring (feasibility, compatibility, evidence, uncertainty penalty, learning, urgency)
- Conservative soft field asking with VOI threshold 0.7
- Aggressive uncertainty penalty (0.2 weight)

**Results**: MSMI 0.417, Ask Cost 684, Sparse 0.0

**Issues identified**:
- High ask cost (684 vs greedy 200) - too many soft field asks
- Uncertainty penalty (0.2) was blocking good pairs
- Sparse variant failure (0.0 MSMI)
- Below greedy baseline (0.500)

### 1.2 V2-V4: Intermediate Experiments

Several intermediate versions tested different weight configurations:
- V2: Oversimplified, removed too many components (0.333 MSMI)
- V3: Rebalanced weights, reduced uncertainty to 0.05 (0.361 MSMI on 3 seeds)
- V4: Removed uncertainty entirely, increased compatibility (0.417 MSMI)

Key findings:
- Removing uncertainty penalty helped performance
- Reducing soft field asking was critical
- High variance across seeds was a persistent issue

### 1.3 V5: Greedy-like Simplification

V5 adopted a greedy-like approach:
- Only ask hard constraints (like greedy baseline)
- Simple match counting for compatibility
- Small urgency bonus
- No learning, no uncertainty penalty

**Results**: MSMI 0.417, Ask Cost 207, Sparse 0.167

**Improvements**:
- Ask cost reduced from 684 to 207
- Sparse improved from 0.0 to 0.167
- Stability improved

### 1.4 V6: Final Optimization

V6 added domain knowledge to V5:
- Extra weight for relationship_goal matches (+2.0 bonus)
- Penalty for relationship_goal mismatches (-1.0)
- Zone proximity bonus for sparse variant

**Results**: MSMI 0.472, Ask Cost 207, Sparse 0.167

**Final performance**:
- 13% MSMI improvement over V1 (0.417 → 0.472)
- 70% ask cost reduction (684 → 207)
- Sparse fixed (0.0 → 0.167)
- Only 5.6% below greedy (0.500)
- 100% validity vs greedy 94.4%

---

## 2. Final Policy Architecture (V6)

### 2.1 Clarification Strategy

**Only ask hard constraints**:
- Identify available members with missing hard constraints
- Ask constraints bundle (cost 3 units each)
- No soft field asks (eliminated to reduce cost)

This matches the greedy baseline exactly for clarification.

### 2.2 Pair Scoring

**Simple match counting with relationship_goal priority**:

```
score = soft_field_matches + relationship_goal_bonus + zone_bonus
```

Where:
- `soft_field_matches`: Count of matching soft preference fields (like greedy)
- `relationship_goal_bonus`: +2.0 if both have relationship_goal and match, -1.0 if mismatch
- `zone_bonus`: +1.0 for same zone in sparse variant

This is a direct extension of the greedy baseline with domain knowledge about the simulator's highest-weighted feature (relationship_goal has weight 0.7 in the simulator).

### 2.3 Global Allocation

Greedy selection:
1. Sort all feasible pairs by score descending
2. Select non-overlapping pairs maximizing total score
3. Stop when no more pairs can be added

This is identical to the greedy baseline allocation.

### 2.4 Memory

Minimal memory:
- Track engine initialization state
- Track current day

No learning component (removed to reduce variance).

---

## 3. Experimental Results

### 3.1 Overall Performance

|| Policy | MSMI/100 | Coverage | Ask Cost | Valid Episodes |
||--------|---------|----------|----------|----------------|
|| Vouchsafe V6 (Final) | **0.472** | 37.1% | 207 | 18/18 (100%) |
|| Vouchsafe V1 (Initial) | 0.417 | 37.0% | 684 | 18/18 (100%) |
|| Greedy Baseline | 0.500 | 43.0% | 200 | 17/18 (94.4%) |
|| Random Baseline | 0.278 | 37.7% | 207 | 18/18 (100%) |
|| No Asks Baseline | 0.139 | 14.3% | 0 | 18/18 (100%) |

### 3.2 Variant-Level Performance (V6)

|| Variant | Vouchsafe V6 | Greedy | Random | No Asks |
||---------|-------------|--------|--------|---------|
|| Development | **0.833** | 0.500 | 0.333 | 0.167 |
|| Shift | 0.667 | 0.500 | 0.500 | 0.167 |
|| Drift | 0.667 | 0.500 | 0.333 | 0.167 |
|| Cold Start | 0.333 | 0.500 | 0.167 | 0.000 |
|| Delayed | 0.167 | 1.000 | 0.167 | 0.333 |
|| Sparse | 0.167 | 0.167 | 0.167 | 0.000 |

### 3.3 Key Insights

**Why V6 works**:
1. **Relationship_goal priority**: The simulator weights relationship_goal at 0.7 (highest). Explicitly prioritizing this field aligns with the actual reward structure.
2. **Simplicity**: Removing complex heuristics (uncertainty penalty, evidence score, learning) reduced variance and improved stability.
3. **Hard-constraint-only asking**: Matching greedy's ask strategy eliminates unnecessary soft field questions.
4. **Zone proximity**: Helps in sparse variant by prioritizing same-zone pairs.

**Remaining limitations**:
1. **Still below greedy**: 0.472 vs 0.500 (5.6% gap)
2. **Cold start degradation**: 0.333 vs V1's 0.667 (learning component removal hurt this variant)
3. **Delayed degradation**: 0.167 vs V1's 0.500 (delayed feedback learning was valuable)

---

## 4. Baseline Gap Analysis

### 4.1 Why V1 Lost to Greedy

V1 (0.417) lost to greedy (0.500) due to:
1. **Uncertainty penalty (0.2 weight)**: Blocked good pairs with missing information
2. **High ask cost (684)**: Too many soft field asks, wasting budget
3. **Sparse failure (0.0)**: Geographic fragmentation not handled
4. **Complex heuristics**: Evidence score, learning, urgency may have added noise

### 4.2 Why V6 Improves

V6 (0.472) closes most of the gap by:
1. **Removing uncertainty penalty**: Good pairs no longer blocked
2. **Only ask hard constraints**: Ask cost reduced to 207 (near greedy's 200)
3. **Relationship_goal priority**: Aligns with simulator's highest weight
4. **Zone proximity**: Improves sparse from 0.0 to 0.167

### 4.3 Remaining Gap

The 5.6% gap to greedy (0.500) likely stems from:
1. **Lack of learning**: Removed for stability, but hurts cold_start and delayed
2. **Simple match counting**: Greedy's exact algorithm may have edge cases
3. **No soft field asks**: Occasionally valuable information is missed

---

## 5. Reproducibility

### 5.1 Environment

- **Python**: 3.10+
- **Dependencies**: Python standard library only
- **Seeds**: 101, 102, 103 (public development seeds)
- **Variants**: development, sparse, cold_start, delayed, shift, drift

### 5.2 Commands

```bash
# Run V6 evaluation
python evaluate_custom.py --seeds 101,102,103 --variants all --output results/custom/final.json

# Run greedy baseline
python evaluate.py --baseline greedy --seeds 101,102,103 --variants all --output results/baselines/greedy.json
```

### 5.3 Files Changed

- `src/policy_engine.py`: V6 implementation (149 lines)
- `policy.py`: Updated to handle V6 (42 lines)
- `results/summary.json`: Updated with V6 results
- `docs/research/RESEARCH_REPORT.md`: This report

---

## 6. Conclusion

Through systematic optimization from V1 to V6, we achieved a policy that:
- Approaches greedy baseline (0.472 vs 0.500 MSMI)
- Maintains 100% validity (vs greedy 94.4%)
- Reduces ask cost by 70% (207 vs 684 in V1)
- Fixes sparse variant (0.167 vs 0.0 in V1)
- Excels in development (0.833), shift (0.667), and drift (0.667)

The key insight was that simpler, greedy-like approaches with domain knowledge (relationship_goal priority) outperform complex heuristic systems. The remaining 5.6% gap to greedy could potentially be closed by reintroducing a lightweight learning component without increasing variance.
