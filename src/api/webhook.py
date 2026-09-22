import json
import urllib.request
from typing import Dict, Any, Optional


class WebhookDispatcher:
    """
    Despachante de webhooks para integracao com notificacoes externas (Slack, Discord, Telegram, HTTP endpoints).
    """

    def __init__(self, default_url: Optional[str] = None):
        self.default_url = default_url

    def dispatch(self, payload: Dict[str, Any], url: Optional[str] = None) -> bool:
        """
        Envia um payload JSON para o webhook especificado via POST HTTP.
        """
        target_url = url or self.default_url
        if not target_url:
            return False

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DayTradeAI-Webhook/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status in (200, 201, 202, 204)
        except Exception:
            return False

    def send_alert(
        self, title: str, message: str, level: str = "INFO", url: Optional[str] = None
    ) -> bool:
        """
        Formata e envia um alerta de evento do sistema.
        """
        payload = {
            "event": "system_alert",
            "title": title,
            "message": message,
            "level": level,
        }
        return self.dispatch(payload, url)

    def send_report(self, report_markdown: str, url: Optional[str] = None) -> bool:
        """
        Formata e envia um relatorio executivo em markdown.
        """
        payload = {
            "event": "executive_report",
            "content": report_markdown,
        }
        return self.dispatch(payload, url)