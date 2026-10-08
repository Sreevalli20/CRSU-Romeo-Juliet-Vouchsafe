"""Vouchsafe consent-first decision policy engine."""
import copy
import itertools
import json
import math
from typing import Dict, List, Optional, Set, Tuple, Any
from kit import eligibility, HARD, SOFT


class PolicyEngine:
    """Consent-first sequential decision policy for Vouchsafe introductions."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.HARD_FIELDS = HARD
        self.SOFT_FIELDS = SOFT

    def initialize_memory(self) -> Dict:
        """Initialize policy memory for a new episode."""
        return {
            'day': 0,
            'field_success': {f: [0, 0] for f in SOFT},  # [positive, total]
            'pair_count': 0,
            'positive_pairs': 0
        }

    def decide_asks(self, state: Dict, memory: Dict) -> Tuple[List[Dict], Dict]:
        """Decide which clarifications to request."""
        budget = state['ask_budget_remaining']
        members = state['members']
        asks = []

        if budget <= 0:
            return asks, memory

        # Phase 1: Prioritize missing hard constraints for available members
        hard_constraint_asks = self._identify_critical_hard_constraints(members, budget, state)
        budget_used = sum(3 for _ in hard_constraint_asks)
        budget -= budget_used
        asks.extend(hard_constraint_asks)

        # Phase 2: Value-of-information for soft fields
        if budget > 0:
            soft_asks = self._identify_high_value_soft_fields(
                members, budget, memory, state
            )
            asks.extend(soft_asks)

        memory['day'] = state['day']
        return asks, memory

    def decide_pairs(self, state: Dict, memory: Dict) -> Tuple[List[List[str]], Dict]:
        """Decide which pairs to introduce."""
        members = [m for m in state['members'] if m['available']]
        past_pairs = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}

        # Score all feasible pairs
        scored_pairs = []
        for a, b in itertools.combinations(members, 2):
            pair_key = tuple(sorted((a['member_id'], b['member_id'])))
            if pair_key in past_pairs:
                continue

            eligibility_result = eligibility(a, b)
            if eligibility_result['status'] != 'feasible':
                continue

            score = self._score_pair(a, b, memory, state)
            scored_pairs.append((score, pair_key, a, b))

        # Global allocation: select non-overlapping pairs maximizing total score
        pairs = self._allocate_pairs(scored_pairs)

        memory['day'] = state['day']
        return pairs, memory

    def update_memory(self, memory: Dict, feedback: List[Dict]) -> Dict:
        """Update policy memory with new feedback."""
        for event in feedback:
            # Track learning from delayed feedback
            if event['event'] == 'second_meeting_intention' and event['value'] == 'yes':
                memory['positive_pairs'] += 1
            memory['pair_count'] += 1

        return memory

    def _identify_critical_hard_constraints(
        self, members: List[Dict], budget: int, state: Dict
    ) -> List[Dict]:
        """Identify members with missing hard constraints that block introductions."""
        candidates = []
        for m in members:
            if not m['available']:
                continue

            missing_hard = [f for f in self.HARD_FIELDS if m['fields'].get(f) is None]
            declined_hard = [f for f in self.HARD_FIELDS if m['field_status'].get(f) == 'declined']

            # Only ask if not declined, has been waiting, and budget allows
            wait_time = state['day'] - m['arrived_day']
            if missing_hard and not declined_hard and budget >= 3 and wait_time >= 3:
                candidates.append({
                    'member_id': m['member_id'],
                    'field': 'constraints'
                })
                budget -= 3
                if budget < 3:
                    break

        return candidates

    def _identify_high_value_soft_fields(
        self, members: List[Dict], budget: int, memory: Dict, state: Dict
    ) -> List[Dict]:
        """Identify soft fields with high expected information value."""
        asks = []
        if budget <= 0:
            return asks

        # Be conservative: only ask soft fields for members who have been waiting
        # and have high uncertainty. Skip soft field asks in early days.
        if state['day'] < 10:
            return asks

        # Calculate expected value for each missing soft field
        field_values = []
        for m in members:
            if not m['available']:
                continue

            # Only consider members who have been waiting
            wait_time = state['day'] - m['arrived_day']
            if wait_time < 5:
                continue

            for field in self.SOFT_FIELDS:
                if m['fields'].get(field) is None and m['field_status'].get(field) != 'declined':
                    voi = self._calculate_voi(m, field, memory, state)
                    field_values.append((voi, m['member_id'], field))

        # Sort by VOI and select top within budget with much higher threshold
        field_values.sort(reverse=True, key=lambda x: x[0])
        for voi, member_id, field in field_values:
            if budget >= 1 and voi > 0.7:  # Much higher threshold
                asks.append({'member_id': member_id, 'field': field})
                budget -= 1
                if budget < 1:
                    break

        return asks

    def _calculate_voi(
        self, member: Dict, field: str, memory: Dict, state: Dict
    ) -> float:
        """Calculate expected value of information for a specific field."""
        # Base value: uniform for now
        base_importance = 0.5

        # Adjust for member availability urgency
        days_active = state['day'] - member['arrived_day']
        urgency = min(1.0, days_active / 20.0)

        # Adjust for number of missing fields (higher uncertainty = higher VOI)
        missing_count = sum(1 for f in self.SOFT_FIELDS if member['fields'].get(f) is None)
        uncertainty_factor = min(1.0, missing_count / len(self.SOFT_FIELDS))

        voi = base_importance * 0.5 + urgency * 0.3 + uncertainty_factor * 0.2
        return voi

    def _score_pair(self, a: Dict, b: Dict, memory: Dict, state: Dict) -> float:
        """Score a candidate pair for introduction."""
        # Component 1: Hard constraint satisfaction (already verified by eligibility)
        feasibility_score = 1.0

        # Component 2: Soft preference compatibility
        compatibility_score = self._calculate_compatibility(a, b)

        # Component 3: Evidence strength
        evidence_score = self._calculate_evidence(a, b)

        # Component 4: Uncertainty penalty
        uncertainty_penalty = self._calculate_uncertainty(a, b)

        # Component 5: Learned preferences
        learned_score = self._calculate_learned_score(a, b, memory)

        # Component 6: Temporal urgency (don't let people wait too long)
        urgency_bonus = self._calculate_urgency(a, b, state)

        # Combine scores
        final_score = (
            feasibility_score * 0.4 +
            compatibility_score * 0.25 +
            evidence_score * 0.15 +
            learned_score * 0.1 +
            urgency_bonus * 0.1 -
            uncertainty_penalty * 0.2
        )

        return max(0.0, final_score)

    def _calculate_compatibility(self, a: Dict, b: Dict) -> float:
        """Calculate soft preference compatibility."""
        matches = 0
        total = 0
        for field in self.SOFT_FIELDS:
            a_val = a['fields'].get(field)
            b_val = b['fields'].get(field)
            if a_val is not None and b_val is not None:
                total += 1
                if a_val == b_val:
                    matches += 1
        return matches / max(1, total)

    def _calculate_evidence(self, a: Dict, b: Dict) -> float:
        """Calculate how much reliable information supports the pair."""
        a_known = sum(1 for f in self.SOFT_FIELDS if a['fields'].get(f) is not None)
        b_known = sum(1 for f in self.SOFT_FIELDS if b['fields'].get(f) is not None)
        total_possible = len(self.SOFT_FIELDS) * 2
        return (a_known + b_known) / total_possible

    def _calculate_uncertainty(self, a: Dict, b: Dict) -> float:
        """Calculate uncertainty penalty for missing information."""
        a_missing = sum(1 for f in self.SOFT_FIELDS if a['fields'].get(f) is None)
        b_missing = sum(1 for f in self.SOFT_FIELDS if b['fields'].get(f) is None)
        total = len(self.SOFT_FIELDS) * 2
        return (a_missing + b_missing) / total

    def _calculate_learned_score(self, a: Dict, b: Dict, memory: Dict) -> float:
        """Calculate score based on learned feature importance."""
        if memory['pair_count'] == 0:
            return 0.5  # Neutral prior

        # Simple overall success rate
        return memory['positive_pairs'] / memory['pair_count']

    def _calculate_urgency(self, a: Dict, b: Dict, state: Dict) -> float:
        """Calculate urgency bonus for members waiting longer."""
        a_wait = state['day'] - a['arrived_day']
        b_wait = state['day'] - b['arrived_day']
        max_wait = max(a_wait, b_wait)
        # Scale: 0 at day 0, 1.0 at day 20+, but capped
        return min(1.0, max_wait / 20.0)

    def _allocate_pairs(self, scored_pairs: List[Tuple]) -> List[List[str]]:
        """Globally allocate non-overlapping pairs to maximize total score."""
        if not scored_pairs:
            return []

        # Sort by score descending
        scored_pairs.sort(reverse=True, key=lambda x: x[0])

        used = set()
        selected_pairs = []

        for score, pair_key, a, b in scored_pairs:
            if a['member_id'] not in used and b['member_id'] not in used:
                selected_pairs.append(list(pair_key))
                used.add(a['member_id'])
                used.add(b['member_id'])

        return selected_pairs
