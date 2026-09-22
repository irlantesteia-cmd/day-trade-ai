from pathlib import Path
from src.deploy.orchestrator import DeploymentOrchestrator


def test_release_notes_exist():
    assert Path("RELEASE_NOTES.md").is_file()


def test_system_release_certification():
    orchestrator = DeploymentOrchestrator()
    readiness = orchestrator.verify_deployment_readiness()

    assert readiness["ready"] is True
    assert readiness["total_components"] >= 8
    assert Path("Dockerfile").exists()
    assert Path("docker-compose.yml").exists()
    assert Path(".github/workflows/ci.yml").exists()