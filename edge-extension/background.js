// Configuration obfusquée (aucune adresse IP lisible en clair)
const DEFAULT_SERVER_URL = atob("aHR0cHM6Ly8xNS0yMjQtMjE4LTI0MC5zc2xpcC5pbw==");
const DEFAULT_API_KEY = atob("bW9ubHljZWUtc2VjcmV0LWtleS1vcmFjbGUtMjAyNg==");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "SYNC_COOKIES") {
    handleSyncCookies(Boolean(request.force))
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Indique une réponse asynchrone
  }

  if (request.action === "CLEAR_COOKIES") {
    handleClearCookies()
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

async function handleSyncCookies(force = false) {
  const config = await chrome.storage.sync.get(["serverUrl", "apiKey"]);
  const serverUrl = (config.serverUrl || DEFAULT_SERVER_URL).replace(/\/$/, "");
  const apiKey = config.apiKey || DEFAULT_API_KEY;

  const endpoint = `${serverUrl}/get-cookies${force ? "?force=true" : ""}`;

  let response;
  try {
    response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      }
    });
  } catch (netErr) {
    throw new Error("Serveur injoignable (" + netErr.message + ")");
  }

  if (response.status === 401) {
    throw new Error("Clé secrète non autorisée (401)");
  }
  if (response.status === 403) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Accès restreint par les règles horaires (403)");
  }
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Erreur serveur (${response.status})`);
  }

  const data = await response.json();
  const cookies = data.cookies;

  if (!Array.isArray(cookies) || cookies.length === 0) {
    throw new Error("Aucun cookie reçu du serveur");
  }

  let injectedCount = 0;

  for (const cookie of cookies) {
    const domainClean = cookie.domain.replace(/^\./, "");
    const protocol = cookie.secure ? "https://" : "http://";
    const cookieUrl = `${protocol}${domainClean}${cookie.path || "/"}`;

    const cookieDetails = {
      url: cookieUrl,
      name: cookie.name,
      value: cookie.value,
      domain: cookie.domain,
      path: cookie.path || "/",
      secure: Boolean(cookie.secure),
      httpOnly: Boolean(cookie.httpOnly)
    };

    // Gestion du même site (SameSite)
    if (cookie.sameSite) {
      const ss = String(cookie.sameSite).toLowerCase();
      if (ss === "none") {
        cookieDetails.sameSite = "no_restriction";
      } else if (ss === "lax") {
        cookieDetails.sameSite = "lax";
      } else if (ss === "strict") {
        cookieDetails.sameSite = "strict";
      }
    }

    // Gestion de l'expiration
    if (cookie.expires && cookie.expires > 0) {
      cookieDetails.expirationDate = cookie.expires;
    }

    try {
      await chrome.cookies.set(cookieDetails);
      injectedCount++;
    } catch (cookieErr) {
      console.warn(`Impossible d'injecter le cookie ${cookie.name}:`, cookieErr);
    }
  }

  return { success: true, count: injectedCount };
}

async function handleClearCookies() {
  let removedCount = 0;
  try {
    const allCookies = await chrome.cookies.getAll({});
    const targetCookies = allCookies.filter(
      (c) => c.domain.includes("monlycee") || c.domain.includes("iledefrance")
    );

    for (const cookie of targetCookies) {
      const cleanDomain = cookie.domain.replace(/^\./, "");
      const protocol = cookie.secure ? "https://" : "http://";
      const url = `${protocol}${cleanDomain}${cookie.path || "/"}`;
      try {
        await chrome.cookies.remove({ url: url, name: cookie.name });
        removedCount++;
      } catch (e) {
        console.warn("Erreur suppression cookie:", cookie.name, e);
      }
    }
    // 2. Réinitialiser également le cache mémoire du serveur
    try {
      const config = await chrome.storage.sync.get(["serverUrl", "apiKey"]);
      const serverUrl = (config.serverUrl || DEFAULT_SERVER_URL).replace(/\/$/, "");
      const apiKey = config.apiKey || DEFAULT_API_KEY;
      await fetch(`${serverUrl}/clear-cache`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${apiKey}` }
      });
    } catch (e) {
      console.warn("Impossible de réinitialiser le cache serveur:", e);
    }

    return { success: true, removed: removedCount };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
