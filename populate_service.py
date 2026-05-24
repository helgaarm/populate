from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fhir.resources.parameters import Parameters
from fhir.resources.questionnaire import Questionnaire
from fhir.resources.questionnaireresponse import QuestionnaireResponse


class PopulateService:
    @staticmethod
    def extract_parameters(body: Dict[str, Any]) -> Dict[str, Any]:
        if body.get("resourceType") != "Parameters":
            return body.get("parameters") or {}

        params: Dict[str, Any] = {}
        for parameter in body.get("parameter", []):
            if not isinstance(parameter, dict):
                continue

            name = parameter.get("name")
            if not name:
                continue

            value: Any = None
            for key, val in parameter.items():
                if key == "name" or val is None:
                    continue
                value = val
                break

            if value is not None:
                params[name] = PopulateService._normalize_value(value)

        return params

    @staticmethod
    def extract_variables(questionnaire_data: Dict[str, Any]) -> Dict[str, str]:
        variables: Dict[str, str] = {}
        for extension in questionnaire_data.get("extension", []):
            if not isinstance(extension, dict):
                continue

            url = extension.get("url", "")
            if "variable" not in url:
                continue

            value_expr = extension.get("valueExpression", {})
            if isinstance(value_expr, dict):
                name = value_expr.get("name")
                expression = value_expr.get("expression")
                if name and expression:
                    variables[name] = expression

        return variables

    @staticmethod
    def extract_data_endpoints(questionnaire_data: Dict[str, Any]) -> Optional[str]:
        """Extract data source endpoint URL from questionnaire extension.
        
        Looks for extensions with URL containing 'populate-data-endpoints' and returns
        the first nested extension with a valueUrl or the first available endpoint URL.
        
        Example extension structure:
        {
            "url": "http://example.org/fhir/StructureDefinition/populate-data-endpoints",
            "extension": [
                {
                    "url": "terminObservation",
                    "valueUrl": "https://api.example.no/fhir/dhg/termin-observation"
                }
            ]
        }
        """
        for extension in questionnaire_data.get("extension", []):
            if not isinstance(extension, dict):
                continue

            url = extension.get("url", "")
            if "populate-data-endpoints" not in url:
                continue

            # Look for nested extensions with valueUrl
            nested_extensions = extension.get("extension", [])
            if isinstance(nested_extensions, list):
                for nested_ext in nested_extensions:
                    if isinstance(nested_ext, dict):
                        value_url = nested_ext.get("valueUrl")
                        if isinstance(value_url, str) and value_url.strip():
                            return value_url

        return None

    @staticmethod
    def extract_initial_expressions(items: List[Dict[str, Any]]) -> Dict[str, str]:
        expressions: Dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                continue

            link_id = item.get("linkId")
            if link_id:
                for extension in item.get("extension", []):
                    if not isinstance(extension, dict):
                        continue

                    url = extension.get("url", "")
                    if "sdc-questionnaire-initialExpression" in url:
                        value_expr = extension.get("valueExpression", {})
                        if isinstance(value_expr, dict):
                            expression = value_expr.get("expression")
                            if expression:
                                expressions[link_id] = expression
                        break

            if link_id and link_id not in expressions and "initialExpression" in item:
                expressions[link_id] = item["initialExpression"]

            if "item" in item and item["item"]:
                expressions.update(PopulateService.extract_initial_expressions(item["item"]))

        return expressions

    @staticmethod
    def sanitize_questionnaire_item(item: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = {
            "linkId",
            "definition",
            "code",
            "prefix",
            "text",
            "type",
            "enableWhen",
            "enableBehavior",
            "required",
            "repeats",
            "readOnly",
            "maxLength",
            "answerConstraint",
            "answerValueSet",
            "answerOption",
            "initial",
            "item",
            "extension",
            "id",
            "modifierExtension",
        }

        sanitized: Dict[str, Any] = {}
        for key, value in item.items():
            if key in allowed_fields or key.endswith("__ext"):
                sanitized[key] = value

        if "item" in sanitized and sanitized["item"]:
            sanitized["item"] = [
                PopulateService.sanitize_questionnaire_item(i) for i in sanitized["item"]
            ]

        return sanitized

    @staticmethod
    def get_questionnaire_resource(body: Dict[str, Any]) -> tuple[Questionnaire, Dict[str, str], Dict[str, str]]:
        questionnaire_data: Optional[Dict[str, Any]] = None

        if body.get("resourceType") == "Questionnaire":
            questionnaire_data = body
        elif body.get("resourceType") == "Parameters":
            for parameter in body.get("parameter", []):
                if isinstance(parameter, dict) and parameter.get("name") == "questionnaire":
                    if "resource" in parameter:
                        questionnaire_data = parameter["resource"]
                        break
            if not questionnaire_data:
                parameters = Parameters.model_validate(body)
                for parameter in parameters.parameter or []:
                    if parameter.name == "questionnaire" and parameter.resource:
                        questionnaire_data = (
                            parameter.resource.model_dump()
                            if hasattr(parameter.resource, "model_dump")
                            else parameter.resource
                        )
                        break
        elif "questionnaire" in body and isinstance(body["questionnaire"], dict):
            questionnaire_data = body["questionnaire"]

        if not questionnaire_data:
            raise ValueError(
                "Request must include a Questionnaire resource or a Parameters resource containing a questionnaire parameter."
            )

        variables = PopulateService.extract_variables(questionnaire_data)
        expressions = PopulateService.extract_initial_expressions(questionnaire_data.get("item", []))

        sanitized_data = dict(questionnaire_data)
        if "item" in sanitized_data:
            sanitized_data["item"] = [
                PopulateService.sanitize_questionnaire_item(i) for i in sanitized_data["item"]
            ]

        questionnaire = Questionnaire.model_validate(sanitized_data)
        return questionnaire, expressions, variables

    @staticmethod
    def build_questionnaire_response(
        questionnaire: Questionnaire,
        parameters: Dict[str, Any],
        expressions: Optional[Dict[str, str]],
        variables: Optional[Dict[str, str]],
        evaluator=None,
    ) -> QuestionnaireResponse:
        questionnaire_id = questionnaire.id or "generated-questionnaire"
        subject = parameters.get("subject")
        encounter = parameters.get("encounter")
        qr_context = parameters.get("context")

        if isinstance(subject, str):
            subject = PopulateService._normalize_reference(subject, "Patient")
        if isinstance(encounter, str):
            encounter = PopulateService._normalize_reference(encounter, "Encounter")

        eval_context: Dict[str, Any] = {
            "subject": subject,
            "encounter": encounter,
            "context": qr_context,
        }
        for key, value in parameters.items():
            if key not in {"subject", "encounter", "context"}:
                eval_context[key] = value

        response_data: Dict[str, Any] = {
            "resourceType": "QuestionnaireResponse",
            "id": str(uuid4()),
            "status": "in-progress",
            "questionnaire": f"Questionnaire/{questionnaire_id}",
            "authored": datetime.now(timezone.utc).isoformat(),
            "item": PopulateService._build_response_items(
                questionnaire.item or [], eval_context, expressions, variables, evaluator
            ),
        }

        if subject is not None:
            response_data["subject"] = subject
        if encounter is not None:
            response_data["encounter"] = encounter
        if qr_context is not None:
            response_data["context"] = qr_context

        return QuestionnaireResponse.model_validate(response_data)

    @staticmethod
    def _build_response_items(
        items: List[Any],
        context: Optional[Dict[str, Any]] = None,
        expressions: Optional[Dict[str, str]] = None,
        variables: Optional[Dict[str, str]] = None,
        evaluator=None,
    ) -> List[Dict[str, Any]]:
        response_items: List[Dict[str, Any]] = []

        for item in items:
            item_dict = PopulateService._to_dict(item)
            response_item: Dict[str, Any] = {
                "linkId": item_dict.get("linkId", ""),
                "text": item_dict.get("text"),
                "definition": item_dict.get("definition"),
            }

            answer = PopulateService._answer_from_item(
                item_dict, context, expressions, variables, evaluator
            )
            if answer is not None:
                response_item["answer"] = answer

            if item_dict.get("item"):
                response_item["item"] = PopulateService._build_response_items(
                    item_dict["item"], context, expressions, variables, evaluator
                )

            response_items.append({k: v for k, v in response_item.items() if v is not None})

        return response_items

    @staticmethod
    def _answer_from_item(
        item: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        expressions: Optional[Dict[str, str]] = None,
        variables: Optional[Dict[str, str]] = None,
        evaluator=None,
    ) -> Optional[List[Dict[str, Any]]]:
        if "initial" in item:
            initial = item["initial"]
            if isinstance(initial, list):
                return initial
            if isinstance(initial, dict):
                return [initial]

        link_id = item.get("linkId")
        if link_id and expressions and link_id in expressions and context and evaluator:
            expr_value = evaluator.evaluate(expressions[link_id], context)
            if expr_value is not None:
                if isinstance(expr_value, bool):
                    return [{"valueBoolean": expr_value}]
                if isinstance(expr_value, int) and not isinstance(expr_value, bool):
                    return [{"valueInteger": expr_value}]
                if isinstance(expr_value, float):
                    return [{"valueDecimal": expr_value}]
                if isinstance(expr_value, dict):
                    return [
                        {
                            "valueReference"
                            if "reference" in expr_value
                            else "valueCoding": expr_value
                        }
                    ]
                return [{"valueString": str(expr_value)}]
            return [{"valueString": f"Expression evaluated to null: {expressions[link_id]}"}]

        if item.get("type") in {
            "boolean",
            "decimal",
            "integer",
            "quantity",
            "date",
            "dateTime",
            "time",
            "string",
            "url",
            "uri",
            "email",
        }:
            return []

        return None

    @staticmethod
    def _normalize_reference(value: Any, default_prefix: str) -> Any:
        if isinstance(value, str):
            if "/" not in value:
                return {"reference": f"{default_prefix}/{value}"}
            return {"reference": value}
        return value

    @staticmethod
    def _to_dict(item: Any) -> Dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return item

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(exclude_none=True)
        if isinstance(value, list):
            return [PopulateService._normalize_value(item) for item in value]
        return value
