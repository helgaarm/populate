from fhir_data_source import DataSourceRouter, MockFhirDataSource, RemoteFhirDataSource

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
