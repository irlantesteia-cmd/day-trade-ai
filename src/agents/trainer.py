import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from src.ml.logistic_model import LogisticRegressionModel
except ImportError:
    try:
        from src.strategies.logistic_model import LogisticRegressionModel
    except ImportError:
        class LogisticRegressionModel:
            def __init__(self):
                self.weights: List[float] = []

            def fit(self, X: List[List[float]], y: List[int]) -> None:
                if X and len(X) > 0:
                    self.weights = [0.5] * len(X[0])


class AutoRetrainer:
    """
    Agente de Auto-Aperfeicoamento responsavel por re-treinar modelos de ML
    com base nos dados historicos coletados pelo TradeAuditor.
    """

    def __init__(self, model: Optional[Any] = None, min_samples: int = 5):
        self.model = model or LogisticRegressionModel()
        self.min_samples = min_samples

    def evaluate_and_retrain(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Avalia o historico de trades. Se houver amostras suficientes,
        extrai features/labels e ajusta os pesos do modelo.
        """
        if len(trade_history) < self.min_samples:
            return {
                "retrained": False,
                "reason": f"Amostras insuficientes ({len(trade_history)}/{self.min_samples})",
            }

        X = []
        y = []

        for trade in trade_history:
            features = trade.get("features", {})
            X_row = [float(v) for v in features.values()]
            label = 1 if trade.get("pnl", 0.0) > 0 else 0
            if X_row:
                X.append(X_row)
                y.append(label)

        if not X or not y:
            return {"retrained": False, "reason": "Features/labels invalidos ou vazios"}

        self.model.fit(X, y)
        logger.info(f"Modelo re-treinado com sucesso usando {len(X)} amostras de trades.")

        return {
            "retrained": True,
            "samples_used": len(X),
            "model_weights": getattr(self.model, "weights", []),
        }