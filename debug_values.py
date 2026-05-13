#!/usr/bin/env python
"""Debug why Patient/123 values aren't populating."""

import json
from clinical_data import mock_data
from expression_evaluator import create_evaluator

# Check if Patient/123 exists and has data
print("=" * 80)
print("CHECKING CLINICAL DATA")
print("=" * 80)

patient = mock_data.get_patient("Patient/123")
print(f"Patient: {json.dumps(patient, indent=2)}\n")

obs = mock_data.get_observations("Patient/123")
print(f"Observations count: {len(obs)}")
for o in obs:
    print(f"  - {o['code']}: {o['value']} {o.get('unit', '')}")

print("\n" + "=" * 80)
print("TESTING EXPRESSION EVALUATION")
print("=" * 80)

evaluator = create_evaluator(mock_data)

# Set up context
context = {"subject": {"reference": "Patient/123"}}

# Test expressions
test_expressions = [
    "Patient/name",
    "Patient/birthDate",
    "Patient/gender",
    "Observation(8480-6).value",
    "Observation(8867-4).value",
]

for expr in test_expressions:
    result = evaluator.evaluate(expr, context)
    print(f"{expr:40} => {result}")

print("\n" + "=" * 80)
print("TESTING VARIABLE EXPRESSIONS")
print("=" * 80)

# Set variables and test
evaluator2 = create_evaluator(mock_data)
variables = {
    "systolicBpObs": "Observation?patient={{%subject.id}}&code=http://loinc.org|8480-6"
}
evaluator2.set_variables(variables)

var_expr = "%systolicBpObs.entry.first().resource.value"
result = evaluator2.evaluate(var_expr, context)
print(f"{var_expr:50} => {result}")
