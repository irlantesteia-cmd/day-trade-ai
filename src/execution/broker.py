from typing import Optional
from src.domain.enums import OrderSide, OrderStatus, PositionSide
from src.domain.models import Order, Position
from src.execution.portfolio import PortfolioManager


class PaperBroker:
    def __init__(self, portfolio: PortfolioManager):
        self.portfolio = portfolio

    def execute_order(self, order: Order, current_price: float) -> Order:
        """Executa a ordem ao preço atual de mercado e atualiza a posição e portfólio."""
        order.price = current_price
        order.status = OrderStatus.FILLED

        symbol = order.symbol
        quantity = order.quantity

        # Se já existe uma posição no ativo
        if symbol in self.portfolio.positions:
            pos = self.portfolio.positions[symbol]
            if (order.side == OrderSide.BUY and pos.side == PositionSide.LONG) or (
                order.side == OrderSide.SELL and pos.side == PositionSide.SHORT
            ):
                # Aumentar posição
                total_qty = pos.quantity + quantity
                pos.entry_price = ((pos.entry_price * pos.quantity) + (current_price * quantity)) / total_qty
                pos.quantity = total_qty
            else:
                # Fechar ou inverter posição
                if quantity >= pos.quantity:
                    # Fechar totalmente a posição
                    pnl = (
                        (current_price - pos.entry_price) * pos.quantity
                        if pos.side == PositionSide.LONG
                        else (pos.entry_price - current_price) * pos.quantity
                    )
                    self.portfolio.cash += pnl
                    del self.portfolio.positions[symbol]
                else:
                    # Fechar parcialmente
                    pnl = (
                        (current_price - pos.entry_price) * quantity
                        if pos.side == PositionSide.LONG
                        else (pos.entry_price - current_price) * quantity
                    )
                    self.portfolio.cash += pnl
                    pos.quantity -= quantity
        else:
            # Abrir nova posição
            side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            self.portfolio.positions[symbol] = Position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=current_price,
                current_price=current_price,
                unrealized_pnl=0.0,
            )

        self.portfolio.order_history.append(order)
        return order