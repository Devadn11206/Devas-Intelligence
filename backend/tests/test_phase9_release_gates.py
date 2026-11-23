import pytest
import pytest_asyncio
import subprocess
import sys
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """Verify Prometheus scrape endpoint /metrics is registered and responds with valid metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/metrics")
        assert response.status_code == 200
        assert "deva_http_requests_total" in response.text
        assert "deva_http_request_duration_seconds" in response.text


def test_quantitative_release_gates_pass():
    """Verify all quantitative gates (retrieval Recall@10, citation rate, refusal rate, linker resolution) pass."""
    # Execute the standalone CLI gate runner
    result = subprocess.run(
        [sys.executable, "-m", "evals.run_release_gate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Release gate failed with code {result.returncode}:\n{result.stdout}\n{result.stderr}"

