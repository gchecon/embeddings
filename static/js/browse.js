(function () {
  const backdrop   = document.getElementById("modal-backdrop");
  const modalPath  = document.getElementById("modal-path");
  const modalList  = document.getElementById("modal-list");
  const modalSel   = document.getElementById("modal-selected");
  const confirmBtn = document.getElementById("modal-confirm");
  const dirInput   = document.getElementById("dir-input");

  let currentPath = "";
  let selectedPath = "";

  document.getElementById("browse-btn").addEventListener("click", () => {
    selectedPath = "";
    confirmBtn.disabled = true;
    modalSel.textContent = "Nenhum diretório selecionado";
    backdrop.classList.add("open");
    navigate("");
  });

  document.getElementById("modal-close").addEventListener("click", close);
  document.getElementById("modal-cancel").addEventListener("click", close);
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });

  confirmBtn.addEventListener("click", () => {
    if (selectedPath) {
      dirInput.value = selectedPath;
      close();
    }
  });

  function close() {
    backdrop.classList.remove("open");
  }

  async function navigate(path) {
    modalList.innerHTML = '<li style="color:#aaa;padding:.75rem 1.25rem">Carregando...</li>';
    const url = "/browse" + (path ? "?path=" + encodeURIComponent(path) : "");

    let data;
    try {
      const res = await fetch(url);
      data = await res.json();
    } catch {
      modalList.innerHTML = '<li style="color:red;padding:.75rem 1.25rem">Erro ao carregar diretório.</li>';
      return;
    }

    if (data.error) {
      modalList.innerHTML = `<li style="color:red;padding:.75rem 1.25rem">${data.error}</li>`;
      return;
    }

    currentPath = data.path;
    modalPath.textContent = currentPath || "Raiz";

    modalList.innerHTML = "";

    // Botão de subir
    if (data.parent !== null && data.parent !== undefined) {
      const li = document.createElement("li");
      li.className = "up";
      li.textContent = ".. Subir";
      li.addEventListener("click", () => navigate(data.parent));
      modalList.appendChild(li);
    }

    if (data.dirs.length === 0) {
      const li = document.createElement("li");
      li.style.color = "#aaa";
      li.style.cursor = "default";
      li.textContent = "Nenhum subdiretório encontrado";
      li.addEventListener("click", () => {
        // Selecionar o diretório atual mesmo sem subpastas
        select(currentPath);
      });
      modalList.appendChild(li);
    }

    for (const dir of data.dirs) {
      const li = document.createElement("li");
      const fullPath = currentPath ? (currentPath.replace(/[\\/]$/, "") + (currentPath.includes("\\") ? "\\" : "/") + dir) : dir;
      li.textContent = dir;

      li.addEventListener("click", (e) => {
        // Single click: seleciona; double click: navega
        if (e.detail === 2) {
          navigate(fullPath);
        } else {
          select(fullPath);
          // Highlight
          modalList.querySelectorAll("li").forEach(l => l.style.background = "");
          li.style.background = "#e8eeff";
        }
      });

      modalList.appendChild(li);
    }
  }

  function select(path) {
    selectedPath = path;
    modalSel.textContent = path;
    confirmBtn.disabled = false;
  }
})();
