"""
Базовый класс для всех стратегий с автоматическим сбором сделок
"""
import backtrader as bt

class BaseStrategy(bt.Strategy):
    """Базовый класс для всех стратегий"""
    
    def __init__(self):
        self.trades_data = []
        self.trade_list = []  # Список для отслеживания сделок
    
    def log(self, txt, dt=None):
        """Логирование"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def notify_trade(self, trade):
        """Сбор сделок"""
        if trade.isclosed:
            self.log(f'ПРИБЫЛЬ ПО СДЕЛКЕ, Валовая: {trade.pnl:.2f}, Чистая: {trade.pnlcomm:.2f}')
            self.trade_list.append(trade)