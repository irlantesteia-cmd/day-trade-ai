import random
from typing import List, Dict, Any


class MonteCarloSimulator:
    def __init__(self, num_simulations: int = 1000, seed: int = 42):
        if num_simulations <= 0:
            raise ValueError("num_simulations must be positive")
        self.num_simulations = num_simulations
        self.seed = seed

    def simulate_equity_curves(self, trades_pnl: List[float], initial_capital: float = 10000.0) -> Dict[str, List[float]]:
        if not trades_pnl:
            raise ValueError("Trades PnL list cannot be empty")
        
        rng = random.Random(self.seed)
        simulated_curves = []
        n_trades = len(trades_pnl)
        
        for _ in range(self.num_simulations):
            shuffled = list(trades_pnl)
            rng.shuffle(shuffled)
            curve = [initial_capital]
            curr = initial_capital
            for pnl in shuffled:
                curr += pnl
                curve.append(curr)
            simulated_curves.append(curve)
        
        percentiles = {"p5": [], "p50": [], "p95": []}
        n_steps = n_trades + 1
        for step in range(n_steps):
            step_values = sorted([curve[step] for curve in simulated_curves])
            p5_idx = int(0.05 * len(step_values))
            p50_idx = int(0.50 * len(step_values))
            p95_idx = int(0.95 * len(step_values))
            
            percentiles["p5"].append(step_values[p5_idx])
            percentiles["p50"].append(step_values[p50_idx])
            percentiles["p95"].append(step_values[p95_idx])
            
        return percentiles


class StressTester:
    @staticmethod
    def apply_shock(trades_pnl: List[float], slippage_multiplier: float = 2.0, loss_amplifier: float = 1.25) -> List[float]:
        if slippage_multiplier < 0 or loss_amplifier < 0:
            raise ValueError("Multipliers cannot be negative")
        
        shocked = []
        for pnl in trades_pnl:
            if pnl < 0:
                shocked.append(pnl * loss_amplifier * slippage_multiplier)
            else:
                shocked.append(pnl / slippage_multiplier)
        return shocked