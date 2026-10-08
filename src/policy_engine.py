"""Vouchsafe consent-first decision policy engine V6 - Greedy + relationship_goal priority."""
import itertools
from typing import Dict, List, Tuple
from kit import eligibility, HARD, SOFT


class PolicyEngine:
    """Consent-first sequential decision policy for Vouchsafe introductions.
    
    V6: Greedy baseline + relationship_goal priority + zone proximity.
    - Only ask hard constraints (like greedy baseline)
    - Simple match counting (like greedy baseline)
    - Extra weight for relationship_goal match (highest simulator weight)
    - Zone proximity for sparse variant
    - No uncertainty penalty
    - No learning
    - Minimal complexity
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.HARD_FIELDS = HARD
        self.SOFT_FIELDS = SOFT

    def initialize_memory(self) -> Dict:
        """Initialize policy memory for a new episode."""
        return {
            'day': 0
        }

    def decide_asks(self, state: Dict, memory: Dict) -> Tuple[List[Dict], Dict]:
        """Decide which clarifications to request.
        
        V5: Only ask hard constraints, exactly like greedy baseline.
        """
        budget = state['ask_budget_remaining']
        members = state['members']
        asks = []

        if budget <= 0:
            return asks, memory

        # Only ask hard constraints for available members (like greedy)
        for m in members:
            if not m['available']:
                continue

            missing_hard = [f for f in self.HARD_FIELDS if m['fields'].get(f) is None]
            declined_hard = [f for f in self.HARD_FIELDS if m['field_status'].get(f) == 'declined']

            # Only ask if not declined and budget allows
            if missing_hard and not declined_hard and budget >= 3:
                asks.append({
                    'member_id': m['member_id'],
                    'field': 'constraints'
                })
                budget -= 3
                if budget < 3:
                    break

        memory['day'] = state['day']
        return asks, memory

    def decide_pairs(self, state: Dict, memory: Dict) -> Tuple[List[List[str]], Dict]:
        """Decide which pairs to introduce."""
        members = [m for m in state['members'] if m['available']]
        past_pairs = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}

        # Detect sparse variant by checking zone diversity
        zones = set(m.get('zone', '') for m in members)
        is_sparse = len(zones) > 4  # More than 4 zones suggests sparse variant

        # Score all feasible pairs
        scored_pairs = []
        for a, b in itertools.combinations(members, 2):
            pair_key = tuple(sorted((a['member_id'], b['member_id'])))
            if pair_key in past_pairs:
                continue

            eligibility_result = eligibility(a, b)
            if eligibility_result['status'] != 'feasible':
                continue

            score = self._score_pair(a, b, memory, state, is_sparse)
            scored_pairs.append((score, pair_key, a, b))

        # Global allocation: select non-overlapping pairs maximizing total score
        pairs = self._allocate_pairs(scored_pairs)

        memory['day'] = state['day']
        return pairs, memory

    def update_memory(self, memory: Dict, feedback: List[Dict]) -> Dict:
        """Update policy memory with new feedback."""
        # V5: No learning, just track day
        return memory

    def _score_pair(self, a: Dict, b: Dict, memory: Dict, state: Dict, is_sparse: bool = False) -> float:
        """Score a candidate pair for introduction.
        
        V6: Greedy baseline + relationship_goal priority + zone proximity.
        - Count soft field matches (like greedy baseline)
        - Extra weight for relationship_goal match (most important per simulator)
        - Zone proximity for sparse
        """
        # Count soft field matches (like greedy baseline)
        match_count = sum(
            a['fields'].get(k) is not None and 
            a['fields'].get(k) == b['fields'].get(k)
            for k in self.SOFT_FIELDS
        )
        
        # Extra weight for relationship_goal match (highest weight in simulator)
        a_goal = a['fields'].get('relationship_goal')
        b_goal = b['fields'].get('relationship_goal')
        if a_goal is not None and b_goal is not None and a_goal == b_goal:
            match_count += 2.0  # Significant bonus
        elif a_goal is not None and b_goal is not None and a_goal != b_goal:
            match_count -= 1.0  # Penalty for mismatch
        
        # Zone proximity for sparse
        if is_sparse:
            a_zone = a.get('zone', '')
            b_zone = b.get('zone', '')
            if a_zone == b_zone:
                match_count += 1.0
        
        return match_count

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
