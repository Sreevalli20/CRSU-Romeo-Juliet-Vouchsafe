"""Systematic weight search for policy optimization."""
import json
import subprocess
import sys
from pathlib import Path

# Define parameter grid
param_grid = [
    # (compatibility_weight, uncertainty_penalty, urgency_weight, soft_ask_threshold)
    (0.5, 0.05, 0.15, 0.9),  # Current V3
    (0.6, 0.0, 0.2, 0.95),   # Higher compat, no uncertainty
    (0.55, 0.02, 0.18, 0.92), # Balanced
    (0.45, 0.0, 0.25, 0.9),   # Lower compat, higher urgency
    (0.7, 0.0, 0.1, 0.95),   # Very high compat
    (0.5, 0.0, 0.2, 0.9),    # Remove uncertainty
]

def test_config(config):
    """Test a single configuration."""
    compat_w, uncertainty_w, urgency_w, ask_thresh = config
    
    # Update policy with this config
    policy_code = f'''"""Auto-generated policy for testing."""
import sys
sys.path.insert(0, "src")
from policy_engine import PolicyEngine

# Override weights
import policy_engine
policy_engine.PolicyEngine._original_score_pair = policy_engine.PolicyEngine._score_pair

def patched_score_pair(self, a, b, memory, state, is_sparse=False):
    feasibility_score = 1.0
    compatibility_score = self._calculate_compatibility(a, b)
    evidence_score = self._calculate_evidence(a, b)
    uncertainty_penalty = self._calculate_uncertainty(a, b)
    learned_score = self._calculate_learned_score(a, b, memory)
    urgency_bonus = self._calculate_urgency(a, b, state)
    zone_bonus = self._calculate_zone_proximity(a, b, state)
    
    zone_weight = 0.2 if is_sparse else 0.05
    compat_weight = 0.35 if is_sparse else {compat_w}
    
    final_score = (
        feasibility_score * 0.15 +
        compatibility_score * compat_weight +
        evidence_score * 0.05 +
        learned_score * 0.1 +
        urgency_bonus * {urgency_w} +
        zone_bonus * zone_weight -
        uncertainty_penalty * {uncertainty_w}
    )
    return max(0.0, final_score)

policy_engine.PolicyEngine._score_pair = patched_score_pair

# Also update ask threshold
policy_engine.PolicyEngine._original_identify_soft = policy_engine.PolicyEngine._identify_high_value_soft_fields

def patched_soft(self, members, budget, memory, state):
    asks = []
    if budget <= 0:
        return asks
    if state['day'] < 15:
        return asks
    field_values = []
    for m in members:
        if not m['available']:
            continue
        wait_time = state['day'] - m['arrived_day']
        if wait_time < 8:
            continue
        for field in self.SOFT_FIELDS:
            if m['fields'].get(field) is None and m['field_status'].get(field) != 'declined':
                voi = self._calculate_voi(m, field, memory, state)
                field_values.append((voi, m['member_id'], field))
    field_values.sort(reverse=True, key=lambda x: x[0])
    for voi, member_id, field in field_values:
        if budget >= 1 and voi > {ask_thresh}:
            asks.append({{'member_id': member_id, 'field': field}})
            budget -= 1
            if budget < 1:
                break
    return asks

policy_engine.PolicyEngine._identify_high_value_soft_fields = patched_soft

# Now run the actual policy
import json
from policy_engine import PolicyEngine

engine = PolicyEngine(seed=42)

def handle_request(request):
    phase = request['phase']
    state = request['state']
    memory = request.get('memory', {{}})
    
    if phase == 'ask':
        if not memory:
            memory = engine.initialize_memory()
        asks, memory = engine.decide_asks(state, memory)
        return {{'asks': asks, 'memory': memory}}
    else:
        pairs, memory = engine.decide_pairs(state, memory)
        return {{'pairs': pairs, 'memory': memory}}

if __name__ == '__main__':
    import sys
    if '--custom' in sys.argv:
        request = json.load(sys.stdin)
        response = handle_request(request)
        print(json.dumps(response))
'''
    
    # Write temporary policy
    with open('test_policy.py', 'w') as f:
        f.write(policy_code)
    
    # Run evaluation
    try:
        result = subprocess.run(
            [sys.executable, 'evaluate_custom.py', '--policy', 'test_policy.py', '--variants', 'development', '--seeds', '101,102,103'],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        # Parse result
        output = json.loads(result.stdout)
        if output['summary']['eligible']:
            msmi = output['summary']['overall']['msmi_per_100_arrived_members']
            ask_cost = output['summary']['overall']['ask_cost']
            return msmi, ask_cost, True
        else:
            return 0, 0, False
    except Exception as e:
        print(f"Error testing config {config}: {e}")
        return 0, 0, False

def main():
    results = []
    for config in param_grid:
        print(f"Testing config: {config}")
        msmi, ask_cost, valid = test_config(config)
        results.append({
            'config': config,
            'msmi': msmi,
            'ask_cost': ask_cost,
            'valid': valid
        })
        print(f"  MSMI: {msmi}, Ask Cost: {ask_cost}, Valid: {valid}")
    
    # Save results
    output_path = Path('results/tuning/weight_search.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Find best
    valid_results = [r for r in results if r['valid']]
    if valid_results:
        best = max(valid_results, key=lambda x: x['msmi'])
        print(f"\nBest config: {best['config']}")
        print(f"MSMI: {best['msmi']}, Ask Cost: {best['ask_cost']}")

if __name__ == '__main__':
    main()
