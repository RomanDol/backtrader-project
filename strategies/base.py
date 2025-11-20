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
    
    def log(self, txt, dt=None):
        """Логирование"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def notify_trade(self, trade):
        """Сбор сделок"""
        if trade.isclosed:
            self.log(f'ПРИБЫЛЬ ПО СДЕЛКЕ, Валовая: {trade.pnl:.2f}, Чистая: {trade.pnlcomm:.2f}')
            
            # Детальное логирование для изучения структуры
            print("\n" + "="*80)
            print("TRADE CLOSED - DETAILED INFO:")
            print("="*80)
            print(f"trade.size: {trade.size}")
            print(f"trade.price: {trade.price}")
            print(f"trade.pnl: {trade.pnl}")
            print(f"trade.pnlcomm: {trade.pnlcomm}")
            print(f"trade.isclosed: {trade.isclosed}")
            print(f"trade.barlen: {trade.barlen}")
            
            # Логируем history
            print(f"\ntrade.history (type: {type(trade.history)}):")
            print(f"Number of events: {len(trade.history) if hasattr(trade.history, '__len__') else 'N/A'}")
            
            if hasattr(trade, 'history') and trade.history:
                for i, event in enumerate(trade.history):
                    print(f"\n--- Event {i} ---")
                    print(f"Type: {type(event)}")
                    print(f"Event: {event}")
                    
                    # Пытаемся получить атрибуты
                    if hasattr(event, '__dict__'):
                        print(f"Attributes: {event.__dict__}")
                    
                    # Пытаемся получить status и event
                    if hasattr(event, 'status'):
                        print(f"\nEvent.status:")
                        print(f"  Type: {type(event.status)}")
                        print(f"  Content: {event.status}")
                        if hasattr(event.status, '__dict__'):
                            print(f"  Attributes: {event.status.__dict__}")
                    
                    if hasattr(event, 'event'):
                        print(f"\nEvent.event:")
                        print(f"  Type: {type(event.event)}")
                        print(f"  Content: {event.event}")
                        if hasattr(event.event, '__dict__'):
                            print(f"  Attributes: {event.event.__dict__}")
            
            print("="*80 + "\n")
            
            # self.trade_list.append(trade)
            trade_data = {
                'pnl': float(trade.pnl),
                'pnlcomm': float(trade.pnlcomm),
                'barlen': int(trade.barlen),
                'size': float(trade.size),
                'price': float(trade.price),
                'value': float(trade.value),
                'commission': float(trade.commission),
                'isclosed': bool(trade.isclosed),
                'history': []
            }
            
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
            
            self.trade_list.append(trade_data)