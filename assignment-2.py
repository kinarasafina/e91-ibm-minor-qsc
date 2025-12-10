from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
 
# Create a new circuit with two qubits
qc = QuantumCircuit(2)
 
# Add a Hadamard gate to qubit 0
qc.h(0)
 
# Perform a controlled-X gate on qubit 1, controlled by qubit 0
qc.cx(0, 1)
 
# Measure both qubits (adds two classical bits automatically)
qc.measure_all()

# Return a drawing of the circuit using MatPlotLib ("mpl").
# These guides are written by using Jupyter notebooks, which
# display the output of the last line of each cell.
# If you're running this in a script, use `print(qc.draw())` to
# print a text drawing.
print(qc.draw())

# Try to run the circuit on a local Aer simulator (if available)
try:
	# Qiskit Aer may be provided either via qiskit_aer or qiskit.Aer
	try:
		from qiskit_aer import AerSimulator
		from qiskit import transpile
		simulator = AerSimulator()
	except Exception:
		from qiskit import Aer
		from qiskit import transpile
		simulator = Aer.get_backend('aer_simulator')

	compiled = transpile(qc, simulator)
	job = simulator.run(compiled, shots=1024)
	result = job.result()
	counts = result.get_counts()
	print("Counts:", counts)
except Exception as e:
	print("Simulator not available or run failed:", e)