from fhir_data_source import DataSourceRouter, MockFhirDataSource, RemoteFhirDataSource, TypedDataSourceRouter

from clinical_data import mock_data


def test_router_selects_mock_by_default():
    router = DataSourceRouter(default_source=MockFhirDataSource(mock_data))
    source = router.select_source({}, {})
    assert isinstance(source, MockFhirDataSource)


def test_router_selects_remote_for_url_hint():
    router = DataSourceRouter(default_source=MockFhirDataSource(mock_data))
    source = router.select_source({"source": "https://example.org/fhir"}, {})
    assert isinstance(source, RemoteFhirDataSource)


def test_router_selects_remote_by_hint_with_default_url():
    router = DataSourceRouter(
        default_source=MockFhirDataSource(mock_data),
        default_remote_url="https://example.org/fhir",
    )
    source = router.select_source({"source": "remote"}, {})
    assert isinstance(source, RemoteFhirDataSource)


def test_router_selects_remote_for_source_url_parameter():
    router = DataSourceRouter(default_source=MockFhirDataSource(mock_data))
    source = router.select_source({"sourceUrl": "https://example.org/fhir"}, {})
    assert isinstance(source, RemoteFhirDataSource)


def test_router_selects_remote_for_source_url_query_param():
    router = DataSourceRouter(default_source=MockFhirDataSource(mock_data))
    source = router.select_source({}, {"sourceUrl": "https://example.org/fhir"})
    assert isinstance(source, RemoteFhirDataSource)


def test_router_returns_typed_router_for_questionnaire_extension_with_typed_endpoints():
    """Test that router returns TypedDataSourceRouter when questionnaire has typed endpoints."""
    router = DataSourceRouter(default_source=MockFhirDataSource(mock_data))
    questionnaire = {
        "resourceType": "Questionnaire",
        "id": "test",
        "extension": [
            {
                "url": "http://example.org/fhir/StructureDefinition/populate-data-endpoints",
                "extension": [
                    {
                        "url": "patient",
                        "valueUrl": "https://patient-api.example.org/fhir"
                    },
                    {
                        "url": "observation",
                        "valueUrl": "https://obs-api.example.org/fhir"
                    }
                ]
            }
        ]
    }
    source = router.select_source({}, {}, questionnaire)
    assert isinstance(source, TypedDataSourceRouter)


def test_typed_router_routes_to_patient_endpoint():
    """Test that TypedDataSourceRouter routes patient requests to patient endpoint."""
    typed_router = TypedDataSourceRouter(
        default_source=MockFhirDataSource(mock_data),
        endpoints={
            "patient": "https://patient-api.example.org/fhir",
            "observation": "https://obs-api.example.org/fhir"
        }
    )
    patient_source = typed_router.get_source_for_type("patient")
    obs_source = typed_router.get_source_for_type("observation")
    
    assert isinstance(patient_source, RemoteFhirDataSource)
    assert isinstance(obs_source, RemoteFhirDataSource)
    assert patient_source.base_url == "https://patient-api.example.org/fhir"
    assert obs_source.base_url == "https://obs-api.example.org/fhir"


def test_typed_router_routes_to_shared_fhir_endpoint():
    """Test that TypedDataSourceRouter uses a shared 'fhir' endpoint when specific type is absent."""
    typed_router = TypedDataSourceRouter(
        default_source=MockFhirDataSource(mock_data),
        endpoints={"fhir": "https://shared-api.example.org/fhir"}
    )
    patient_source = typed_router.get_source_for_type("patient")
    obs_source = typed_router.get_source_for_type("observation")

    assert isinstance(patient_source, RemoteFhirDataSource)
    assert isinstance(obs_source, RemoteFhirDataSource)
    assert patient_source.base_url == "https://shared-api.example.org/fhir"
    assert obs_source.base_url == "https://shared-api.example.org/fhir"


def test_typed_router_uses_default_for_missing_resource_type():
    """Test that TypedDataSourceRouter falls back to default for unmapped resource types."""
    typed_router = TypedDataSourceRouter(
        default_source=MockFhirDataSource(mock_data),
        endpoints={"patient": "https://api.example.org/fhir"}
    )
    missing_source = typed_router.get_source_for_type("procedure")
    assert isinstance(missing_source, MockFhirDataSource)


def test_typed_router_caches_sources():
    """Test that TypedDataSourceRouter caches created sources."""
    typed_router = TypedDataSourceRouter(
        default_source=MockFhirDataSource(mock_data),
        endpoints={"patient": "https://api.example.org/fhir"}
    )
    source1 = typed_router.get_source_for_type("patient")
    source2 = typed_router.get_source_for_type("patient")
    assert source1 is source2  # Same instance

