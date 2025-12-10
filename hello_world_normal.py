import os
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService
from dotenv import load_dotenv

load_dotenv()

service = QiskitRuntimeService(
    token=os.getenv('API_KEY'),  # Use the 44-character API_KEY you created and saved from the IBM Quantum Platform Home dashboard
    # instance="<CRN>",  # Optional
)

qc = QuantumCircuit(2)

qc.h(0)

qc.cx(0, 1)

print(qc.draw())