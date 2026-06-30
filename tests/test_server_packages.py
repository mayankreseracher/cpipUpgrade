from fastapi.testclient import TestClient
from server.app import app


def test_catalog_endpoint_not_shadowed():
    client = TestClient(app)
    response = client.get("/api/v1/packages/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "packages" in data
    
    # Verify we got the catalog and not a 404 for package "catalog"
    package_names = [p["name"] for p in data["packages"]]
    assert "torch" in package_names
    assert "tensorflow" in package_names
    
    # Verify getting a specific package still works
    response_pkg = client.get("/api/v1/packages/torch")
    assert response_pkg.status_code == 200
    pkg_data = response_pkg.json()
    assert pkg_data["name"] == "torch"
