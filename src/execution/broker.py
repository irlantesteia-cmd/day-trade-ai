from typing import Dict, Any
from src.domain.enums import OrderDirection, OrderStatus, PositionSide
from src.domain.models import Order, Position
from src.execution.broker_base import Broker

class Portfolio:
    def __init__(self, cash: float = 10000.0):
        self.cash: float = cash
        self.positions: Dict[str, Any] = {}


class PaperBroker(Broker):
    def __init__(
        self,
        initial_balance: float = 10000.0,
        portfolio=None,
        slippage: float = 0.0,
        fee_per_contract: float = 0.0,
    ):
        self.portfolio = portfolio if portfolio is not None else Portfolio(cash=initial_balance)
        self.slippage = slippage
        self.fee_per_contract = fee_per_contract

        if not hasattr(self.portfolio, "cash") and hasattr(self.portfolio, "balance"):
            self.portfolio.cash = self.portfolio.balance
        if not hasattr(self.portfolio, "positions"):
            self.portfolio.positions = {}

    def _modify_cash(self, amount: float):
        portfolio = self.portfolio
        if hasattr(portfolio, "deposit") and callable(portfolio.deposit):
            if amount >= 0:
                portfolio.deposit(amount)
            elif hasattr(portfolio, "withdraw") and callable(portfolio.withdraw):
                portfolio.withdraw(abs(amount))
            else:
                self._fallback_cash_add(amount)
        else:
            self._fallback_cash_add(amount)

    def _fallback_cash_add(self, amount: float):
        portfolio = self.portfolio
        try:
            if hasattr(portfolio, "cash"):
                if isinstance(portfolio.cash, (int, float)):
                    portfolio.cash += amount
                elif hasattr(portfolio.cash, "value"):
                    portfolio.cash.value += amount
                else:
                    setattr(portfolio, "cash", float(getattr(portfolio, "cash", 0.0) or 0.0) + amount)
            else:
                portfolio.cash = amount
        except Exception:
            pass
        if hasattr(portfolio, "balance"):
            try:
                portfolio.balance = portfolio.cash
            except Exception:
                pass

    def execute_order(self, order: Order, current_price: float) -> Order:
        symbol = order.symbol
        quantity = order.quantity

        dir_val = getattr(order.direction, "value", str(order.direction))
        is_buy = "BUY" in str(dir_val).upper() or "LONG" in str(dir_val).upper()

        # Calculo de slippage: piora o preco na entrada/saida a mercado
        effective_price = current_price
        order_type_val = getattr(order.order_type, "value", str(order.order_type)).upper()
        if "MARKET" in order_type_val:
            effective_price += self.slippage if is_buy else -self.slippage

        order.price = effective_price
        order.status = OrderStatus.FILLED

        # Debito de taxas por contrato (corretagem / B3)
        total_fee = self.fee_per_contract * quantity
        if total_fee > 0:
            self._modify_cash(-total_fee)

        positions = getattr(self.portfolio, "positions", None)
        if not isinstance(positions, dict):
            positions = getattr(self.portfolio, "positions", {})

        if symbol in positions:
            pos = positions[symbol]
            pos_val = getattr(
                getattr(pos, "side", getattr(pos, "direction", "LONG")),
                "value",
                str(getattr(pos, "side", getattr(pos, "direction", "LONG"))),
            )
            is_long = "LONG" in str(pos_val).upper() or "BUY" in str(pos_val).upper()

            if (is_buy and is_long) or (not is_buy and not is_long):
                pos_qty = getattr(pos, "quantity", 0.0)
                entry_price = getattr(pos, "entry_price", effective_price)
                total_qty = pos_qty + quantity
                new_avg = (
                    ((entry_price * pos_qty) + (effective_price * quantity)) / total_qty
                    if total_qty > 0
                    else effective_price
                )
                if hasattr(pos, "quantity"):
                    pos.quantity = total_qty
                if hasattr(pos, "entry_price"):
                    pos.entry_price = new_avg
            else:
                pos_qty = getattr(pos, "quantity", 0.0)
                entry_price = getattr(pos, "entry_price", effective_price)
                if quantity >= pos_qty:
                    pnl = (
                        (effective_price - entry_price) * pos_qty
                        if is_long
                        else (entry_price - effective_price) * pos_qty
                    )
                    self._modify_cash(pnl)
                    if symbol in positions:
                        del positions[symbol]
                else:
                    pnl = (
                        (effective_price - entry_price) * quantity
                        if is_long
                        else (entry_price - effective_price) * quantity
                    )
                    self._modify_cash(pnl)
                    if hasattr(pos, "quantity"):
                        pos.quantity -= quantity
        else:
            target_side = PositionSide.LONG if is_buy else PositionSide.SHORT
            pos_obj = Position(
                symbol=symbol,
                side=target_side,
                quantity=quantity,
                entry_price=effective_price,
            )
            positions[symbol] = pos_obj

        return order