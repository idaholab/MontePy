"""Sphinx extension to inject schema.org JSON-LD structured data.

Add to conf.py:
    extensions = [..., "schema_org"]

    schema_org_configs = {
        "index": {
            "@type": "SoftwareApplication",
            "name": "MontePy",
            ...
        }
    }
"""

import json
from typing import Any, Dict

from docutils import nodes
from sphinx.application import Sphinx


def add_schema_org_data(app: Sphinx, pagename: str, templatename: str, context: Dict, doctree: Any) -> None:
    """Add schema.org JSON-LD to page if configured."""
    configs = app.config.schema_org_configs
    if not configs or pagename not in configs:
        return

    schema_data = configs[pagename]
    schema_json = json.dumps(schema_data, indent=2)
    context['schema_org_data'] = schema_json


def setup(app: Sphinx) -> Dict[str, Any]:
    """Register the extension."""
    app.add_config_value("schema_org_configs", {}, "html")
    app.connect("html-page-context", add_schema_org_data)

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
