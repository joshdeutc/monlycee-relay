// popup.js - Contrôleur de l'interface utilisateur

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const btnConnect = document.getElementById("btnConnect");
const btnConnectText = document.getElementById("btnConnectText");
const btnOpen = document.getElementById("btnOpen");
const serverUrlInput = document.getElementById("serverUrl");
const apiKeyInput = document.getElementById("apiKey");
const btnSaveConfig = document.getElementById("btnSaveConfig");

const DEFAULT_SERVER_URL = "https://15-224-218-240.sslip.io";
const DEFAULT_API_KEY = "monlycee-secret-key-oracle-2026";

// Charger les paramètres au démarrage
chrome.storage.sync.get(["serverUrl", "apiKey"], (items) => {
  serverUrlInput.value = items.serverUrl || DEFAULT_SERVER_URL;
  apiKeyInput.value = items.apiKey || DEFAULT_API_KEY;
  setStatus("ready", "Prêt pour la connexion");
});

// Enregistrer les paramètres
btnSaveConfig.addEventListener("click", () => {
  const serverUrl = serverUrlInput.value.trim().replace(/\/$/, "");
  const apiKey = apiKeyInput.value.trim();

  chrome.storage.sync.set({ serverUrl, apiKey }, () => {
    setStatus("ready", "Paramètres sauvegardés !");
    setTimeout(() => setStatus("ready", "Prêt pour la connexion"), 2000);
  });
});

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
