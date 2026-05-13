"""OpenAI Agents SDK assistant for the FHIR SDC populate simulator."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from agents import Agent, Runner, function_tool

from clinical_data import mock_data
from expression_evaluator import create_evaluator
from fhir_data_source import MockFhirDataSource
from populate_service import PopulateService


PROJECT_ROOT = Path(__file__).resolve().parent


def load_local_env() -> None:
    """Load simple KEY=VALUE entries from local env files without extra dependencies."""
    for env_path in (PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"):
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _normalize_patient_reference(patient_reference: str) -> str:
    patient_reference = patient_reference.strip()
    if "/" in patient_reference:
        return patient_reference
    return f"Patient/{patient_reference}"


@function_tool
def get_patient_summary(patient_reference: str) -> str:
    """Return demographic details for a mock patient reference such as Patient/123."""
    reference = _normalize_patient_reference(patient_reference)
    patient = mock_data.get_patient(reference)
    if patient is None:
        return json.dumps({"error": f"No mock patient found for {reference}"})

    summary = {
        "reference": reference,
        "name": mock_data.get_patient_name(reference),
        "birthDate": patient.get("birthDate"),
        "gender": patient.get("gender"),
        "address": patient.get("address", []),
        "contact": patient.get("contact", []),
    }
    return json.dumps(summary, indent=2)


@function_tool
def get_latest_observation(patient_reference: str, loinc_code: str) -> str:
    """Return the latest mock Observation for a patient and LOINC code."""
    reference = _normalize_patient_reference(patient_reference)
    observation = mock_data.get_latest_observation(reference, loinc_code.strip())
    if observation is None:
        return json.dumps(
            {
                "error": (
                    f"No mock observation found for {reference} "
                    f"with code {loinc_code}"
                )
            }
        )
    return json.dumps(observation, indent=2)


@function_tool
def populate_questionnaire(questionnaire_json: str, subject: Optional[str] = None) -> str:
    """Populate a FHIR Questionnaire or Parameters JSON payload with mock clinical data."""
    try:
        payload = json.loads(questionnaire_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc.msg}"})

    if not isinstance(payload, dict):
        return json.dumps({"error": "Questionnaire payload must be a JSON object."})

    try:
        questionnaire, expressions, variables = PopulateService.get_questionnaire_resource(payload)
        parameters: Dict[str, Any] = PopulateService.extract_parameters(payload)
        if subject and not parameters.get("subject"):
            parameters["subject"] = subject

        evaluator = create_evaluator(MockFhirDataSource(mock_data))
        evaluator.set_variables(variables)
        response = PopulateService.build_questionnaire_response(
            questionnaire, parameters, expressions, variables, evaluator
        )
        return json.dumps(response.model_dump(exclude_none=True), indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


populate_agent = Agent(
    name="FHIR SDC Populate Assistant",
    instructions=(
        "You help developers and clinicians test a local FHIR SDC "
        "Questionnaire/$populate simulator. Use the tools for patient data, "
        "observations, and questionnaire population when the user asks about "
        "mock clinical data or wants a questionnaire populated. Be concise, "
        "state which mock patient or LOINC code you used, and do not invent "
        "clinical data that is not returned by the tools."
    ),
    tools=[get_patient_summary, get_latest_observation, populate_questionnaire],
)


def run_agent(prompt: str) -> str:
    """Run the populate assistant and return its final output."""
    load_local_env()
    result = Runner.run_sync(populate_agent, prompt)
    return str(result.final_output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FHIR populate agent.")
    parser.add_argument("prompt", nargs="+", help="Prompt to send to the agent.")
    args = parser.parse_args()

    print(run_agent(" ".join(args.prompt)))


if __name__ == "__main__":
    main()
