// Ждём пока библиотека точно загрузится
if (typeof LightweightCharts === "undefined") {
  console.error("LightweightCharts not loaded yet, retrying...")
  setTimeout(() => {
    window.location.reload()
  }, 1000)
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("Backtest page loaded")

  // === Элементы формы ===
  const symbolSelect = document.getElementById("symbol-select")
  const timeframeSelect = document.getElementById("timeframe-select")
  const startDateInput = document.getElementById("start-date")
  const endDateInput = document.getElementById("end-date")
  const backtestForm = document.getElementById("backtest-form")
  const backtestMessage = document.getElementById("backtest-message")
  const resultsTable = document.getElementById("results-table")

  const strategySelect = document.getElementById("strategy-select")
  const strategyParamsContainer = document.getElementById(
    "strategy-params-container"
  )

  console.log("Form elements found:", {
    symbolSelect: !!symbolSelect,
    timeframeSelect: !!timeframeSelect,
    backtestForm: !!backtestForm,
  })

  // Хранилище доступных данных
  let availableData = []

  // Хранилище доступных стратегий
  let availableStrategies = []
  let selectedStrategy = null

  // Переменные для графиков (инициализируем позже)
  let candlestickChart = null
  let candlestickSeries = null
  let equityChart = null
  let equitySeries = null

  // === Функции сообщений (определяем в начале) ===
  function showMessage(text, type) {
    if (!backtestMessage) {
      console.log("Message:", text, type)
      return
    }
    backtestMessage.textContent = text
    backtestMessage.className = "message message--" + type
    backtestMessage.style.display = "block"
  }

  // === Инициализация графиков (только если элементы существуют) ===
  function initCharts() {
    const candlestickContainer = document.getElementById("candlestick-chart")
    const equityContainer = document.getElementById("equity-chart")

    if (!candlestickContainer || !equityContainer) {
      console.warn("Chart containers not found")
      return
    }

    if (typeof LightweightCharts === "undefined") {
      console.error("LightweightCharts library not loaded")
      return
    }

    try {
      // 1. Candlestick Chart
      candlestickChart = LightweightCharts.createChart(candlestickContainer, {
        width: candlestickContainer.clientWidth,
        height: candlestickContainer.clientHeight,
        layout: {
          background: { color: "#0a0e17" },
          textColor: "#d1d4dc",
        },
        grid: {
          vertLines: { color: "#1e2330" },
          horzLines: { color: "#1e2330" },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
          borderColor: "#2e3442",
        },
        timeScale: {
          borderColor: "#2e3442",
          timeVisible: true,
          secondsVisible: false,
        },
      })

      candlestickSeries = candlestickChart.addCandlestickSeries({
        upColor: "#026c3a",
        downColor: "#ff4444",
        borderUpColor: "#026c3a",
        borderDownColor: "#ff4444",
        wickUpColor: "#00ff88",
        wickDownColor: "#ff4444",
      })

      // 2. Equity Chart
      equityChart = LightweightCharts.createChart(equityContainer, {
        width: equityContainer.clientWidth,
        height: equityContainer.clientHeight,
        layout: {
          background: { color: "#0a0e17" },
          textColor: "#d1d4dc",
        },
        grid: {
          vertLines: { color: "#1e2330" },
          horzLines: { color: "#1e2330" },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
          borderColor: "#2e3442",
        },
        timeScale: {
          borderColor: "#2e3442",
          timeVisible: true,
          secondsVisible: false,
        },
      })

      equitySeries = equityChart.addLineSeries({
        color: "#00ff88",
        lineWidth: 2,
      })

      console.log("Charts initialized successfully")

      // === Обработка изменения размера окна ===
      window.addEventListener("resize", () => {
        if (candlestickChart) {
          candlestickChart.applyOptions({
            width: candlestickContainer.clientWidth,
            height: candlestickContainer.clientHeight,
          })
        }
        if (equityChart) {
          equityChart.applyOptions({
            width: equityContainer.clientWidth,
            height: equityContainer.clientHeight,
          })
        }
      })
    } catch (error) {
      console.error("Error initializing charts:", error)
    }
  }

  // Инициализируем графики
  initCharts()

  // === Загрузка доступных данных ===
  async function loadAvailableData() {
    console.log("Loading available data...")
    try {
      const response = await fetch("/api/get_available_data")
      console.log("Response status:", response.status)

      const result = await response.json()
      console.log("Result:", result)

      if (response.ok && result.status === "success") {
        availableData = result.data
        console.log("Available data loaded:", availableData)

        // Заполняем select символов
        const symbols = [...new Set(availableData.map((d) => d.symbol))]
        console.log("Unique symbols:", symbols)

        symbolSelect.innerHTML =
          '<option value="">Select symbol...</option>' +
          symbols.map((s) => `<option value="${s}">${s}</option>`).join("")

        console.log("Symbols populated:", symbols.length)
      } else {
        showMessage("Error loading available data", "error")
      }
    } catch (error) {
      showMessage("Connection error: " + error.message, "error")
      console.error("Load available data error:", error)
    }
  }

  // === Загрузка списка стратегий ===
  async function loadStrategies() {
    try {
      const response = await fetch("/api/strategies")
      const data = await response.json()

      if (data.success && data.strategies) {
        availableStrategies = data.strategies

        // Заполняем select стратегий
        strategySelect.innerHTML =
          '<option value="">Select strategy...</option>'

        data.strategies.forEach((strategy, index) => {
          const option = document.createElement("option")
          option.value = index
          option.textContent = strategy.module
          strategySelect.appendChild(option)
        })

        console.log(`Loaded ${data.strategies.length} strategies`)
      }
    } catch (error) {
      console.error("Error loading strategies:", error)
      showMessage("Error loading strategies: " + error.message, "error")
    }
  }

  // === Обработчик выбора стратегии ===
  if (strategySelect) {
    strategySelect.addEventListener("change", function () {
      const strategyIndex = this.value

      if (strategyIndex === "") {
        selectedStrategy = null
        renderStrategyParams(null)
        return
      }

      selectedStrategy = availableStrategies[strategyIndex]
      console.log("Selected strategy:", selectedStrategy)
      renderStrategyParams(selectedStrategy)
    })
  }

  // === Отрисовка параметров стратегии ===
  function renderStrategyParams(strategy) {
    if (!strategyParamsContainer) return

    if (!strategy || !strategy.params) {
      strategyParamsContainer.innerHTML = ""
      return
    }

    let html = ""

    for (const [paramKey, paramConfig] of Object.entries(strategy.params)) {
      html += `
        <div class="form-group">
          <label for="strategy-param-${paramKey}">${paramConfig.label}:</label>
          <input
            type="${paramConfig.type}"
            id="strategy-param-${paramKey}"
            name="strategy_params[${paramKey}]"
            value="${paramConfig.default}"
            min="${paramConfig.min || ""}"
            max="${paramConfig.max || ""}"
            step="${paramConfig.step || ""}"
            required
          />
          ${
            paramConfig.description
              ? `<small style="color: var(--text-secondary); font-size: 0.85em;">${paramConfig.description}</small>`
              : ""
          }
        </div>
      `
    }

    strategyParamsContainer.innerHTML = html
  }

  // Загружаем доступные данные при загрузке страницы
  loadAvailableData()
  loadStrategies()

  // === Обновление таймфреймов при выборе символа ===
  symbolSelect.addEventListener("change", function () {
    const symbol = symbolSelect.value
    console.log("Symbol selected:", symbol)

    if (!symbol) {
      timeframeSelect.innerHTML =
        '<option value="">Select timeframe...</option>'
      startDateInput.value = ""
      endDateInput.value = ""
      return
    }

    // Фильтруем доступные таймфреймы для выбранного символа
    const symbolData = availableData.filter((d) => d.symbol === symbol)
    const timeframes = symbolData.map((d) => d.timeframe)

    console.log("Available timeframes for", symbol, ":", timeframes)

    timeframeSelect.innerHTML =
      '<option value="">Select timeframe...</option>' +
      timeframes.map((tf) => `<option value="${tf}">${tf}</option>`).join("")
  })

  // === Обновление дат при выборе таймфрейма ===
  timeframeSelect.addEventListener("change", function () {
    const symbol = symbolSelect.value
    const timeframe = timeframeSelect.value

    console.log("Timeframe selected:", timeframe)

    if (!symbol || !timeframe) {
      startDateInput.value = ""
      endDateInput.value = ""
      return
    }

    // Находим диапазон дат для выбранной комбинации
    const dataInfo = availableData.find(
      (d) => d.symbol === symbol && d.timeframe === timeframe
    )

    if (dataInfo) {
      startDateInput.value = dataInfo.start_date
      endDateInput.value = dataInfo.end_date
      startDateInput.min = dataInfo.start_date
      startDateInput.max = dataInfo.end_date
      endDateInput.min = dataInfo.start_date
      endDateInput.max = dataInfo.end_date

      console.log(
        "Date range set:",
        dataInfo.start_date,
        "to",
        dataInfo.end_date
      )
    }
  })

  // === Загрузка данных для графика ===
  async function loadChartData(symbol, timeframe, startDate, endDate) {
    try {
      showMessage("Loading chart data...", "info")

      const response = await fetch("/api/get_candles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          symbol: symbol,
          timeframe: timeframe,
          start_date: startDate,
          end_date: endDate,
        }),
      })

      const result = await response.json()

      if (response.ok && result.status === "success") {
        const candles = result.candles

        if (candles.length === 0) {
          showMessage("No data available for selected parameters", "error")
          return
        }

        console.log("Loaded candles:", candles.length)

        // Обновляем график свечей
        candlestickSeries.setData(candles)

        // Генерируем equity curve (пока тестовую)
        const equityData = candles.map((candle, idx) => ({
          time: candle.time,
          value: 10000 + idx * 10,
        }))
        equitySeries.setData(equityData)

        showMessage(
          `Loaded ${candles.length} candles for ${symbol} (${timeframe})`,
          "success"
        )
      } else {
        showMessage(result.message || "Error loading chart data", "error")
      }
    } catch (error) {
      showMessage("Error loading chart data: " + error.message, "error")
      console.error("Load chart data error:", error)
    }
  }

  // === Обработка формы бэктеста ===
  if (backtestForm) {
    backtestForm.addEventListener("submit", async function (e) {
      e.preventDefault()

      const formData = new FormData(backtestForm)
      const symbol = formData.get("symbol")
      const timeframe = formData.get("timeframe")
      const startDate = formData.get("start_date")
      const endDate = formData.get("end_date")
      const initialCash = formData.get("initial_cash")
      const commission = formData.get("commission")

      // Проверяем что стратегия выбрана
      if (!selectedStrategy) {
        showMessage("Please select a strategy", "error")
        return
      }

      if (!symbol || !timeframe || !startDate || !endDate) {
        showMessage("Please fill all fields", "error")
        return
      }

      // Собираем параметры стратегии
      const strategyParams = {}
      for (const [key, config] of Object.entries(selectedStrategy.params)) {
        const value = formData.get(`strategy_params[${key}]`)
        // Преобразуем в нужный тип
        if (config.type === "number") {
          strategyParams[key] = parseFloat(value) || config.default
        } else {
          strategyParams[key] = value || config.default
        }
      }

      console.log("Starting backtest with params:", {
        symbol,
        timeframe,
        startDate,
        endDate,
        strategy: selectedStrategy.module,
        strategyParams,
      })

      showMessage("Running backtest...", "info")

      try {
        const response = await fetch("/api/backtest", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            symbol: symbol,
            timeframe: timeframe,
            start_date: startDate,
            end_date: endDate,
            strategy_module: selectedStrategy.module,
            strategy_class: selectedStrategy.class_name,
            strategy_params: strategyParams,
            initial_cash: parseFloat(initialCash),
            commission: parseFloat(commission),
          }),
        })

        const result = await response.json()

        console.log("Backtest result:", result)

        if (result.success) {
          showMessage("Backtest completed successfully", "success")
          displayResults(result.results)

          // Загружаем данные для графика
          await loadChartData(symbol, timeframe, startDate, endDate)
        } else {
          showMessage("Backtest failed: " + result.error, "error")
        }
      } catch (error) {
        showMessage("Error running backtest: " + error.message, "error")
        console.error("Backtest error:", error)
      }
    })
  }

  function showMessage(text, type) {
    backtestMessage.textContent = text
    backtestMessage.className = "message message--" + type
    backtestMessage.style.display = "block"
  }

  function displayResults(results) {
    if (!resultsTable) return

    resultsTable.innerHTML = `
      <table style="width: 100%; font-size: 14px;">
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Final Value:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold;">$${results.final_value.toFixed(
            2
          )}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Profit:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold; color: ${
            results.profit >= 0 ? "var(--color-success)" : "var(--color-error)"
          };">$${results.profit.toFixed(2)}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Return:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold; color: ${
            results.profit_percent >= 0
              ? "var(--color-success)"
              : "var(--color-error)"
          };">${results.profit_percent.toFixed(2)}%</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Sharpe Ratio:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold;">${results.sharpe_ratio.toFixed(
            2
          )}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Max Drawdown:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold; color: var(--color-error);">${results.max_drawdown.toFixed(
            2
          )}%</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: var(--text-secondary);">Total Trades:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: bold;">${
            results.total_trades
          }</td>
        </tr>
      </table>
    `
  }
})
