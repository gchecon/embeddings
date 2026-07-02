(function () {
  function formatDuration(seconds) {
    if (seconds === undefined || seconds === null) return "";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}min ${s}s`;
  }

  const scanBtn = document.getElementById("scan-btn");
  const dirInput = document.getElementById("dir-input");
  const progressSection = document.getElementById("progress-section");
  const progressBar = document.getElementById("progress-bar");
  const statusText = document.getElementById("status-text");
  const logArea = document.getElementById("log-area");

  let evtSource = null;

  scanBtn.addEventListener("click", async () => {
    const directory = dirInput.value.trim();
    if (!directory) {
      alert("Informe o caminho do diretório.");
      return;
    }

    scanBtn.disabled = true;
    progressSection.style.display = "block";
    progressBar.style.width = "0%";
    logArea.innerHTML = "";
    statusText.textContent = "Iniciando varredura...";

    // Close any existing stream
    if (evtSource) {
      evtSource.close();
    }

    // Start the scan
    const res = await fetch("/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directory }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      statusText.textContent = "Erro: " + (err.error || res.statusText);
      scanBtn.disabled = false;
      return;
    }

    // Open SSE stream
    evtSource = new EventSource("/progress");

    evtSource.onmessage = (event) => {
      if (!event.data || event.data === "{}") return;

      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.status === "start") {
        const gpu = data.device === "cuda" ? `GPU (${data.gpu_name || "desconhecida"})` : "CPU";
        statusText.textContent = `Iniciando indexação de ${data.total} arquivo(s) usando ${gpu}...`;
        const p = document.createElement("p");
        p.textContent = `⚙️ Dispositivo: ${gpu}`;
        logArea.appendChild(p);
        logArea.scrollTop = logArea.scrollHeight;
        return;
      }

      if (data.status === "summary") {
        const p = document.createElement("p");
        p.innerHTML = `<strong>📊 Relatório final:</strong> ${data.indexed} indexado(s), ${data.skipped} pulado(s), ${data.errors} erro(s) — ` +
          `${data.total_chunks} chunk(s), ${data.total_tokens} token(s) — tempo total: ${formatDuration(data.total_time_seconds)}`;
        logArea.appendChild(p);
        logArea.scrollTop = logArea.scrollHeight;
        return;
      }

      if (data.status === "done") {
        statusText.textContent = "Varredura concluída!";
        progressBar.style.width = "100%";
        evtSource.close();
        scanBtn.disabled = false;
        return;
      }

      const pct = data.total > 0 ? Math.round((data.done / data.total) * 100) : 0;
      progressBar.style.width = pct + "%";
      statusText.textContent = `Processando ${data.done}/${data.total}...`;

      const p = document.createElement("p");
      const icon = data.status === "error" ? "❌" : data.status === "skipped" ? "⏭" : "✅";
      let detail = "";
      if (data.status === "error") {
        detail = ` — ${data.error || "erro desconhecido"}`;
      } else if (data.status === "indexed") {
        detail = ` — ${data.chunks} chunk(s), ${data.tokens} token(s)`;
      }
      const time = data.elapsed_seconds !== undefined ? ` (${formatDuration(data.elapsed_seconds)})` : "";
      p.textContent = `${icon} ${data.file} — ${data.status}${detail}${time}`;
      logArea.appendChild(p);
      logArea.scrollTop = logArea.scrollHeight;
    };

    evtSource.onerror = () => {
      statusText.textContent = "Conexão com o servidor perdida.";
      evtSource.close();
      scanBtn.disabled = false;
    };
  });
})();
