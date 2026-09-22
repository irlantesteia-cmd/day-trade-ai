from pathlib import Path
from typing import Dict, Any
from src.main import build_system


class DeploymentOrchestrator:
    """
    Orquestrador de ambiente e verificador de prontidao para deploy em producao.
    """

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def check_environment_prerequisites(self) -> Dict[str, bool]:
        """
        Verifica se os arquivos vitais de deploy e orquestracao existem.
        """
        return {
            "dockerfile": (self.base_path / "Dockerfile").exists(),
            "docker_compose": (self.base_path / "docker-compose.yml").exists(),
            "pyproject": (self.base_path / "pyproject.toml").exists(),
        }

    def verify_deployment_readiness(self) -> Dict[str, Any]:
        """
        Executa a checagem completa de integridade dos subsistemas e manifestos.
        """
        prereqs = self.check_environment_prerequisites()
        system = build_system()
        health = system["health"].check_health() if "health" in system else {}

        health_status = health.get("status", "OK") if isinstance(health, dict) else "OK"
        raw_status = str(health_status).upper()

        is_healthy = raw_status not in ("CRITICAL", "ERROR", "FAILED", "DOWN", "UNHEALTHY")
        is_ready = all(prereqs.values()) and is_healthy

        return {
            "ready": is_ready,
            "prerequisites": prereqs,
            "health_status": health_status,
            "total_components": len(system),
        }