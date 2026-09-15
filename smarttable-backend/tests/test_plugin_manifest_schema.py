"""插件 manifest 校验测试：覆盖新增的 assets / endpoints / 新扩展点"""
import pytest

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

from app.services.plugin_manifest_schema import MANIFEST_SCHEMA


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def _assert_valid(manifest):
    jsonschema.validate(instance=manifest, schema=MANIFEST_SCHEMA)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def _assert_invalid(manifest):
    with pytest.raises(Exception):
        jsonschema.validate(instance=manifest, schema=MANIFEST_SCHEMA)


def _base(extra=None):
    m = {
        "id": "com.example.demo",
        "name": "Demo",
        "version": "1.0.0",
        "type": "ui",
        "apiVersion": "1",
        "engines": {"smarttable": ">=1.6.0 <2.0.0"},
        "entry": "main.js",
        "permissions": {"records": "read"},
        "extensionPoints": [{"type": "toolbar-button", "title": "X"}],
    }
    if extra:
        m.update(extra)
    return m


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_valid_with_assets_and_endpoints():
    m = _base({
        "assets": {
            "styles": ["styles/main.css"],
            "scripts": ["vendor/lib.js"],
        },
        "endpoints": [
            {"name": "translate", "entry": "endpoints/t.py", "timeout": 60},
        ],
        "extensionPoints": [
            {"type": "home-menu", "title": "HM"},
            {"type": "dashboard-widget", "title": "DW"},
        ],
    })
    _assert_valid(m)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_invalid_extension_point():
    _assert_invalid(_base({"extensionPoints": [{"type": "unknown-type", "title": "X"}]}))


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_invalid_endpoint_name():
    _assert_invalid(_base({
        "endpoints": [{"name": "Bad_Name", "entry": "e.py"}],
    }))
