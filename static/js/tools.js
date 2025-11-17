document.addEventListener("DOMContentLoaded", function () {
  const updateSymbolsBtn = document.getElementById("update-symbols-btn")
  const symbolsMessage = document.getElementById("symbols-message")
  const symbolSelect = document.getElementById("symbol-select")
  const downloadForm = document.getElementById("download-data-form")
  const downloadMessage = document.getElementById("download-message")
  const downloadProgress = document.getElementById("download-progress")
  const progressBar = document.getElementById("progress-bar")
  const progressText = document.getElementById("progress-text")

  // === Обновление списка символов ===
  if (updateSymbolsBtn) {
    updateSymbolsBtn.addEventListener("click", async function () {
      updateSymbolsBtn.disabled = true
      updateSymbolsBtn.innerHTML =
        '<span class="btn-icon">⏳</span> Обновляем...'
      hideSymbolsMessage()

      try {
        const response = await fetch("/api/update_symbols", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        })

        const result = await response.json()

        if (response.ok && result.status === "success") {
          showSymbolsMessage(
            result.message || "Символы успешно обновлены",
            "success"
          )
          // Перезагружаем список символов в select
          loadSymbols()
        } else {
          showSymbolsMessage(
            result.message || "Ошибка обновления символов",
            "error"
          )
        }
      } catch (error) {
        showSymbolsMessage("Ошибка соединения с сервером", "error")
      } finally {
        updateSymbolsBtn.disabled = false
        updateSymbolsBtn.innerHTML =
          '<span class="btn-icon">🔄</span> Update Symbols List'
      }
    })
  }

  // === Загрузка списка символов в select ===
  async function loadSymbols() {
    try {
      const response = await fetch("/api/get_symbols")
      const result = await response.json()

      if (response.ok && result.status === "success") {
        symbolSelect.innerHTML = '<option value="">Select symbol...</option>'
        result.symbols.forEach((symbol) => {
          const option = document.createElement("option")
          option.value = symbol
          option.textContent = symbol
          symbolSelect.appendChild(option)
        })
      } else {
        symbolSelect.innerHTML =
          '<option value="">Error loading symbols</option>'
      }
    } catch (error) {
      symbolSelect.innerHTML = '<option value="">Error loading symbols</option>'
    }
  }

  // Загружаем символы при загрузке страницы
  loadSymbols()

  // === Обработка формы загрузки данных ===
  if (downloadForm) {
    downloadForm.addEventListener("submit", async function (e) {
      e.preventDefault()

      const formData = new FormData(downloadForm)
      const data = {
        symbol: formData.get("symbol"),
        timeframe: formData.get("timeframe"),
        period: formData.get("period"),
        start_date: formData.get("start_date"),
        end_date: formData.get("end_date"),
      }

      // Скрываем предыдущие сообщения
      hideDownloadMessage()
      showProgress(0, "Preparing download...")

      try {
        const response = await fetch("/api/download_historical_data", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        })

        const result = await response.json()

        if (response.ok && result.status === "success") {
          showProgress(100, "Download complete!")
          setTimeout(() => {
            hideProgress()
            showDownloadMessage(
              result.message || "Данные успешно загружены",
              "success"
            )
          }, 1000)
        } else {
          hideProgress()
          showDownloadMessage(
            result.message || "Ошибка загрузки данных",
            "error"
          )
        }
      } catch (error) {
        hideProgress()
        showDownloadMessage("Ошибка соединения с сервером", "error")
      }
    })
  }

  // === Вспомогательные функции ===
  function showSymbolsMessage(text, type) {
    symbolsMessage.textContent = text
    symbolsMessage.className = "message message--" + type
    symbolsMessage.style.display = "block"
  }

  function hideSymbolsMessage() {
    symbolsMessage.style.display = "none"
  }

  function showDownloadMessage(text, type) {
    downloadMessage.textContent = text
    downloadMessage.className = "message message--" + type
    downloadMessage.style.display = "block"
  }

  function hideDownloadMessage() {
    downloadMessage.style.display = "none"
  }

  function showProgress(percent, text) {
    downloadProgress.style.display = "block"
    progressBar.style.width = percent + "%"
    progressBar.textContent = percent + "%"
    progressText.textContent = text
  }

  function hideProgress() {
    downloadProgress.style.display = "none"
  }
})
