// popup.js - Contrôleur de l'interface utilisateur

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const btnConnect = document.getElementById("btnConnect");
const btnConnectText = document.getElementById("btnConnectText");
const btnOpen = document.getElementById("btnOpen");

// Initialisation de l'interface
setStatus("ready", "Prêt pour la connexion");

// Clic sur "Se connecter à MonLycée" (utilise le cache si disponible)
btnConnect.addEventListener("click", () => triggerLogin(false));

// Clic sur "Forcer une nouvelle session" (bypass le cache et génère des cookies neufs)
const btnForceConnect = document.getElementById("btnForceConnect");
btnForceConnect.addEventListener("click", () => triggerLogin(true));

function triggerLogin(force = false) {
  setStatus("loading", force ? "Création session fraîche (Playwright)..." : "Connexion au serveur...");
  btnConnect.disabled = true;
  btnForceConnect.disabled = true;

  chrome.runtime.sendMessage({ action: "SYNC_COOKIES", force: force }, (response) => {
    btnConnect.disabled = false;
    btnForceConnect.disabled = false;
    if (chrome.runtime.lastError) {
      setStatus("error", "Erreur: Service worker inaccessible");
      console.error(chrome.runtime.lastError);
      return;
    }

    if (response && response.success) {
      setStatus("ready", `Connecté (${response.count} cookies injectés)`);
      btnConnectText.textContent = "Session active";
      // Ouvre MonLycée dans un nouvel onglet
      chrome.tabs.create({ url: "https://psn.monlycee.net/" });
    } else {
      const errMsg = response?.error || "Échec de connexion";
      setStatus("error", errMsg);
      btnConnectText.textContent = "Réessayer";
    }
  });
}

// Clic sur "Ouvrir MonLycée"
btnOpen.addEventListener("click", () => {
  chrome.tabs.create({ url: "https://psn.monlycee.net/" });
});

// Clic sur "Déconnexion (Vider les cookies)"
const btnClearCookies = document.getElementById("btnClearCookies");
btnClearCookies.addEventListener("click", () => {
  setStatus("loading", "Suppression des cookies...");
  chrome.runtime.sendMessage({ action: "CLEAR_COOKIES" }, (response) => {
    if (response && response.success) {
      setStatus("ready", `Session vidée (${response.removed} cookies supprimés)`);
      btnConnectText.textContent = "Se connecter à MonLycée";
    } else {
      const msg = response?.error || "Erreur lors de la suppression";
      setStatus("error", msg);
    }
  });
});

function setStatus(type, message) {
  statusDot.className = "status-dot " + type;
  statusText.textContent = message;
}
