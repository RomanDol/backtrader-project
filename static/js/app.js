document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('backtestForm');
    const runBtn = document.getElementById('runBtn');
    const loader = document.getElementById('loader');
    const results = document.getElementById('results');
    const error = document.getElementById('error');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Скрыть предыдущие результаты
        results.style.display = 'none';
        error.style.display = 'none';
        loader.style.display = 'block';
        runBtn.disabled = true;

        // Собрать данные формы
        const formData = {
            initial_cash: parseFloat(document.getElementById('initial_cash').value),
            commission: parseFloat(document.getElementById('commission').value) / 100, // Конвертировать в десятичную дробь
            fast_period: parseInt(document.getElementById('fast_period').value),
            slow_period: parseInt(document.getElementById('slow_period').value)
        };

        try {
            const response = await fetch('/api/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                displayResults(data.results);
            } else {
                showError(data.error || 'Произошла ошибка при выполнении бэктеста');
            }
        } catch (err) {
            showError('Ошибка соединения с сервером: ' + err.message);
        } finally {
            loader.style.display = 'none';
            runBtn.disabled = false;
        }
    });

    function displayResults(data) {
        // Финальный капитал
        document.getElementById('final_value').textContent = 
            '$' + data.final_value.toFixed(2);

        // Прибыль/Убыток
        const profitElement = document.getElementById('profit');
        profitElement.textContent = '$' + data.profit.toFixed(2);
        profitElement.className = 'result-value ' + (data.profit >= 0 ? 'positive' : 'negative');

        // Доходность в процентах
        const profitPercentElement = document.getElementById('profit_percent');
        profitPercentElement.textContent = data.profit_percent.toFixed(2) + '%';
        profitPercentElement.className = 'result-value ' + (data.profit_percent >= 0 ? 'positive' : 'negative');

        // Коэффициент Шарпа
        const sharpeElement = document.getElementById('sharpe_ratio');
        const sharpeValue = data.sharpe_ratio || 0;
        sharpeElement.textContent = sharpeValue.toFixed(2);
        sharpeElement.className = 'result-value ' + (sharpeValue > 0 ? 'positive' : 'negative');

        // Максимальная просадка
        const drawdownElement = document.getElementById('max_drawdown');
        drawdownElement.textContent = data.max_drawdown.toFixed(2) + '%';
        drawdownElement.className = 'result-value negative';

        // Общая доходность
        const returnElement = document.getElementById('total_return');
        returnElement.textContent = data.total_return.toFixed(2) + '%';
        returnElement.className = 'result-value ' + (data.total_return >= 0 ? 'positive' : 'negative');

        // Информация о сделках
        const tradesInfo = document.getElementById('trades_info');
        if (data.trades && data.trades.total) {
            const total = data.trades.total.total || 0;
            const won = data.trades.won ? data.trades.won.total : 0;
            const lost = data.trades.lost ? data.trades.lost.total : 0;
            const winRate = total > 0 ? ((won / total) * 100).toFixed(2) : 0;

            tradesInfo.innerHTML = `
                <p><strong>Всего сделок:</strong> ${total}</p>
                <p><strong>Прибыльных:</strong> ${won}</p>
                <p><strong>Убыточных:</strong> ${lost}</p>
                <p><strong>Процент побед:</strong> ${winRate}%</p>
            `;
        } else {
            tradesInfo.innerHTML = '<p>Нет данных о сделках</p>';
        }

        results.style.display = 'block';
        results.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showError(message) {
        document.getElementById('error_message').textContent = message;
        error.style.display = 'block';
        error.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});
