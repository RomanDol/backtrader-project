"""
Стратегия на основе скользящих средних (SMA)
"""
import backtrader as bt
from .base import BaseStrategy

class SimpleMovingAverageStrategy(BaseStrategy):
    """
    Простая стратегия на основе скользящих средних (SMA)
    Сигнал на покупку: быстрая SMA пересекает медленную снизу вверх
    Сигнал на продажу: быстрая SMA пересекает медленную сверху вниз
    """
    
    # Метаданные стратегии для UI
    STRATEGY_INFO = {
        'id': 'sma',
        'name': 'Simple Moving Average',
        'description': 'Стратегия на основе пересечения двух скользящих средних',
        'params': {
            'fast_period': {
                'label': 'Fast MA Period',
                'type': 'number',
                'default': 10,
                'min': 2,
                'max': 50,
                'step': 1,
                'description': ''
            },
            'slow_period': {
                'label': 'Slow MA Period',
                'type': 'number',
                'default': 30,
                'min': 5,
                'max': 200,
                'step': 1,
                'description': ''
            }
        }
    }
    
    # Параметры Backtrader
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('printlog', False),
    )

    def __init__(self):
        super().__init__()  # Вызов базового __init__
        
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Индикаторы
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period)
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period)
        
        # Сигнал кроссовера
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'ПОКУПКА ИСПОЛНЕНА, Цена: {order.executed.price:.2f}, '
                    f'Стоимость: {order.executed.value:.2f}, '
                    f'Комиссия: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    f'ПРОДАЖА ИСПОЛНЕНА, Цена: {order.executed.price:.2f}, '
                    f'Стоимость: {order.executed.value:.2f}, '
                    f'Комиссия: {order.executed.comm:.2f}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Ордер Отменен/Маржа/Отклонен')

        self.order = None

    def next(self):
        self.log(f'Закрытие: {self.dataclose[0]:.2f}')

        if self.order:
            return

        if not self.position:
            if self.crossover > 0:
                self.log(f'СИГНАЛ НА ПОКУПКУ, Цена: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.log(f'СИГНАЛ НА ПРОДАЖУ, Цена: {self.dataclose[0]:.2f}')
                self.order = self.sell()