"""Mock clinical data store for populating questionnaires."""

from __future__ import annotations

from typing import Any, Dict, Optional


class MockPatientData:
    """Mock patient and clinical data store."""

    def __init__(self) -> None:
        self.patients: Dict[str, Dict[str, Any]] = {
            "Patient/123": {
                "id": "123",
                "name": [{"given": ["Alice"], "family": "Smith"}],
                "birthDate": "1990-05-15",
                "gender": "female",
                "address": [{"city": "Portland", "state": "OR"}],
                "contact": [{"system": "phone", "value": "503-555-0123"}],
            },
            "Patient/456": {
                "id": "456",
                "name": [{"given": ["Robert"], "family": "Jones"}],
                "birthDate": "1985-03-22",
                "gender": "male",
                "address": [{"city": "Seattle", "state": "WA"}],
                "contact": [{"system": "email", "value": "robert.jones@example.com"}],
            },
        }

        self.observations: Dict[str, list[Dict[str, Any]]] = {
            "Patient/123": [
                {
                    "id": "obs-1",
                    "code": "8480-6",
                    "display": "Systolic Blood Pressure",
                    "value": 120,
                    "unit": "mmHg",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-2",
                    "code": "8462-4",
                    "display": "Diastolic Blood Pressure",
                    "value": 80,
                    "unit": "mmHg",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-3",
                    "code": "8867-4",
                    "display": "Heart rate",
                    "value": 72,
                    "unit": "/min",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-4",
                    "code": "9279-1",
                    "display": "Respiratory rate",
                    "value": 16,
                    "unit": "/min",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-5",
                    "code": "59408-5",
                    "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
                    "value": 98,
                    "unit": "%",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-6",
                    "code": "8310-5",
                    "display": "Body temperature",
                    "value": 37.0,
                    "unit": "Cel",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-7",
                    "code": "29463-7",
                    "display": "Body weight",
                    "value": 70,
                    "unit": "kg",
                    "effectiveDateTime": "2026-05-10",
                },
                {
                    "id": "obs-8",
                    "code": "8302-2",
                    "display": "Body height",
                    "value": 170,
                    "unit": "cm",
                    "effectiveDateTime": "2026-05-10",
                },
            ],
            "Patient/456": [
                {
                    "id": "obs-9",
                    "code": "8302-2",
                    "display": "Body height",
                    "value": 170,
                    "unit": "cm",
                    "effectiveDateTime": "2026-05-08",
                }
            ],
        }

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve patient data by ID."""
        return self.patients.get(patient_id)

    def get_patient_name(self, patient_id: str) -> Optional[str]:
        """Get patient's full name."""
        patient = self.get_patient(patient_id)
        if not patient or not patient.get("name"):
            return None

        name_parts = patient["name"][0]
        given = " ".join(name_parts.get("given", []))
        family = name_parts.get("family", "")
        return f"{given} {family}".strip()

    def get_patient_birthdate(self, patient_id: str) -> Optional[str]:
        """Get patient's birth date."""
        patient = self.get_patient(patient_id)
        return patient.get("birthDate") if patient else None

    def get_patient_gender(self, patient_id: str) -> Optional[str]:
        """Get patient's gender."""
        patient = self.get_patient(patient_id)
        return patient.get("gender") if patient else None

    def get_observations(self, patient_id: str, code: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get patient observations, optionally filtered by code."""
        obs = self.observations.get(patient_id, [])
        if code:
            obs = [o for o in obs if o.get("code") == code]
        return obs

    def get_latest_observation_value(self, patient_id: str, code: str) -> Optional[Any]:
        """Get the value of the latest observation for a given code."""
        obs = self.get_observations(patient_id, code)
        if obs:
            return obs[-1].get("value")
        return None

    def get_latest_observation(self, patient_id: str, code: str) -> Optional[Dict[str, Any]]:
        """Get the latest observation for a given code."""
        obs = self.get_observations(patient_id, code)
        return obs[-1] if obs else None


# Global instance
mock_data = MockPatientData()
