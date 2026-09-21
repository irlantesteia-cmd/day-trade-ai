import itertools
import math
from typing import Callable, Dict, List, Tuple, Any


class SensitivityResult:
    def __init__(
        self,
        results: Dict[Tuple[Any, ...], float],
        param_names: List[str],
        mean_score: float,
        std_score: float,
        stability_index: float,
        best_params: Dict[str, Any],
        worst_params: Dict[str, Any],
    ):
        self.results = results
        self.param_names = param_names
        self.mean_score = mean_score
        self.std_score = std_score
        self.stability_index = stability_index
        self.best_params = best_params
        self.worst_params = worst_params


class SensitivityAnalyzer:
    def __init__(self, eval_func: Callable[[Dict[str, Any]], float]):
        if not callable(eval_func):
            raise TypeError("eval_func must be a callable function")
        self.eval_func = eval_func

    def analyze(self, param_grid: Dict[str, List[Any]]) -> SensitivityResult:
        if not param_grid:
            raise ValueError("param_grid cannot be empty")

        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        combinations = list(itertools.product(*param_values))
        if not combinations:
            raise ValueError("param_grid must yield at least one parameter combination")

        raw_results = {}
        scores = []
        best_score = float("-inf")
        worst_score = float("inf")
        best_comb = None
        worst_comb = None

        for comb in combinations:
            params = dict(zip(param_names, comb))
            score = float(self.eval_func(params))
            raw_results[comb] = score
            scores.append(score)

            if score > best_score:
                best_score = score
                best_comb = params
            if score < worst_score:
                worst_score = score
                worst_comb = params

        n = len(scores)
        mean_score = sum(scores) / n

        if n > 1:
            variance = sum((s - mean_score) ** 2 for s in scores) / (n - 1)
            std_score = math.sqrt(variance)
        else:
            std_score = 0.0

        denom = abs(mean_score) + 1e-9
        cv = std_score / denom
        stability_index = max(0.0, 1.0 - cv)

        return SensitivityResult(
            results=raw_results,
            param_names=param_names,
            mean_score=mean_score,
            std_score=std_score,
            stability_index=stability_index,
            best_params=best_comb or {},
            worst_params=worst_comb or {},
        )