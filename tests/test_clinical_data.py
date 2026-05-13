"""Tests for clinical data and expression evaluation."""

from clinical_data import MockPatientData
from expression_evaluator import create_evaluator


def test_mock_patient_data_retrieval():
    """Test retrieving patient data."""
    data = MockPatientData()
    patient = data.get_patient("Patient/123")
    assert patient is not None
    assert patient["id"] == "123"
    assert patient["gender"] == "female"


def test_mock_patient_name():
    """Test retrieving patient name."""
    data = MockPatientData()
    name = data.get_patient_name("Patient/123")
    assert name == "Alice Smith"


def test_mock_patient_birthdate():
    """Test retrieving patient birth date."""
    data = MockPatientData()
    birthdate = data.get_patient_birthdate("Patient/123")
    assert birthdate == "1990-05-15"


def test_mock_observations():
    """Test retrieving observations."""
    data = MockPatientData()
    obs = data.get_observations("Patient/123")
    assert len(obs) == 8
    assert obs[0]["code"] == "8480-6"


def test_mock_observation_value_by_code():
    """Test retrieving observation value by code."""
    data = MockPatientData()
    value = data.get_latest_observation_value("Patient/123", "8480-6")
    assert value == 120


def test_expression_evaluator_patient_name():
    """Test evaluating Patient/name expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/123"}}
    result = evaluator.evaluate("Patient/name", context)
    assert result == "Alice Smith"


def test_expression_evaluator_patient_name_family_dot_path():
    """Test evaluating Patient.name.family expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/123"}}
    result = evaluator.evaluate("Patient.name.family", context)
    assert result == "Smith"


def test_expression_evaluator_patient_name_given_dot_path():
    """Test evaluating Patient.name.given expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/123"}}
    result = evaluator.evaluate("Patient.name.given", context)
    assert result == "Alice"


def test_expression_evaluator_patient_birthdate():
    """Test evaluating Patient/birthDate expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/123"}}
    result = evaluator.evaluate("Patient/birthDate", context)
    assert result == "1990-05-15"


def test_expression_evaluator_observation_value():
    """Test evaluating Observation(code).value expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/123"}}
    result = evaluator.evaluate("Observation(8480-6).value", context)
    assert result == 120


def test_expression_evaluator_patient_gender():
    """Test evaluating Patient/gender expression."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/456"}}
    result = evaluator.evaluate("Patient/gender", context)
    assert result == "male"


def test_expression_evaluator_no_context():
    """Test that evaluator returns None when context is missing."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    result = evaluator.evaluate("Patient/name", None)
    assert result is None


def test_expression_evaluator_nonexistent_patient():
    """Test that evaluator returns None for nonexistent patient."""
    data = MockPatientData()
    evaluator = create_evaluator(data)
    context = {"subject": {"reference": "Patient/999"}}
    result = evaluator.evaluate("Patient/name", context)
    assert result is None
