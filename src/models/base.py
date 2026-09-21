from abc import ABC, abstractmethod
from typing import List


class BaseModel(ABC):
    @abstractmethod
    def fit(self, X: List[List[float]], y: List[int]) -> None:
        """Treina o modelo com a matriz de atributos X e vetor de rótulos y."""
        pass

    @abstractmethod
    def predict(self, X: List[List[float]]) -> List[int]:
        """Retorna previsões de classe binária (0 ou 1)."""
        pass

    @abstractmethod
    def predict_proba(self, X: List[List[float]]) -> List[float]:
        """Retorna probabilidades da classe positiva (1)."""
        pass