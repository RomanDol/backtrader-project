from backend.core.binance_data_loader import binance_data_loader
import inspect

# Проверяем какие методы есть
methods = [method for method in dir(binance_data_loader) if not method.startswith('_')]
print("Доступные методы:", methods)

# Проверяем есть ли load_data_for_backtest
if hasattr(binance_data_loader, 'load_data_for_backtest'):
    print("\n✅ Метод load_data_for_backtest существует")
    # Показываем сигнатуру
    sig = inspect.signature(binance_data_loader.load_data_for_backtest)
    print(f"Сигнатура: {sig}")
else:
    print("\n❌ Метод load_data_for_backtest НЕ существует")