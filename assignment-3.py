import os
import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_aer import AerSimulator
from qiskit.visualization import circuit_drawer
from dotenv import load_dotenv

load_dotenv()

# Configuration: Set to True for IBM Cloud, False for local simulation
USE_IBM_CLOUD = False

# ----------------------------------------------------------------------
# E91 Protocol Configuration
# ----------------------------------------------------------------------
# E91 uses specific measurement bases:
# Alice: 0=X (a_1), 1=W (a_2), 2=Z (a_3)  where W = (Z+X)/√2
# Bob:   0=W (b_1), 1=Z (b_2), 2=V (b_3)  where V = (Z-X)/√2
# Key generation uses: a_2/b_1 (both W) and a_3/b_2 (both Z)
# CHSH test uses: a_1/b_1, a_1/b_3, a_3/b_1, a_3/b_3

# ----------------------------------------------------------------------
# One-Time Pad Encryption/Decryption
# ----------------------------------------------------------------------
def bits_to_bytes(bits):
    """Convert list of bits to bytes (8 bits per byte)."""
    n = len(bits) - (len(bits) % 8)
    bytes_list = []
    for i in range(0, n, 8):
        byte_str = ''.join(str(b) for b in bits[i:i+8])
        bytes_list.append(int(byte_str, 2))
    return bytes(bytes_list)

def xor_bytes(data, pad):
    """Elementwise XOR of two byte sequences."""
    return bytes(a ^ b for a, b in zip(data, pad))

def one_time_pad_encrypt(message, key_bits):
    """Encrypt message using one-time pad with key bits."""
    msg_bytes = message.encode('utf-8')
    key_bytes = bits_to_bytes(key_bits)
    if len(key_bytes) < len(msg_bytes):
        raise ValueError("Not enough key bits to encrypt the message.")
    pad = key_bytes[:len(msg_bytes)]
    return xor_bytes(msg_bytes, pad)

def one_time_pad_decrypt(encrypted, key_bits):
    """Decrypt message using one-time pad with key bits."""
    key_bytes = bits_to_bytes(key_bits)
    pad = key_bytes[:len(encrypted)]
    decrypted = xor_bytes(encrypted, pad)
    return decrypted.decode('utf-8', errors='replace')

# ----------------------------------------------------------------------
# E91 Protocol Functions
# ----------------------------------------------------------------------
def create_entangled_circuit():
    """Create singlet state for E91 protocol."""
    qr = QuantumRegister(2, 'q')  # Alice (q[0]), Bob (q[1])
    cr = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(qr, cr)
    
    # Create singlet state |Ψ-⟩ = (|01⟩ - |10⟩)/√2
    qc.x(qr[0])
    qc.x(qr[1])
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    
    return qc

def apply_measurement_rotations(qc, alice_basis, bob_basis):
    """Apply rotation gates before measurement based on chosen bases."""
    # Alice's measurements: 1=X, 2=W, 3=Z
    if alice_basis == 0:  # X basis (a_1)
        qc.h(0)
    elif alice_basis == 1:  # W basis (a_2) = (Z+X)/√2
        qc.s(0)
        qc.h(0)
        qc.t(0)
        qc.h(0)
    # elif alice_basis == 2: Z basis (a_3) - no rotation needed
    
    # Bob's measurements: 1=W, 2=Z, 3=V
    if bob_basis == 0:  # W basis (b_1) = (Z+X)/√2
        qc.s(1)
        qc.h(1)
        qc.t(1)
        qc.h(1)
    # elif bob_basis == 1: Z basis (b_2) - no rotation needed
    elif bob_basis == 2:  # V basis (b_3) = (Z-X)/√2
        qc.s(1)
        qc.h(1)
        qc.tdg(1)
        qc.h(1)
    
    # Measure both qubits
    qc.measure([0, 1], [0, 1])
    
    return qc

def calculate_CHSH_parameter(results):
    """Calculate CHSH parameter S from measurement results."""
    correlations = {(a, b): 0 for a in range(3) for b in range(3)}
    counts = {(a, b): 0 for a in range(3) for b in range(3)}
    
    for i in range(len(results['alice_bases'])):
        a_base = results['alice_bases'][i]
        b_base = results['bob_bases'][i]
        
        # Map outcome: 0 -> +1, 1 -> -1
        a_val = 1 if results['alice_results'][i] == 0 else -1
        b_val = 1 if results['bob_results'][i] == 0 else -1
        
        correlations[(a_base, b_base)] += a_val * b_val
        counts[(a_base, b_base)] += 1
    
    # Average correlations
    for key in correlations:
        if counts[key] > 0:
            correlations[key] /= counts[key]
    
    # CHSH for E91: Use a_1/b_1, a_1/b_3, a_3/b_1, a_3/b_3
    # S = |E(a_1,b_1) - E(a_1,b_3) + E(a_3,b_1) + E(a_3,b_3)|
    # Singlet state should give S ≈ 2√2
    S = abs(correlations.get((0, 0), 0) - correlations.get((0, 2), 0) +
            correlations.get((2, 0), 0) + correlations.get((2, 2), 0))
    
    return S, correlations

def run_e91_protocol(num_pairs=150):
    """Run E91 protocol on IBM Quantum Cloud or local simulator."""
    
    results = {
        'alice_bases': [],
        'bob_bases': [],
        'alice_results': [],
        'bob_results': [],
        'circuits': []
    }
    
    if USE_IBM_CLOUD:
        print("Initializing E91 Protocol on IBM Quantum Cloud...")
        
        # Initialize IBM Quantum service
        service = QiskitRuntimeService(
            token=os.getenv("API_KEY"),
            instance=os.getenv("INSTANCE_NAME"),
        )
        
        # Select backend
        try:
            backend = service.least_busy(simulator=False, operational=True)
            print(f"Using backend: {backend.name}")
        except:
            from qiskit_ibm_runtime.fake_provider import FakeManilaV2
            backend = FakeManilaV2()
            print(f"Using simulator: {backend.name}")
        
        # Initialize sampler and pass manager
        sampler = Sampler(mode=backend)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        
        print(f"\nGenerating {num_pairs} entangled pairs...")
        
        for i in range(num_pairs):
            # Random basis selection
            alice_basis = np.random.choice([0, 1, 2])
            bob_basis = np.random.choice([0, 1, 2])
            
            results['alice_bases'].append(alice_basis)
            results['bob_bases'].append(bob_basis)
            
            # Create and measure circuit
            qc = create_entangled_circuit()
            qc = apply_measurement_rotations(qc, alice_basis, bob_basis)
            results['circuits'].append(qc.copy())
            
            # Optimize for backend
            isa_circuit = pm.run(qc)
            
            # Run on IBM quantum backend
            job = sampler.run([isa_circuit], shots=1)
            outcome = job.result()
            
            # Extract measurement results
            counts = outcome[0].data.c.get_counts()
            bitstring = list(counts.keys())[0].replace(" ", "")
            
            # Parse results (reversed for qubit indexing)
            bitstring = bitstring[::-1]
            results['alice_results'].append(int(bitstring[0]))
            results['bob_results'].append(int(bitstring[1]))
            
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{num_pairs} pairs...")
    
    else:
        print("Initializing E91 Protocol with Local Simulator...")
        
        # Use local Aer simulator
        backend = AerSimulator()
        print(f"Using simulator: AerSimulator")
        
        print(f"\nGenerating {num_pairs} entangled pairs...")
        
        for i in range(num_pairs):
            # Random basis selection
            alice_basis = np.random.choice([0, 1, 2])
            bob_basis = np.random.choice([0, 1, 2])
            
            results['alice_bases'].append(alice_basis)
            results['bob_bases'].append(bob_basis)
            
            # Create and measure circuit
            qc = create_entangled_circuit()
            qc = apply_measurement_rotations(qc, alice_basis, bob_basis)
            results['circuits'].append(qc.copy())
            
            # Run on local simulator
            compiled = transpile(qc, backend)
            job = backend.run(compiled, shots=1)
            result = job.result()
            counts = result.get_counts()
            bitstring = list(counts.keys())[0].replace(" ", "")
            
            # Parse results (reversed for qubit indexing)
            bitstring = bitstring[::-1]
            results['alice_results'].append(int(bitstring[0]))
            results['bob_results'].append(int(bitstring[1]))
            
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{num_pairs} pairs...")
    
    # Calculate CHSH parameter
    results['S_parameter'], results['correlations'] = calculate_CHSH_parameter(results)
    
    return results

def generate_secure_key(results):
    """Extract secure key from matching basis measurements."""
    alice_key = []
    bob_key = []
    
    num_pairs = len(results['alice_bases'])
    for i in range(num_pairs):
        # Only keep results where Alice used a_2 or a_3 and Bob used matching b_1 or b_2
        # a_2/b_1 (both measure W) or a_3/b_2 (both measure Z)
        if (results['alice_bases'][i] == 1 and results['bob_bases'][i] == 0) or \
           (results['alice_bases'][i] == 2 and results['bob_bases'][i] == 1):
            alice_key.append(results['alice_results'][i])
            # For singlet state: Bob inverts his result
            bob_key.append(1 - results['bob_results'][i])
    
    return alice_key, bob_key

def visualize_results(results):
    """Visualize E91 protocol results."""
    # Show first circuit
    if results['circuits']:
        circuit_drawer(results['circuits'][0], output='mpl')
        plt.gcf().suptitle("E91 Protocol Circuit Example")
        plt.tight_layout()
    
    # Correlation matrix
    correlations = np.zeros((3, 3))
    for i in range(len(results['alice_bases'])):
        a_base = results['alice_bases'][i]
        b_base = results['bob_bases'][i]
        if results['alice_results'][i] == results['bob_results'][i]:
            correlations[a_base, b_base] += 1
    
    plt.figure(figsize=(8, 6))
    plt.imshow(correlations, cmap='Blues', interpolation='nearest')
    plt.colorbar(label='Matching Measurements')
    plt.title("Measurement Correlation Matrix")
    plt.xlabel("Bob's Bases")
    plt.ylabel("Alice's Bases")
    plt.xticks([0, 1, 2])
    plt.yticks([0, 1, 2])
    plt.tight_layout()

# ----------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Run E91 protocol
    num_pairs = 200
    results = run_e91_protocol(num_pairs=num_pairs)
    
    # Generate secure keys
    alice_key, bob_key = generate_secure_key(results)
    
    # Calculate QBER (Quantum Bit Error Rate)
    if alice_key and bob_key:
        errors = sum(1 for a, b in zip(alice_key, bob_key) if a != b)
        qber = errors / len(alice_key) if len(alice_key) > 0 else 0
    else:
        qber = None
    
    # Display results
    print("\n" + "="*70)
    print("E91 PROTOCOL RESULTS")
    print("="*70)
    print(f"\nTotal entangled pairs generated: {num_pairs}")
    print(f"Secure key length: {len(alice_key)} bits")
    print(f"\nCHSH Parameter S: {results['S_parameter']:.3f}")
    print(f"  Classical bound: S ≤ 2")
    print(f"  Quantum bound: S ≤ 2√2 ≈ 2.828")
    
    if results['S_parameter'] > 2:
        print("CHSH inequality VIOLATED - Quantum entanglement confirmed!")
    else:
        print("No CHSH violation detected")
    
    print(f"\nAlice's key (first 50): {alice_key[:50]}")
    print(f"Bob's key   (first 50): {bob_key[:50]}")
    
    if qber is not None:
        print(f"\nQuantum Bit Error Rate (QBER): {qber * 100:.2f}%")
        if qber == 0:
            print("Keys match perfectly - No eavesdropping detected!")
        elif qber < 0.11:
            print("QBER below threshold - Communication is secure")
        else:
            print("Warning: High QBER - Possible eavesdropping!")
    
    # Secret message transmission using One-Time Pad
    print("\n" + "="*70)
    print("SECRET MESSAGE TRANSMISSION (One-Time Pad)")
    print("="*70)
    
    secret_message = "HI"
    required_bits = len(secret_message) * 8
    
    # Extract only matching bits for encryption
    matching_key = [alice_key[i] for i in range(len(alice_key)) if alice_key[i] == bob_key[i]]
    
    print(f"\nOriginal key length: {len(alice_key)} bits")
    print(f"Matching bits: {len(matching_key)} bits")
    print(f"Key error rate: {((len(alice_key) - len(matching_key)) / len(alice_key) * 100):.2f}%")
    
    if len(matching_key) < required_bits:
        print(f"\nNot enough matching key bits ({len(matching_key)} bits)")
        print(f"  Need {required_bits} bits to encrypt '{secret_message}'")
        print("  Increase num_pairs for longer key")
    else:
        try:
            # Use only the matching bits
            encryption_key = matching_key[:required_bits]
            
            encrypted_msg = one_time_pad_encrypt(secret_message, encryption_key)
            decrypted_msg = one_time_pad_decrypt(encrypted_msg, encryption_key)
            
            print(f"\nOriginal Message: {secret_message}")
            print(f"Encrypted (hex):  {encrypted_msg.hex()}")
            print(f"Decrypted Message: {decrypted_msg}")
            
            # Show the key bits used for encryption
            print(f"\nKey bits used for encryption ({required_bits} matching bits):")
            print(f"Encryption key: {encryption_key}")
            
            if secret_message == decrypted_msg:
                print("\nSUCCESS: Message transmitted securely!")
            else:
                print("\nERROR: Decryption failed")
        except Exception as ex:
            print(f"\nEncryption error: {str(ex)}")
    
    # Visualize results
    print("\nGenerating visualizations...")
    visualize_results(results)
    
    plt.show()
