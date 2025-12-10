import os
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService
from dotenv import load_dotenv
import numpy as np
from qiskit_aer import AerSimulator


load_dotenv()

service = QiskitRuntimeService(
    token=os.getenv("API_KEY"),
    # instance="<CRN>",  # Optional
)

qc = QuantumCircuit(1)

qc.x(0)

qc.z(0)

qc.rz(np.pi / 4, 0)

qc.measure_all()

print("-------circuit--------")
print(qc.draw())

# uncomment code below for seeing state vector

# qc.save_statevector()

# sim = AerSimulator(method="statevector")

# result = sim.run(qc).result()
# statevector = result.get_statevector()
# print("-------result--------")
# print(statevector)

print("-------measurement--------")
sim = AerSimulator()
result = sim.run(qc, shots=1024).result()
counts = result.get_counts()
print("Measurement result:", counts)

