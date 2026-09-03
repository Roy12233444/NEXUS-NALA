"""
Interactive CLI Simulator for NALA's PredictiveModeEngine.
Allows manual interaction with WCI, CLP, and transition decisions.
"""
import time
import os
import sys

# Add NALA workspace path to sys.path so we can import fleet.coordinator
sys.path.insert(0, r"E:\NALA-Project\NALA")

from fleet.coordinator import PredictiveModeEngine, OperationMode, PredictiveSignals

class TaskGraphMock:
    def __init__(self, node_count, edge_count):
        self.nodes = list(range(node_count))
        self.edges = [(i, i+1) for i in range(min(edge_count, node_count-1))]

def print_status(engine, wci, clp, scs, hb):
    mode = engine.get_current_mode().value
    print("\n" + "="*50)
    print(f"📊 CURRENT ENGINE STATE:")
    print(f"   Mode:              {mode}")
    print(f"   Hysteresis Buffer: {hb:.4f}")
    print(f"   Signals:")
    print(f"     - Workload Complexity (WCI): {wci:.2f}")
    print(f"     - Cognitive Load (CLP):      {clp:.2f}")
    print(f"     - State Cohesion (SCS):      {scs:.2f}")
    
    # Calculate benefits
    benefit_to_int = (clp * 0.4) + ((1.0 - wci) * 0.3) + (scs * 0.3)
    benefit_to_auto = (wci * 0.5) + ((1.0 - clp) * 0.3) + (scs * 0.2)
    
    print(f"   Decisions:")
    if engine.get_current_mode() == OperationMode.AUTONOMOUS:
        threshold = 0.5 + hb
        print(f"     - Interactive Benefit: {benefit_to_int:.2f} (Threshold: > {threshold:.2f})")
        print(f"     - Will switch?         {'👉 YES 🟢' if benefit_to_int > threshold else '❌ NO'}")
    else:
        threshold = 0.6 + hb
        print(f"     - Autonomous Benefit:  {benefit_to_auto:.2f} (Threshold: > {threshold:.2f})")
        print(f"     - Will switch?         {'👉 YES 🟢' if benefit_to_auto > threshold else '❌ NO'}")
    print("="*50 + "\n")

def main():
    engine = PredictiveModeEngine()
    
    # Initial state values
    node_count = 10
    edge_count = 2
    interaction_latencies = [2.5, 3.0, 2.0]  # Moderate CLP
    scs = 0.9
    
    print("🕉️ Welcome to the NALA Predictive Mode Simulator! 🕉️")
    print("Interact with WCI, CLP, and watch the state transitions.")
    
    while True:
        # Calculate current signals
        graph = TaskGraphMock(node_count, edge_count)
        wci = engine.compute_workload_complexity_index(graph)
        clp = engine.compute_cognitive_load_predictive(interaction_latencies)
        hb = engine.compute_hysteresis_buffer()
        
        print_status(engine, wci, clp, scs, hb)
        
        print("Menu:")
        print("1. Simulate User typing fast (CLP ↑)")
        print("2. Simulate User idle / slow (CLP ↓)")
        print("3. Add complex task nodes (WCI ↑)")
        print("4. Clear task nodes (WCI ↓)")
        print("5. Check / Trigger Mode Transition")
        print("6. Simulate rapid transition thrashing (Test Hysteresis)")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == '1':
            # Fast latencies -> high CLP
            interaction_latencies = [0.1, 0.2, 0.3, 0.15]
            print("\n⚡ Simulated rapid typing. CLP increased!")
        elif choice == '2':
            # High latencies -> low CLP
            interaction_latencies = [4.8, 5.0, 4.9]
            print("\n💤 Simulated idle user. CLP decreased!")
        elif choice == '3':
            node_count += 30
            edge_count += 15
            print(f"\n📂 Added complex tasks. Task graph has {node_count} nodes, {edge_count} edges. WCI increased!")
        elif choice == '4':
            node_count = 5
            edge_count = 1
            print("\n🧹 Cleared task graph. WCI decreased!")
        elif choice == '5':
            # Check transition
            current_mode = engine.get_current_mode()
            if current_mode == OperationMode.AUTONOMOUS:
                should_switch = engine.should_transition_to_interactive("AUTONOMOUS", wci, clp, scs, hb)
                if should_switch:
                    print("\n⏳ Triggering prepare_for_interaction()...")
                    prep = engine.prepare_for_interaction(None)
                    print(f"   Initiated: {prep['actions_initiated']}")
                    if engine.validate_transition_readiness(prep):
                        print("   Validation PASSED! Swapped to INTERACTIVE mode.")
                        signals = PredictiveSignals(wci, clp, scs, hb)
                        engine.record_transition(OperationMode.AUTONOMOUS, OperationMode.INTERACTIVE, signals)
                    else:
                        print("   Validation FAILED!")
                else:
                    print("\n❌ Transition condition not met (Benefit is below threshold).")
            else:
                should_switch = engine.should_transition_to_autonomous("INTERACTIVE", wci, clp, scs, hb)
                if should_switch:
                    print("\n⏳ Triggering prepare_for_autonomous()...")
                    prep = engine.prepare_for_autonomous(None)
                    print(f"   Initiated: {prep['actions_initiated']}")
                    if engine.validate_transition_readiness(prep):
                        print("   Validation PASSED! Swapped to AUTONOMOUS mode.")
                        signals = PredictiveSignals(wci, clp, scs, hb)
                        engine.record_transition(OperationMode.INTERACTIVE, OperationMode.AUTONOMOUS, signals)
                    else:
                        print("   Validation FAILED!")
                else:
                    print("\n❌ Transition condition not met (Benefit is below threshold).")
        elif choice == '6':
            print("\n🔄 Simulating 5 transitions in 2 seconds to test Hysteresis Buffer...")
            dummy_signals = PredictiveSignals(wci, clp, scs, hb)
            for _ in range(5):
                engine.record_transition(OperationMode.AUTONOMOUS, OperationMode.INTERACTIVE, dummy_signals)
                engine.record_transition(OperationMode.INTERACTIVE, OperationMode.AUTONOMOUS, dummy_signals)
            print("   Instability detected! Check the Hysteresis Buffer value below:")
        elif choice == '7':
            print("\nGoodbye, buddy!")
            break
        else:
            print("\nInvalid choice. Try again.")
            
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
