import pytest
from src.deploy.orchestrator import DeploymentOrchestrator


def test_check_environment_prerequisites():
    orchestrator = DeploymentOrchestrator()
    prereqs = orchestrator.check_environment_prerequisites()
    assert prereqs["dockerfile"] is True
    assert prereqs["docker_compose"] is True
    assert prereqs["pyproject"] is True


def test_verify_deployment_readiness():
    orchestrator = DeploymentOrchestrator()
    readiness = orchestrator.verify_deployment_readiness()
    assert isinstance(readiness, dict)
    assert readiness["ready"] is True
    assert str(readiness["health_status"]).upper() not in ("CRITICAL", "ERROR", "FAILED", "DOWN", "UNHEALTHY")
    assert readiness["total_components"] > 0