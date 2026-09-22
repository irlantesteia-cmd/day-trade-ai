import json
from typing import Dict, Any


class ExecutiveReportExporter:
    """
    Formatador e exportador de relatorios executivos de performance em Markdown e JSON.
    """

    def export_to_json(self, report_data: Dict[str, Any]) -> str:
        """
        Exporta os dados do relatorio em formato JSON formatado.
        """
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def export_to_markdown(self, report_data: Dict[str, Any]) -> str:
        """
        Exporta os dados do relatorio em formato Markdown executivo.
        """
        lines = [
            "# 📊 Relatório Executivo de Performance",
            "",
            "## Resumo Geral",
            f"- **Total de Trades:** {report_data.get('total_trades', 0)}",
            f"- **PnL Total:** R$ {report_data.get('total_pnl', 0.0):.2f}",
            f"- **Win Rate:** {report_data.get('win_rate', 0.0) * 100:.2f}%",
            f"- **Profit Factor:** {report_data.get('profit_factor', 0.0):.2f}",
            f"- **Sharpe Ratio:** {report_data.get('sharpe_ratio', 0.0):.2f}",
            f"- **Max Drawdown:** R$ {report_data.get('max_drawdown', 0.0):.2f}",
            f"- **Expectativa Matemática:** R$ {report_data.get('expectancy', 0.0):.2f}",
        ]
        return "\n".join(lines)