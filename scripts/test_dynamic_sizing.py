"""Teste do DynamicPositionSizer."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.risk.dynamic_sizing import DynamicPositionSizer


def main():
    sizer = DynamicPositionSizer(
        base_risk_pct=1.0,
        vol_target_pct=0.5,
        confidence_scaling=True,
    )

    balance = 10000
    entry = 130000
    sl = 129500  # 500 pontos de risco

    print("Base (sem ajustes):")
    q_base = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.5, current_vol=0.005,  # vol = alvo
    )
    print(f"  qty={q_base} (esperado ~20: 10000*1% / 500)")

    print("\nVol alta (2x alvo):")
    q_low = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.5, current_vol=0.010,
    )
    print(f"  qty={q_low} (esperado ~10)")

    print("\nVol baixa (0.5x alvo):")
    q_high = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.5, current_vol=0.0025,
    )
    print(f"  qty={q_high} (esperado ~30, cap max 2x = 40)")

    print("\nConfidence alta (0.9):")
    q_conf = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.9, current_vol=0.005,
    )
    print(f"  qty={q_conf} (esperado ~28, factor 1.4)")

    print("\nCombinado: vol alta + confidence alta:")
    q_combo = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.9, current_vol=0.010,
    )
    print(f"  qty={q_combo} (esperado ~14)")

    print("\nSem ATR/vol (fallback):")
    q_fallback = sizer.compute_quantity(
        balance=balance, entry_price=entry, stop_loss=sl,
        signal_confidence=0.7, current_vol=None,
    )
    print(f"  qty={q_fallback} (esperado ~24)")


if __name__ == "__main__":
    main()