"""
Базовый класс для всех стратегий с автоматическим сбором сделок
"""
import backtrader as bt
import copy

class BaseStrategy(bt.Strategy):
    """Базовый класс для всех стратегий"""
    
    def __init__(self):
        self.trades_data = []
        self.trade_list = []  # Список для отслеживания сделок
        self.pending_trade_data = {}  # Новый словарь для кастомных данных

    def add_trade_data(self, key, value):
        """Добавляет кастомное поле к текущей сделке"""
        self.pending_trade_data[key] = value
    
    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'{dt.isoformat()} {txt}')
    
    def notify_trade(self, trade):
        """Сбор сделок"""
        if trade.isclosed:

            exit_reason = getattr(self, 'exit_reason', 'UNKNOWN')

            trade_data = {
                'pnl': float(trade.pnl),
                'pnlcomm': float(trade.pnlcomm),
                'barlen': int(trade.barlen),
                'size': float(trade.size),
                'price': float(trade.price),
                'value': float(trade.value),
                'commission': float(trade.commission),
                'isclosed': bool(trade.isclosed),
                'exit_reason': exit_reason,
                'history': []
            }

            self.exit_reason = None
            
            # Конвертируем history в простые словари
            if hasattr(trade, 'history') and trade.history:
                for event in trade.history:
                    event_dict = {}
                    
                    # Конвертируем event
                    for key, value in event.event.items():
                        if key == 'order':
                            # Извлекаем ВСЮ информацию из order объекта
                            order = value
                            event_dict['order_data'] = {
                                'ref': order.ref,
                                'status': order.status,
                                'status_name': order.getstatusname(),
                                'ordtype': order.ordtype,
                                'ordtype_name': order.ordtypename(),
                                'isbuy': order.isbuy(),
                                'issell': order.issell(),
                                'alive': order.alive(),
                                'active': order.active(),
                                'completed': order.completed(),
                                'partial': order.partial(),
                                # Атрибуты
                                'triggered': order.triggered if hasattr(order, 'triggered') else None,
                                'created': {
                                    'dt': float(order.created.dt) if hasattr(order, 'created') and order.created else None,
                                    'size': float(order.created.size) if hasattr(order, 'created') and order.created else None,
                                    'price': float(order.created.price) if hasattr(order, 'created') and order.created else None,
                                    'pricelimit': float(order.created.pricelimit) if hasattr(order, 'created') and order.created else None,
                                } if hasattr(order, 'created') and order.created else None,
                                'executed': {
                                    'dt': float(order.executed.dt) if hasattr(order, 'executed') and order.executed else None,
                                    'size': float(order.executed.size) if hasattr(order, 'executed') and order.executed else None,
                                    'price': float(order.executed.price) if hasattr(order, 'executed') and order.executed else None,
                                } if hasattr(order, 'executed') and order.executed else None,
                            }
                        else:
                            event_dict[key] = value
                    
                    event_data = {
                        'status': dict(event.status),
                        'event': event_dict
                    }
                    trade_data['history'].append(event_data)
            trade_data['custom'] = self.pending_trade_data.copy()
            self.pending_trade_data = {}  # Очищаем для следующей сделки
            
            self.trade_list.append(trade_data)