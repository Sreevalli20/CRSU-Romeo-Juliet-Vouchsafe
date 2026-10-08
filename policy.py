"""Vouchsafe policy: JSON adapter for official evaluation interface."""
import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from src.policy_engine import PolicyEngine


def decide(request):
    """Main decision function for official JSON interface."""
    # Initialize or retrieve engine from memory
    memory = request.get('memory') or {}
    if not memory.get('engine_initialized'):
        # Extract seed from context if available, otherwise use default
        seed = memory.get('seed', 42)
        engine = PolicyEngine(seed=seed)
        memory = engine.initialize_memory()
        memory['engine_initialized'] = True
        memory['seed'] = seed
    else:
        # Reconstruct engine from memory
        seed = memory.get('seed', 42)
        engine = PolicyEngine(seed=seed)

    state = request['state']
    phase = request['phase']

    # Update memory with any new feedback
    if state.get('feedback'):
        memory = engine.update_memory(memory, state['feedback'])

    if phase == 'ask':
        asks, memory = engine.decide_asks(state, memory)
        return {'asks': asks, 'memory': memory}
    elif phase == 'match':
        pairs, memory = engine.decide_pairs(state, memory)
        return {'pairs': pairs, 'memory': memory}
    else:
        raise ValueError(f"Unknown phase: {phase}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', choices=['greedy', 'no_asks', 'random'], default='greedy')
    parser.add_argument('--custom', action='store_true', help='Use custom Vouchsafe policy instead of baseline')
    args = parser.parse_args()

    # If custom flag is set, use our policy
    if args.custom:
        request = json.load(sys.stdin)
        response = decide(request)
        print(json.dumps(response, allow_nan=False))
    else:
        # Use official baseline implementation from kit.py
        from kit import baseline_asks, baseline_match
        request = json.load(sys.stdin)
        state = request['state']
        memory = request.get('memory') or {}

        if request['phase'] == 'ask':
            asks = [] if args.baseline == 'no_asks' else baseline_asks(state)
            print(json.dumps({'asks': asks, 'memory': memory}, allow_nan=False))
        else:
            if args.baseline == 'random':
                import random
                candidates = [m for m in state['members'] if m['available']]
                past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
                from kit import eligibility
                edges = [tuple(sorted((a['member_id'], b['member_id'])))
                         for a, b in __import__('itertools').combinations(candidates, 2)
                         if eligibility(a, b)['status'] == 'feasible'
                         and tuple(sorted((a['member_id'], b['member_id']))) not in past]
                random.Random(17 + state['day']).shuffle(edges)
                pairs, used = [], set()
                for pair in edges:
                    if not used.intersection(pair):
                        pairs.append(list(pair))
                        used.update(pair)
                print(json.dumps({'pairs': pairs, 'memory': memory}, allow_nan=False))
            else:
                pairs = baseline_match(state)
                print(json.dumps({'pairs': pairs, 'memory': memory}, allow_nan=False))
