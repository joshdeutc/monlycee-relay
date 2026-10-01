# 🎓 MonLycée Auto-Connect & Auth Relay

Système d'authentification déportée sécurisée pour **MonLycée.net** / **psn.monlycee.net**.

Ce projet permet de déporter la saisie et le stockage des identifiants ENT sur un serveur distant sécurisé, afin d'injecter automatiquement les cookies de session dans **Microsoft Edge** sans que le mot de passe ne soit physiquement présent sur la machine locale. Utilisé en combinaison avec **Cold Turkey Blocker**, ce système permet un contrôle numérique rigoureux sans bloquer l'accès à l'espace de travail scolaire.

---

## 🏛️ Architecture du Projet

```
[ Serveur Distant / Local ]
   FastAPI + Playwright (Headless Chromium)
   - Cache de session en RAM (réponse < 50ms)
   - Route GET /get-cookies (avec Bearer API_KEY)
   - Route POST /clear-cache
   - Plages horaires configurables (Discipline)
        ▲
        │ HTTPS sécurisé (ou local)
        ▼
[ Navigateur Local - Microsoft Edge ]
   Extension Manifest V3 (edge-extension/)
   - Bouton "⚡ Se connecter à MonLycée" (1 clic)
   - Bouton "🔄 Forcer une nouvelle session"
   - Bouton "🧹 Déconnexion (Vider les cookies)"
   - Injection transparente des cookies via chrome.cookies.set()
```

---

## 📁 Structure des Dossiers

- **`edge-extension/`** : L'extension Microsoft Edge (Manifest V3) complète et prête à charger (`edge://extensions`).
  - `manifest.json` : Déclaration et permissions cookies/storage.
  - `popup.html`, `popup.css`, `popup.js` : Interface Fluent moderne avec statuts et paramètres.
  - `background.js` : Service worker d'injection et de synchronisation des cookies.
  - `icons/` : Icônes de l'extension.
- **`server/`** : Le serveur FastAPI principal à déployer sur le Cloud (AWS / Oracle / VPS).
  - `server.py` : Serveur FastAPI avec Playwright, cache en mémoire et mutex lock.
  - `requirements.txt` : Dépendances Python (FastAPI, Uvicorn, Playwright, python-dotenv).
  - `setup_oracle.sh` : Script Bash d'installation automatique pour machine Ubuntu (crée 2 Go de swap, installe Chromium et active un service systemd permanent).
- **`hf-gradio/`** & **`hf-space/`** : Fichiers de test pour Hugging Face Spaces.
- **`test_login.py`** : Script local de test Playwright autonome qui valide les sélecteurs de MonLycée.

---

## 🚀 État d'Avancement & Ce qui fonctionne déjà

1. **Extraction et injection validées à 100%** :
   - URL d'entrée vérifiée : `https://psn.monlycee.net`
   - Redirection Keycloak TWIDF : `#username`, `#password`, bouton `#kc-login`.
   - 16 cookies de session extraits et réinjectés avec succès dans Edge sans aucune mire de mot de passe.
2. **Extension Microsoft Edge** :
   - Fonctionnelle et testée en local.
   - Supporte la connexion instantanée par cache, la déconnexion avec purge locale et serveur, et le refresh forcé de session.
3. **Prochaine étape** :
   - Déployer le dossier `server/` sur une machine distante ayant une adresse IP européenne/française (ex: AWS EC2 gratuit 12 mois à Paris `eu-west-3`, ou VPS Ionos/OVH à 1€).
   - Renseigner l'URL distante dans les paramètres de l'extension Edge.
   - Verrouiller la machine distante avec Cold Turkey Blocker sur le PC.

---

## 💻 Démarrage Rapide en Local

### 1. Lancer le serveur local
```powershell
cd server
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

### 2. Charger l'extension dans Edge
1. Ouvre `edge://extensions`.
2. Active le **Mode développeur** (en bas à gauche).
3. Clique sur **Charger les fichiers décompressés**.
4. Sélectionne le dossier `edge-extension`.
5. Clique sur l'icône de l'extension puis sur **⚡ Se connecter à MonLycée**.
