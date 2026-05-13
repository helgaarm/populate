from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from fhir.resources.parameters import Parameters
from fhir.resources.questionnaire import Questionnaire
from fhir.resources.questionnaireresponse import QuestionnaireResponse

from clinical_data import mock_data
from expression_evaluator import create_evaluator
from fhir_data_source import DataSourceRouter, MockFhirDataSource
from populate_service import PopulateService


app = FastAPI(
    title="FHIR SDC Populate Simulator",
    version="0.2.0",
    description="A FastAPI service that simulates the FHIR SDC Questionnaire/$populate operation using FHIR resource models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "message": "FHIR SDC Populate Simulator",
        "version": "0.2.0",
        "endpoints": {
            "populate": {
                "method": "POST",
                "path": "/Questionnaire/$populate",
                "description": "Populate a questionnaire with patient data",
                "parameters": {
                    "subject": "Optional query param: Patient reference (e.g., Patient/123)",
                    "encounter": "Optional query param: Encounter reference",
                },
            },
            "docs": {
                "method": "GET",
                "path": "/docs",
                "description": "Interactive API documentation (Swagger UI)",
            },
        },
        "mock_patients": ["Patient/123 (Alice Smith)", "Patient/456 (Robert Jones)"],
    }


@app.post("/Questionnaire/$populate", response_class=JSONResponse)
@app.post("/fhir/Questionnaire/$populate", response_class=JSONResponse)
async def populate_questionnaire(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    subject: Optional[str] = Query(None, description="Default subject reference if not in payload (e.g., Patient/123)"),
    encounter: Optional[str] = Query(None, description="Default encounter reference if not in payload"),
) -> Dict[str, Any]:
    try:
        questionnaire, expressions, variables = PopulateService.get_questionnaire_resource(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        parameters = PopulateService.extract_parameters(payload)

        if not parameters.get("subject") and subject:
            parameters["subject"] = subject
        if not parameters.get("encounter") and encounter:
            parameters["encounter"] = encounter

        for key, value in request.query_params.items():
            if key in {"subject", "encounter"}:
                continue
            if key not in parameters:
                parameters[key] = value

        default_remote_url = os.environ.get("REMOTE_FHIR_BASE_URL")
        router = DataSourceRouter(
            default_source=MockFhirDataSource(mock_data),
            default_remote_url=default_remote_url,
        )
        source = router.select_source(parameters, request.query_params)

        evaluator = create_evaluator(source)
        evaluator.set_variables(variables)

        questionnaire_response = PopulateService.build_questionnaire_response(
            questionnaire, parameters, expressions, variables, evaluator
        )
        return questionnaire_response.model_dump(exclude_none=True)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())


