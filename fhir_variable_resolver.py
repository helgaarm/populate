from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import parse_qs

from fhir_data_source import FhirDataSource


class FhirVariableResolver:
    """Resolve patient resources, observation queries, and SDC variables."""

    def __init__(self, data_source: Union[FhirDataSource, Any]) -> None:
        # Accept Any type to avoid circular imports with TypedDataSourceRouter
        self.data_source = data_source
        self.variables: Dict[str, Any] = {}

    def set_variables(self, variables: Dict[str, Any]) -> None:
        self.variables = variables

    def _get_source_for_type(self, resource_type: str) -> FhirDataSource:
        """Get the appropriate data source for a resource type.
        
        If data_source is a TypedDataSourceRouter, routes to the appropriate endpoint.
        Otherwise returns the single data source.
        """
        # Import here to avoid circular imports
        from fhir_data_source import TypedDataSourceRouter
        
        if isinstance(self.data_source, TypedDataSourceRouter):
            return self.data_source.get_source_for_type(resource_type)
        return self.data_source

    def set_variables(self, variables: Dict[str, Any]) -> None:
        self.variables = variables

    def resolve_expression(
        self, expression: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[Any, str]]:
        if not expression or context is None:
            return None

        if expression.startswith("%"):
            return self._resolve_variable_expression(expression, context)

        if expression.startswith("Patient/") or expression.startswith("Patient."):
            return self._resolve_patient_expression(expression[8:], context)

        if expression.startswith("Observation("):
            return self._resolve_observation_expression(expression, context)

        return None

    def _resolve_patient_expression(
        self, expression: str, context: Dict[str, Any]
    ) -> Optional[Tuple[Any, str]]:
        patient_id = self._get_subject_reference(context)
        if not patient_id:
            return None

        source = self._get_source_for_type("patient")
        patient = source.get_patient(patient_id)
        if not patient:
            return None

        path = expression.replace("/", ".").lstrip(".")
        return patient, path

    def _resolve_observation_expression(
        self, expression: str, context: Dict[str, Any]
    ) -> Optional[Tuple[Any, str]]:
        match = re.match(r"Observation\(([\w\-]+)\)(?:\.(.+))?$", expression)
        if not match:
            return None

        code = match.group(1)
        path = match.group(2) or ""
        patient_id = self._get_subject_reference(context)
        if not patient_id:
            return None

        source = self._get_source_for_type("observation")
        observation = source.get_latest_observation(patient_id, code)
        if not observation:
            return None

        return observation, path

    def _resolve_variable_expression(
        self, expression: str, context: Dict[str, Any]
    ) -> Optional[Tuple[Any, str]]:
        match = re.match(r"%(\w+)(?:\.(.+))?$", expression)
        if not match:
            return None

        variable_name = match.group(1)
        variable_path = match.group(2) or ""
        variable_definition = self.variables.get(variable_name)
        if variable_definition is None:
            return None

        resolved = self._resolve_variable_definition(variable_definition, context)
        if resolved is None:
            return None

        if isinstance(resolved, tuple):
            resource, resource_path = resolved
            path = resource_path
            if variable_path:
                path = ".".join(filter(None, [resource_path, variable_path]))
            return resource, path

        return resolved, variable_path

    def _resolve_variable_definition(
        self, definition: Any, context: Dict[str, Any]
    ) -> Optional[Any]:
        if isinstance(definition, str):
            if definition.startswith("Observation?"):
                return self._resolve_observation_query(definition, context)

            if definition.startswith("Patient/") or definition.startswith("Patient.") or definition.startswith("Observation("):
                return self.resolve_expression(definition, context)

            return definition

        return definition

    def _resolve_observation_query(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        parts = query.split("?", 1)
        if len(parts) != 2:
            return None

        query_string = parts[1]
        query_params = parse_qs(query_string, keep_blank_values=True)

        subject_id = self._get_subject_reference(context)
        if not subject_id and "subject" in query_params:
            subject_id = query_params["subject"][0]

        if not subject_id:
            return None

        code_value = query_params.get("code", [None])[0]
        if not code_value:
            return None

        if code_value.startswith("http://loinc.org|"):
            code_value = code_value.split("|", 1)[1]

        source = self._get_source_for_type("observation")
        observation = source.get_latest_observation(subject_id, code_value)
        if not observation:
            return None

        return {"entry": [{"resource": observation}]}

    def _get_subject_reference(self, context: Dict[str, Any]) -> Optional[str]:
        subject = context.get("subject")
        if isinstance(subject, str):
            return subject
        if isinstance(subject, dict):
            return subject.get("reference")
        return None
