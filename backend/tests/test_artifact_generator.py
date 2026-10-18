"""Tests for scoring and generated artifacts."""

import yaml

from artifact_generator import compute_audit_score, generate_artifacts
from models import CoreAction, ProductAnalysis


def _analysis(actions: list[CoreAction]) -> ProductAnalysis:
    return ProductAnalysis(
        product_name='Acme "Invoices"',
        product_description="Invoicing API: create, list and send invoices.",
        product_category="API",
        core_actions=actions,
        auth_method="api_key",
        tech_stack=["Python"],
        has_existing_openapi=False,
        has_existing_docs=True,
        webhook_support=False,
        missing_agent_features=[],
        recommendations=[],
    )


ACTIONS = [
    CoreAction(name="list_invoices", description="List invoices", http_method="GET",
               endpoint="/invoices"),
    CoreAction(name="create_invoice", description="Create: a new invoice", http_method="POST",
               endpoint="/invoices"),
    CoreAction(name="get_invoice", description="Get one invoice", http_method="GET",
               endpoint="/invoices/:id"),
    CoreAction(name="mystery", description="Unknown", http_method="UNKNOWN", endpoint="UNKNOWN"),
]


def test_llms_txt_check_is_measured_not_guessed() -> None:
    analysis = _analysis(ACTIONS)
    without = compute_audit_score(analysis, has_llms_txt=False)
    with_file = compute_audit_score(analysis, has_llms_txt=True)
    assert with_file.score - without.score == 15
    assert with_file.breakdown.has_llms_txt


def test_openapi_is_valid_yaml_with_grouped_paths() -> None:
    spec = yaml.safe_load(generate_artifacts(_analysis(ACTIONS), "https://acme.com").openapi_yaml)
    assert spec["info"]["title"] == 'Acme "Invoices"'
    assert set(spec["paths"]["/invoices"]) == {"get", "post"}
    assert spec["paths"]["/invoices"]["post"]["summary"] == "Create: a new invoice"
    params = spec["paths"]["/invoices/{id}"]["get"]["parameters"]
    assert params[0]["name"] == "id" and params[0]["in"] == "path"
    assert "/unknown" not in spec["paths"]


def test_mcp_scaffold_uses_mcp_server_api() -> None:
    ts = generate_artifacts(_analysis(ACTIONS), "https://acme.com").mcp_server_ts
    assert 'from "@modelcontextprotocol/sdk/server/mcp.js"' in ts
    assert "new McpServer(" in ts
    assert "server.tool(" not in ts
    assert ts.count("server.registerTool(") == 4
    assert "`/invoices/${encodeURIComponent(id)}`" in ts
    assert "await server.connect" in ts and "main().catch" in ts


def test_blocked_bots_appear_in_audit() -> None:
    audit = generate_artifacts(_analysis([]), None, blocked_ai_bots=["GPTBot"]).audit_md
    assert "## AI Crawler Access" in audit and "`GPTBot`" in audit
