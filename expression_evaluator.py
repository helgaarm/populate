"""Expression evaluator for FHIR populate initialExpression."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fhirpathpy import evaluate as fhirpath_evaluate

from fhir_data_source import FhirDataSource
from fhir_variable_resolver import FhirVariableResolver


class ExpressionEvaluator:
    """Evaluates FHIR initialExpression values using a FHIRPath engine."""

    def __init__(self, data_source: FhirDataSource) -> None:
        self.resolver = FhirVariableResolver(data_source)

    def set_variables(self, variables: Dict[str, Any]) -> None:
        """Set the variable definitions used during evaluation."""
        self.resolver.set_variables(variables)

    def evaluate(
        self, expression: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        if not expression or not context:
            return None

        resolved = self.resolver.resolve_expression(expression, context)
        if resolved is None:
            return None

        if isinstance(resolved, tuple):
            resource, path = resolved
            if not path:
                return self._normalize_result(resource, expression)

            try:
                result = fhirpath_evaluate(resource, path, context=context)
            except Exception:
                return None

            return self._normalize_result(result, expression)

        return self._normalize_result(resolved, expression)

    def _normalize_result(self, value: Any, expression: str) -> Optional[Any]:
        if value is None:
            return None

        if isinstance(value, list):
            if not value:
                return None
            if len(value) == 1:
                value = value[0]

        if expression.startswith("Patient/name") and isinstance(value, dict):
            return self._format_human_name(value)

        return value

    def _format_human_name(self, name: Dict[str, Any]) -> Optional[str]:
        if not isinstance(name, dict):
            return None

        given = name.get("given") or []
        family = name.get("family") or ""
        if isinstance(given, list):
            given_text = " ".join(str(part) for part in given if part is not None)
        else:
            given_text = str(given)

        return f"{given_text} {family}".strip() or None


def create_evaluator(data_source: FhirDataSource) -> ExpressionEvaluator:
    """Factory to create an expression evaluator."""
    return ExpressionEvaluator(data_source)

