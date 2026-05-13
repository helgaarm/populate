# FHIR SDC Populate Simulator

FastAPI service and OpenAI Agents SDK assistant for testing a local FHIR SDC `Questionnaire/$populate` workflow. The service accepts a FHIR `Questionnaire` or `Parameters` payload, resolves supported `initialExpression` values from mock or remote FHIR data, and returns a `QuestionnaireResponse`.

## Project layout

- `app.py` - FastAPI app and populate endpoints.
- `main.py` - local Uvicorn entry point.
- `populate_service.py` - extracts questionnaires, parameters, SDC variables, and builds `QuestionnaireResponse` resources.
- `expression_evaluator.py` - evaluates supported expression forms and normalizes results.
- `fhir_variable_resolver.py` - resolves Patient paths, Observation lookups, and SDC variable references.
- `fhir_data_source.py` - data source protocol, mock source, remote FHIR source, and source router.
- `clinical_data.py` - mock patient and observation data.
- `agent.py` - OpenAI Agents SDK assistant using the same populate logic.
- `tests/` - pytest coverage for the API, clinical data, and data source routing.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the service

```powershell
python main.py
```

or run Uvicorn directly:

```powershell
python -m uvicorn app:app --reload
```

The API runs on `http://localhost:8000` by default. Swagger UI is available at `http://localhost:8000/docs`.

## Populate endpoints

- `POST /Questionnaire/$populate`
- `POST /fhir/Questionnaire/$populate`

The service accepts questionnaires and parameters in multiple forms.

### Direct Questionnaire

For simple questionnaires with only `initial` values, no subject parameter is required:

```bash
curl -X POST http://localhost:8000/Questionnaire/\$populate \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Questionnaire",
    "id": "simple",
    "status": "draft",
    "item": [
      {
        "linkId": "q1",
        "type": "string",
        "text": "Name",
        "initial": [{ "valueString": "John" }]
      }
    ]
  }'
```

### Subject in query parameters

```bash
curl -X POST "http://localhost:8000/Questionnaire/\$populate?subject=Patient/123" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Questionnaire",
    "id": "patient-name",
    "status": "draft",
    "item": [
      {
        "linkId": "name",
        "type": "string",
        "text": "Patient name",
        "initialExpression": "Patient/name"
      }
    ]
  }'
```

### Standard FHIR Parameters body

```bash
curl -X POST http://localhost:8000/Questionnaire/\$populate \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Parameters",
    "parameter": [
      {
        "name": "questionnaire",
        "resource": {
          "resourceType": "Questionnaire",
          "id": "patient-name",
          "status": "draft",
          "item": [
            {
              "linkId": "name",
              "type": "string",
              "text": "Patient name",
              "initialExpression": "Patient/name"
            }
          ]
        }
      },
      {
        "name": "subject",
        "valueReference": { "reference": "Patient/123" }
      },
      {
        "name": "encounter",
        "valueReference": { "reference": "Encounter/e1" }
      }
    ]
  }'
```

## Supported parameters

- `subject` - Patient reference used by expression evaluation.
- `encounter` - optional Encounter reference copied into the response and made available to expressions.
- `context` - optional context value copied into the response and made available to expressions.
- `source` - optional data source selector. Supported values: `mock`, `local`, `remote`, `ehr`, or `fhir`.
- `sourceUrl` - optional remote FHIR base URL. May be passed in the body parameters or query string.

`sourceUrl` takes precedence over `source`. If `source` is `remote`, `ehr`, or `fhir`, the app uses `REMOTE_FHIR_BASE_URL` when that environment variable is configured. Otherwise it falls back to mock data.

## Expression evaluation

The service supports FHIRPath-like expressions through item-level `initialExpression` fields and FHIR SDC `variable` extensions. Supported patterns include:

- `Patient/name`
- `Patient/birthDate`
- `Patient/gender`
- `Observation(code).value`
- `%variableName.entry.first().resource.value`
- SDC variable definitions using `Observation?patient=...&code=...`

Complete SDC vital-signs questionnaire example:

```json
{
  "resourceType": "Questionnaire",
  "id": "vital-signs-sdc-questionnaire",
  "meta": {
    "profile": [
      "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire"
    ]
  },
  "url": "http://example.org/fhir/Questionnaire/vital-signs",
  "version": "1.0.0",
  "name": "VitalSignsQuestionnaire",
  "title": "Vital Signs Questionnaire",
  "status": "draft",
  "subjectType": [
    "Patient"
  ],
  "extension": [
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "bodyTemperatureObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|8310-5&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "heartRateObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|8867-4&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "respiratoryRateObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|9279-1&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "oxygenSaturationObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|59408-5&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "systolicBpObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|8480-6&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "diastolicBpObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|8462-4&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "bodyWeightObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|29463-7&_sort=-date&_count=1"
      }
    },
    {
      "url": "http://hl7.org/fhir/StructureDefinition/variable",
      "valueExpression": {
        "name": "bodyHeightObs",
        "language": "application/x-fhir-query",
        "expression": "Observation?patient={{%subject.id}}&code=http://loinc.org|8302-2&_sort=-date&_count=1"
      }
    }
  ],
  "item": [
    {
      "linkId": "vitals",
      "text": "Vital signs",
      "type": "group",
      "item": [
        {
          "linkId": "body-temperature",
          "text": "Body temperature",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "8310-5",
              "display": "Body temperature"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%bodyTemperatureObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "heart-rate",
          "text": "Heart rate",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "8867-4",
              "display": "Heart rate"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%heartRateObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "respiratory-rate",
          "text": "Respiratory rate",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "9279-1",
              "display": "Respiratory rate"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%respiratoryRateObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "oxygen-saturation",
          "text": "Oxygen saturation SpO2",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "59408-5",
              "display": "Oxygen saturation in Arterial blood by Pulse oximetry"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%oxygenSaturationObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "systolic-bp",
          "text": "Systolic blood pressure",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "8480-6",
              "display": "Systolic blood pressure"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%systolicBpObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "diastolic-bp",
          "text": "Diastolic blood pressure",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "8462-4",
              "display": "Diastolic blood pressure"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%diastolicBpObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "body-weight",
          "text": "Body weight",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "29463-7",
              "display": "Body weight"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%bodyWeightObs.entry.first().resource.value"
              }
            }
          ]
        },
        {
          "linkId": "body-height",
          "text": "Body height",
          "type": "quantity",
          "code": [
            {
              "system": "http://loinc.org",
              "code": "8302-2",
              "display": "Body height"
            }
          ],
          "extension": [
            {
              "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
              "valueExpression": {
                "language": "text/fhirpath",
                "expression": "%bodyHeightObs.entry.first().resource.value"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

When populated with `subject: Patient/123`, the vital-sign items resolve to:

- `body-temperature` - `37.0`
- `heart-rate` - `72`
- `respiratory-rate` - `16`
- `oxygen-saturation` - `98`
- `systolic-bp` - `120`
- `diastolic-bp` - `80`
- `body-weight` - `70`
- `body-height` - `170`

## Mock clinical data

`Patient/123` is Alice Smith:

- Birth date: `1990-05-15`
- Gender: `female`
- Vitals: systolic BP `120`, diastolic BP `80`, heart rate `72`, respiratory rate `16`, oxygen saturation `98`, temperature `37.0 Cel`
- Anthropometrics: weight `70 kg`, height `170 cm`

`Patient/456` is Robert Jones:

- Birth date: `1985-03-22`
- Gender: `male`
- Anthropometrics: height `170 cm`

## Agent assistant

`agent.py` provides a small OpenAI Agents SDK assistant that can answer questions about the mock clinical data and call the same questionnaire population logic used by the FastAPI service.

```powershell
python agent.py "Show me a summary for Patient/123"
```

The agent reads `OPENAI_API_KEY` from the environment, `.env.local`, or `.env`.

## Diagrams

- `populate_architecture.mmd` - end-to-end populate architecture.
- `populate_components.mmd` - main modules and responsibilities.
- `data_source_selection.mmd` - source routing decision tree.
- `expression_evaluation_pipeline.mmd` - expression and variable resolution flow.
- `fhir_resource_relationships.mmd` - FHIR resource relationships used by populate.

## Tests

```powershell
pytest
```
