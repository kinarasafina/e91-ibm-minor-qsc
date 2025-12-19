import os
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2 as Estimator, SamplerV2 as Sampler
from qiskit_aer import AerSimulator
from dotenv import load_dotenv

load_dotenv()

# Configuration: Set to True for IBM Cloud, False for local simulation
USE_IBM_CLOUD = False

# Create a new circuit with two qubits (Bell state)
qc = QuantumCircuit(2)

# Add a Hadamard gate to qubit 0
qc.h(0)

# Perform a controlled-X gate on qubit 1, controlled by qubit 0
qc.cx(0, 1)

print("-------circuit--------")
print(qc.draw())

if USE_IBM_CLOUD:
    print("\n--- Using IBM Quantum Cloud ---")
    
    service = QiskitRuntimeService(
        token=os.getenv("API_KEY"),
        instance=os.getenv("INSTANCE_NAME"),
    )
    
    # Set up observables to measure entanglement
    observables_labels = ["IZ", "IX", "ZI", "XI", "ZZ", "XX"]
    observables = [SparsePauliOp(label) for label in observables_labels]
    
    # Select backend
    try:
        backend = service.least_busy(simulator=False, operational=True)
        print(f"Using backend: {backend.name}")
    except:
        from qiskit_ibm_runtime.fake_provider import FakeManilaV2
        backend = FakeManilaV2()
        print(f"Using simulator: {backend.name}")
    
    # Optimize circuit for the backend
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(qc)
    
    # Map observables to the circuit layout
    mapped_observables = [
        observable.apply_layout(isa_circuit.layout) for observable in observables
    ]
    
    print("\n-------estimator results (expectation values)--------")
    # Run using Estimator primitive to get expectation values
    estimator = Estimator(mode=backend)
    estimator.options.default_shots = 5000
    job = estimator.run([(isa_circuit, mapped_observables)])
    result = job.result()
    
    # Display expectation values
    pub_result = result[0]
    values = pub_result.data.evs
    
    print("Observable expectation values:")
    for label, value in zip(observables_labels, values):
        print(f"  <{label}> = {value:.3f}")
    
    print(f"\nJob ID: {job.job_id()}")
    print("\nNote: For entangled Bell state |00⟩+|11⟩, expect:")
    print("  Independent measurements (IZ, IX, ZI, XI) ≈ 0")
    print("  Correlations (ZZ, XX) ≈ 1")
    
    # Also run with Sampler to get measurement counts
    print("\n-------sampler results (measurement counts)--------")
    qc_with_meas = QuantumCircuit(2)
    qc_with_meas.h(0)
    qc_with_meas.cx(0, 1)
    qc_with_meas.measure_all()
    
    isa_circuit_meas = pm.run(qc_with_meas)
    sampler = Sampler(mode=backend)
    job_sampler = sampler.run([isa_circuit_meas], shots=1024)
    result_sampler = job_sampler.result()
    
    counts = result_sampler[0].data.meas.get_counts()
    print("Measurement counts:", counts)
    print("Expected: roughly equal counts of '00' and '11' (entanglement)")
    
else:
    print("\n--- Using Local Simulator ---")
    
    # Measure both qubits
    qc.measure_all()
    
    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    job = simulator.run(compiled, shots=1024)
    result = job.result()
    counts = result.get_counts()
    
    print("\n-------measurement counts--------")
    print("Counts:", counts)
    print("Expected: roughly equal counts of '00' and '11' (entanglement)")