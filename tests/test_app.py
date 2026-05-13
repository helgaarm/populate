from uuid import UUID

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_cors_preflight_for_populate_endpoint():
    response = client.options(
        "/Questionnaire/$populate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_populate_questionnaire_direct():
    payload = {
        "resourceType": "Questionnaire",
        "id": "q1",
        "status": "active",
        "item": [
            {
                "linkId": "1",
                "type": "string",
                "text": "Name",
                "initial": [{"valueString": "Alice"}],
            }
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["resourceType"] == "QuestionnaireResponse"
    assert data["questionnaire"] == "Questionnaire/q1"
    assert data["item"][0]["answer"][0]["valueString"] == "Alice"


def test_questionnaire_response_id_is_guid():
    payload = {
        "resourceType": "Questionnaire",
        "id": "q-guid",
        "status": "active",
        "item": [
            {
                "linkId": "1",
                "type": "string",
                "text": "Name",
                "initial": [{"valueString": "Alice"}],
            }
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["resourceType"] == "QuestionnaireResponse"
    UUID(data["id"], version=4)


def test_populate_questionnaire_via_parameters():
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaire",
                "resource": {
                    "resourceType": "Questionnaire",
                    "id": "q2",
                    "status": "active",
                    "item": [
                        {
                            "linkId": "1",
                            "type": "boolean",
                            "text": "Check",
                            "initial": [{"valueBoolean": True}],
                        }
                    ],
                },
            },
            {"name": "subject", "valueReference": {"reference": "Patient/123"}},
        ],
    }

    response = client.post("/fhir/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["questionnaire"] == "Questionnaire/q2"
    assert data["subject"]["reference"] == "Patient/123"
    assert data["item"][0]["answer"][0]["valueBoolean"] is True


def test_populate_with_initial_expression_patient_name():
    """Test evaluation of Patient/name initialExpression."""
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaire",
                "resource": {
                    "resourceType": "Questionnaire",
                    "id": "q3",
                    "status": "active",
                    "item": [
                        {
                            "linkId": "1",
                            "type": "string",
                            "text": "Patient Name",
                            "initialExpression": "Patient/name",
                        }
                    ],
                },
            },
            {"name": "subject", "valueReference": {"reference": "Patient/123"}},
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["item"][0]["answer"][0]["valueString"] == "Alice Smith"


def test_populate_with_initial_expression_birthdate():
    """Test evaluation of Patient/birthDate initialExpression."""
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaire",
                "resource": {
                    "resourceType": "Questionnaire",
                    "id": "q4",
                    "status": "active",
                    "item": [
                        {
                            "linkId": "1",
                            "type": "date",
                            "text": "Birth Date",
                            "initialExpression": "Patient/birthDate",
                        }
                    ],
                },
            },
            {"name": "subject", "valueReference": {"reference": "Patient/123"}},
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["item"][0]["answer"][0]["valueString"] == "1990-05-15"


def test_populate_with_observation_value_expression():
    """Test evaluation of Observation(code).value initialExpression."""
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaire",
                "resource": {
                    "resourceType": "Questionnaire",
                    "id": "q5",
                    "status": "active",
                    "item": [
                        {
                            "linkId": "1",
                            "type": "integer",
                            "text": "Systolic BP",
                            "initialExpression": "Observation(8480-6).value",
                        }
                    ],
                },
            },
            {"name": "subject", "valueReference": {"reference": "Patient/123"}},
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["item"][0]["answer"][0]["valueInteger"] == 120


def test_populate_with_gender_expression():
    """Test evaluation of Patient/gender initialExpression."""
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaire",
                "resource": {
                    "resourceType": "Questionnaire",
                    "id": "q6",
                    "status": "active",
                    "item": [
                        {
                            "linkId": "1",
                            "type": "string",
                            "text": "Gender",
                            "initialExpression": "Patient/gender",
                        }
                    ],
                },
            },
            {"name": "subject", "valueReference": {"reference": "Patient/456"}},
        ],
    }

    response = client.post("/Questionnaire/$populate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["item"][0]["answer"][0]["valueString"] == "male"
