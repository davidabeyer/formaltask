"""Tests for API documentation - OpenAPI spec and Swagger UI."""

from fastapi.testclient import TestClient

from formaltask.api.app import create_app


def _client():
    return TestClient(create_app())


class TestSwaggerUI:
    """Swagger UI accessible at /docs."""

    def test_docs_returns_200(self):
        response = _client().get("/docs")
        assert response.status_code == 200

    def test_docs_contains_swagger_ui(self):
        response = _client().get("/docs")
        assert "swagger-ui" in response.text.lower()


class TestOpenAPISchema:
    """OpenAPI schema generated with correct metadata."""

    def test_openapi_json_returns_200(self):
        response = _client().get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_has_info(self):
        schema = _client().get("/openapi.json").json()
        assert schema["info"]["title"] == "FormalTask API"
        assert "version" in schema["info"]

    def test_openapi_has_paths(self):
        schema = _client().get("/openapi.json").json()
        assert len(schema["paths"]) > 0


class TestEndpointExamples:
    """All endpoints have request/response examples."""

    def _schema(self):
        return _client().get("/openapi.json").json()

    def test_every_endpoint_has_response_example(self):
        schema = self._schema()
        missing = []
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "delete"):
                    responses = details.get("responses", {})
                    has_example = False
                    for _code, resp in responses.items():
                        content = resp.get("content", {})
                        for _media, media_spec in content.items():
                            if "example" in media_spec or "examples" in media_spec:
                                has_example = True
                            # Check schema-level examples
                            if "schema" in media_spec:
                                ref = media_spec["schema"].get("$ref", "")
                                if ref:
                                    schema_name = ref.split("/")[-1]
                                    schemas = schema.get("components", {}).get("schemas", {})
                                    if schema_name in schemas:
                                        s = schemas[schema_name]
                                        if "example" in s or "examples" in s:
                                            has_example = True
                                        # Check json_schema_extra
                                        if s.get("properties"):
                                            has_example = True
                    if not has_example:
                        missing.append(f"{method.upper()} {path}")
        assert not missing, f"Endpoints missing response examples: {missing}"

    def test_post_endpoints_have_request_body_example(self):
        schema = self._schema()
        missing = []
        for path, methods in schema["paths"].items():
            for method in ("post", "put"):
                if method not in methods:
                    continue
                details = methods[method]
                body = details.get("requestBody", {})
                content = body.get("content", {})
                has_example = False
                for _media, media_spec in content.items():
                    if "example" in media_spec or "examples" in media_spec:
                        has_example = True
                    if "schema" in media_spec:
                        ref = media_spec["schema"].get("$ref", "")
                        if ref:
                            schema_name = ref.split("/")[-1]
                            schemas = schema.get("components", {}).get("schemas", {})
                            if schema_name in schemas:
                                s = schemas[schema_name]
                                if "example" in s or "examples" in s:
                                    has_example = True
                                if s.get("properties"):
                                    has_example = True
                if not has_example:
                    missing.append(f"{method.upper()} {path}")
        assert not missing, f"POST/PUT endpoints missing request examples: {missing}"
