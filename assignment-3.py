import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

# ----------------------------------------------------------------------
# Bell pair generator
# ----------------------------------------------------------------------
def create_e91_circuit():
    """Create entangled Bell state for E91 protocol."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc

# ----------------------------------------------------------------------
# Measurement rotations for A1,A2,A3 and B1,B2,B3
# ----------------------------------------------------------------------
alice_angles = {
    "A1": 0,            
    "A2": np.pi / 2,    
    "A3": np.pi / 4     
}

bob_angles = {
    "B1": 0,
    "B2": -np.pi / 4,
    "B3": np.pi / 4
}

def apply_measurement(qc, angle, qubit):
    qc.ry(angle, qubit)

# ----------------------------------------------------------------------
# CHSH correlation helper
# ----------------------------------------------------------------------
def correlation(samples):
    if len(samples) == 0:
        return 0
    vals = [(1 if a == b else -1) for (_, a, b, _, _) in samples]
    return np.mean(vals)

# ----------------------------------------------------------------------
# Full E91 simulation
# ----------------------------------------------------------------------
def simulate_e91_protocol(num_pairs=200):

    sampler = StatevectorSampler()

    alice_choices = np.random.choice(["A1", "A2", "A3"], num_pairs)
    bob_choices   = np.random.choice(["B1", "B2", "B3"], num_pairs)

    results = []

    # Store base pair occurrences for detailed statistics
    base_counts = {Ai: {Bj: 0 for Bj in ["B1","B2","B3"]} for Ai in ["A1","A2","A3"]}

    # ------------------------------------------------------------------
    # Generate results
    # ------------------------------------------------------------------
    for i in range(num_pairs):
        qc = create_e91_circuit()

        apply_measurement(qc, alice_angles[alice_choices[i]], 0)
        apply_measurement(qc, bob_angles[bob_choices[i]], 1)
        qc.measure_all()

        outcome = sampler.run([qc], shots=1).result()
        bits = list(outcome[0].data.meas.get_counts().keys())[0]

        alice_bit = int(bits[1])
        bob_bit = int(bits[0])

        Ai = alice_choices[i]
        Bj = bob_choices[i]

        base_counts[Ai][Bj] += 1

        results.append((i, alice_bit, bob_bit, Ai, Bj))

    # ------------------------------------------------------------------
    # Partition samples
    # ------------------------------------------------------------------
    key_pairs = [p for p in results if (p[3], p[4]) in [("A1","B1"), ("A3","B3")]]
    chsh_pairs = [p for p in results if (p[3], p[4]) in [
        ("A1","B2"), ("A1","B3"),
        ("A2","B2"), ("A2","B3")
    ]]

    # Individual CHSH group counts
    CHSH_counts = {
        "A1,B2": len([p for p in chsh_pairs if p[3]=="A1" and p[4]=="B2"]),
        "A1,B3": len([p for p in chsh_pairs if p[3]=="A1" and p[4]=="B3"]),
        "A2,B2": len([p for p in chsh_pairs if p[3]=="A2" and p[4]=="B2"]),
        "A2,B3": len([p for p in chsh_pairs if p[3]=="A2" and p[4]=="B3"])
    }

    # ------------------------------------------------------------------
    # Compute CHSH
    # ------------------------------------------------------------------
    E_A1B2 = correlation([p for p in chsh_pairs if p[3]=="A1" and p[4]=="B2"])
    E_A1B3 = correlation([p for p in chsh_pairs if p[3]=="A1" and p[4]=="B3"])
    E_A2B2 = correlation([p for p in chsh_pairs if p[3]=="A2" and p[4]=="B2"])
    E_A2B3 = correlation([p for p in chsh_pairs if p[3]=="A2" and p[4]=="B3"])

    S = abs(E_A1B2 + E_A1B3 + E_A2B2 - E_A2B3)

    # ------------------------------------------------------------------
    # Build key
    # ------------------------------------------------------------------
    alice_key = [p[1] for p in key_pairs]
    bob_key   = [p[2] for p in key_pairs]
    agreement = np.mean([a == b for a,b in zip(alice_key,bob_key)]) * 100

    # ------------------------------------------------------------------
    # Outputs
    # ------------------------------------------------------------------
    print("\n========== E91 protocol ==========")
    print(f"Total entangled pairs: {num_pairs}\n")

    print("Basis usage counts:")
    print("Alice:")
    print(f"  A1: {np.sum(alice_choices == 'A1')}")
    print(f"  A2: {np.sum(alice_choices == 'A2')}")
    print(f"  A3: {np.sum(alice_choices == 'A3')}")
    print("Bob:")
    print(f"  B1: {np.sum(bob_choices == 'B1')}")
    print(f"  B2: {np.sum(bob_choices == 'B2')}")
    print(f"  B3: {np.sum(bob_choices == 'B3')}\n")

    print("Full 3x3 base-pair count matrix:")
    for Ai in ["A1","A2","A3"]:
        row = "  " + Ai + ": "
        for Bj in ["B1","B2","B3"]:
            row += f"{Bj}={base_counts[Ai][Bj]:3d}   "
        print(row)

    print("\nKey-generation base counts:")
    print(f"  (A1,B1): {base_counts['A1']['B1']}")
    print(f"  (A3,B3): {base_counts['A3']['B3']}")
    print(f"  Total key samples: {len(key_pairs)}\n")

    print("CHSH test base counts:")
    for pair, count in CHSH_counts.items():
        print(f"  ({pair}): {count}")
    print(f"  Total CHSH samples: {len(chsh_pairs)}\n")

    print("CHSH correlations:")
    print(f"  E(A1,B2) = {E_A1B2:.3f}")
    print(f"  E(A1,B3) = {E_A1B3:.3f}")
    print(f"  E(A2,B2) = {E_A2B2:.3f}")
    print(f"  E(A2,B3) = {E_A2B3:.3f}")
    print(f"\n  CHSH S = {S:.3f}   (classical ≤ 2, quantum ≤ 2.828)\n")

    print("Key agreement:")
    print(f"  Key length: {len(alice_key)}")
    print(f"  Agreement: {agreement:.1f}%")
    print(f"  Alice key (first 20): {alice_key[:20]}")
    print(f"  Bob key   (first 20): {bob_key[:20]}\n")

    return alice_key, bob_key, S

# Run test
simulate_e91_protocol(200)