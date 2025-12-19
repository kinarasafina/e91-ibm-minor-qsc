import os
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Configuration: Set to True for IBM Cloud, False for local simulation
USE_IBM_CLOUD = False

# Create circuit
qc = QuantumCircuit(1)
qc.x(0)
qc.z(0)
qc.rz(np.pi / 4, 0)
qc.measure_all()

print("-------circuit--------")
print(qc.draw())

# Choose execution mode
if USE_IBM_CLOUD:
    print("\n--- Using IBM Quantum Cloud ---")
    service = QiskitRuntimeService(
        token=os.getenv("API_KEY"),
        instance=os.getenv("INSTANCE_NAME"),
    )
    
    # Select backend - use least busy or a simulator
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
    
    print("\n-------measurement--------")
    # Run using Sampler primitive
    sampler = Sampler(mode=backend)
    job = sampler.run([isa_circuit], shots=1024)
    result = job.result()
    
    # Extract counts from the result
    counts = result[0].data.meas.get_counts()
    print("Measurement result:", counts)
    print(f"Job ID: {job.job_id()}")
    
else:
    print("\n--- Using Local Simulator ---")
    sim = AerSimulator()
    result = sim.run(qc, shots=1024).result()
    counts = result.get_counts()
    
    print("\n-------measurement--------")
    print("Measurement result:", counts)

