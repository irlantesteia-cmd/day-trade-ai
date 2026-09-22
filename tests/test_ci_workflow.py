from pathlib import Path


def test_github_actions_workflow_exists():
    workflow_file = Path(".github/workflows/ci.yml")
    assert workflow_file.is_file()


def test_github_actions_workflow_content():
    content = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest" in content
    assert 'python-version: "3.12"' in content
    assert "DeploymentOrchestrator" in content