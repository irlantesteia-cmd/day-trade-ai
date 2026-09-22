import os
from pathlib import Path


def test_dockerfile_exists():
    assert Path("Dockerfile").is_file()


def test_docker_compose_exists():
    assert Path("docker-compose.yml").is_file()


def test_dockerignore_exists():
    assert Path(".dockerignore").is_file()


def test_dockerfile_content():
    content = Path("Dockerfile").read_text()
    assert "FROM python:3.12-slim" in content
    assert "EXPOSE 8000" in content