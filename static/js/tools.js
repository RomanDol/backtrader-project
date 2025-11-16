document.addEventListener("DOMContentLoaded", function () {
  const updateSymbolsBtn = document.getElementById("update-symbols-btn")
  const symbolsMessage = document.getElementById("symbols-message")

  if (updateSymbolsBtn) {
    updateSymbolsBtn.addEventListener("click", async function () {
      // Показываем состояние загрузки
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

  function showSymbolsMessage(text, type) {
    symbolsMessage.textContent = text
    symbolsMessage.className = "message message--" + type
    symbolsMessage.style.display = "block"
  }

  function hideSymbolsMessage() {
    symbolsMessage.style.display = "none"
  }
})
