from __future__ import annotations

import httpx
from typing import Any, Dict, List, Mapping, Optional, Protocol

from clinical_data import MockPatientData


class FhirDataSource(Protocol):
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_patient_name(self, patient_id: str) -> Optional[str]:
        ...

    def get_patient_birthdate(self, patient_id: str) -> Optional[str]:
        ...

    def get_patient_gender(self, patient_id: str) -> Optional[str]:
        ...

    def get_observations(self, patient_id: str, code: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def get_latest_observation(self, patient_id: str, code: str) -> Optional[Dict[str, Any]]:
        ...

    def get_latest_observation_value(self, patient_id: str, code: str) -> Optional[Any]:
        ...


class MockFhirDataSource:
    def __init__(self, mock_data: MockPatientData) -> None:
        self.mock_data = mock_data

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self.mock_data.get_patient(patient_id)

    def get_patient_name(self, patient_id: str) -> Optional[str]:
        return self.mock_data.get_patient_name(patient_id)

    def get_patient_birthdate(self, patient_id: str) -> Optional[str]:
        return self.mock_data.get_patient_birthdate(patient_id)

    def get_patient_gender(self, patient_id: str) -> Optional[str]:
        return self.mock_data.get_patient_gender(patient_id)

    def get_observations(self, patient_id: str, code: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.mock_data.get_observations(patient_id, code)

    def get_latest_observation(self, patient_id: str, code: str) -> Optional[Dict[str, Any]]:
        return self.mock_data.get_latest_observation(patient_id, code)

    def get_latest_observation_value(self, patient_id: str, code: str) -> Optional[Any]:
        return self.mock_data.get_latest_observation_value(patient_id, code)


class RemoteFhirDataSource:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout)

    def _fetch_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.client.get(
                url,
                params=params,
                headers={"Accept": "application/fhir+json,application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        patient_id = patient_id.split("/")[-1]
        resource = self._fetch_json(f"Patient/{patient_id}")
        if resource and resource.get("resourceType") == "Patient":
            return resource
        return None

    def get_patient_name(self, patient_id: str) -> Optional[str]:
        patient = self.get_patient(patient_id)
        if not patient:
            return None

        name = patient.get("name")
        if not name or not isinstance(name, list):
            return None

        first_name = name[0]
        given = first_name.get("given") or []
        family = first_name.get("family", "")
        if isinstance(given, list):
            given = " ".join(str(part) for part in given if part is not None)

        return f"{given} {family}".strip() or None

    def get_patient_birthdate(self, patient_id: str) -> Optional[str]:
        patient = self.get_patient(patient_id)
        return patient.get("birthDate") if patient else None

    def get_patient_gender(self, patient_id: str) -> Optional[str]:
        patient = self.get_patient(patient_id)
        return patient.get("gender") if patient else None

    def get_observations(self, patient_id: str, code: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, str] = {"patient": patient_id}
        if code:
            params["code"] = code

        bundle = self._fetch_json("Observation", params=params)
        if not bundle or bundle.get("resourceType") != "Bundle":
            return []

        entries = bundle.get("entry") or []
        return [entry.get("resource") for entry in entries if isinstance(entry, dict) and entry.get("resource")]

    def get_latest_observation(self, patient_id: str, code: str) -> Optional[Dict[str, Any]]:
        observations = self.get_observations(patient_id, code)
        if not observations:
            return None

        observations.sort(key=lambda obs: obs.get("effectiveDateTime", ""), reverse=True)
        return observations[0]

    def get_latest_observation_value(self, patient_id: str, code: str) -> Optional[Any]:
        observation = self.get_latest_observation(patient_id, code)
        if not observation:
            return None

        if "valueQuantity" in observation:
            return observation["valueQuantity"].get("value")
        return observation.get("value")


class TypedDataSourceRouter:
    """Routes FHIR requests to resource-type-specific data sources."""

    def __init__(
        self,
        default_source: FhirDataSource,
        endpoints: Optional[Dict[str, str]] = None,
        default_remote_url: Optional[str] = None,
    ) -> None:
        """Initialize router with optional resource-type-specific endpoints.
        
        Args:
            default_source: Default data source for fallback.
            endpoints: Dict mapping resource types (e.g., "patient", "observation") to URLs.
            default_remote_url: Fallback remote URL if not in endpoints.
        """
        self.default_source = default_source
        self.endpoints = endpoints or {}
        self.default_remote_url = default_remote_url
        self._source_cache: Dict[str, FhirDataSource] = {}

    def get_source_for_type(self, resource_type: str) -> FhirDataSource:
        """Get the appropriate data source for a resource type.
        
        Priority:
        1. Explicit endpoint for resource_type in extension
        2. Shared endpoint alias 'fhir'
        3. First configured endpoint in the extension
        4. Default remote URL (shared endpoint)
        5. Default source (mock)
        """
        if resource_type in self._source_cache:
            return self._source_cache[resource_type]

        # Check for explicit endpoint for this resource type
        if resource_type in self.endpoints:
            url = self.endpoints[resource_type]
            source = RemoteFhirDataSource(url)
            self._source_cache[resource_type] = source
            return source

        # Allow a shared alias endpoint for all resource types
        if "fhir" in self.endpoints:
            source = RemoteFhirDataSource(self.endpoints["fhir"])
            self._source_cache[resource_type] = source
            return source

        # Fallback to first available endpoint for older extension structures
        if self.endpoints:
            first_url = next(iter(self.endpoints.values()))
            source = RemoteFhirDataSource(first_url)
            self._source_cache[resource_type] = source
            return source

        # Fallback to default remote URL
        if self.default_remote_url:
            source = RemoteFhirDataSource(self.default_remote_url)
            self._source_cache[resource_type] = source
            return source

        # Fallback to default source
        return self.default_source


class DataSourceRouter:
    """Route FHIR requests to the configured data source backend."""

    def __init__(
        self,
        default_source: FhirDataSource,
        default_remote_url: Optional[str] = None,
    ) -> None:
        self.default_source = default_source
        self.default_remote_url = default_remote_url

    def select_source(
        self,
        parameters: Dict[str, Any],
        query_params: Mapping[str, str],
        questionnaire_data: Optional[Dict[str, Any]] = None,
    ) -> FhirDataSource | TypedDataSourceRouter:
        """Select data source based on questionnaire extension, parameters, or query params.
        
        If questionnaire has resource-type-specific endpoints, returns a TypedDataSourceRouter.
        Otherwise returns a single FhirDataSource for backward compatibility.
        
        Priority order:
        1. Data endpoints extension in questionnaire (with resource type support)
        2. sourceUrl parameter or query param
        3. source parameter or query param (e.g., 'remote', 'mock')
        4. REMOTE_FHIR_BASE_URL environment variable
        5. Default source
        """
        # Check questionnaire for typed data endpoints extension
        if questionnaire_data:
            from populate_service import PopulateService
            endpoints = PopulateService.extract_data_endpoints(questionnaire_data)
            if endpoints:
                # Return a typed router for resource-type-specific sources
                return TypedDataSourceRouter(
                    default_source=self.default_source,
                    endpoints=endpoints,
                    default_remote_url=self.default_remote_url,
                )

        # Fallback to old behavior for single URL selection
        source_hint = self._get_source_hint(parameters, query_params)
        if source_hint is None:
            return self.default_source

        normalized = source_hint.strip().lower()
        if normalized in {"mock", "local"}:
            return self.default_source

        if normalized in {"remote", "ehr", "fhir"} and self.default_remote_url:
            return RemoteFhirDataSource(self.default_remote_url)

        if source_hint.startswith("http://") or source_hint.startswith("https://"):
            return RemoteFhirDataSource(source_hint)

        return self.default_source

    def _get_source_hint(
        self,
        parameters: Dict[str, Any],
        query_params: Mapping[str, str],
    ) -> Optional[str]:
        """Get source hint from parameters or query params."""
        source_hint = parameters.get("sourceUrl")
        if isinstance(source_hint, str) and source_hint.strip():
            return source_hint

        source_hint = query_params.get("sourceUrl")
        if isinstance(source_hint, str) and source_hint.strip():
            return source_hint

        source_hint = parameters.get("source")
        if isinstance(source_hint, str) and source_hint.strip():
            return source_hint

        source_hint = query_params.get("source")
        if isinstance(source_hint, str) and source_hint.strip():
            return source_hint

        return None
