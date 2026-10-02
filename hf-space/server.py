import os
import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn

# ==========================================
# CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT
# (À renseigner dans les "Secrets" du Space Hugging Face)
# ==========================================
API_KEY = os.getenv("API_KEY", "monlycee-secret-key-oracle-2026")
ENT_USER = os.getenv("ENT_USER", "misha.nancey")
ENT_PASS = os.getenv("ENT_PASS", "MOT_DE_PASSE_DEPORTE_SUR_AWS")

# Durée de validité du cache en secondes (ex: 25 minutes = 1500s)
CACHE_TTL = int(os.getenv("CACHE_TTL", "1500"))

# Plages horaires autorisées (ex: 0 à 24 = toujours actif, ou 8 à 22)
ALLOWED_START_HOUR = int(os.getenv("ALLOWED_START_HOUR", "0"))
ALLOWED_END_HOUR = int(os.getenv("ALLOWED_END_HOUR", "24"))

LOGIN_URL = "https://psn.monlycee.net"

app = FastAPI(title="MonLycée Auth Relay", version="1.0.0")

# Autoriser les requêtes CORS depuis l'extension Edge
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# GESTION DU CACHE ET CONCURRENCE
# ==========================================
cached_cookies = None
cache_timestamp = 0
login_lock = asyncio.Lock()

def is_within_allowed_hours() -> bool:
    current_hour = datetime.now().hour
    if ALLOWED_START_HOUR == 0 and ALLOWED_END_HOUR == 24:
        return True
    return ALLOWED_START_HOUR <= current_hour < ALLOWED_END_HOUR

async def fetch_fresh_cookies():
    """Lance Chromium en headless pour effectuer la connexion et extraire les cookies."""
    global cached_cookies, cache_timestamp

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lancement de Playwright pour une nouvelle session...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. Navigation
            await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)

            # 2. Remplissage des identifiants
            await page.wait_for_selector("#username", timeout=15000)
            await page.fill("#username", ENT_USER)

            await page.wait_for_selector("#password", timeout=10000)
            await page.fill("#password", ENT_PASS)

            # 3. Clic sur connexion
            await page.click("#kc-login")

            # 4. Attente de la redirection vers l'espace connecté
            await page.wait_for_url(lambda url: "auth.monlycee.net" not in url, timeout=25000)
            await page.wait_for_load_state("networkidle")

            # 5. Extraction
            cookies = await context.cookies()
            if not cookies:
                raise Exception("Aucun cookie n'a pu être extrait après connexion.")

            cached_cookies = cookies
            cache_timestamp = time.time()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Succès : {len(cookies)} cookies mis en cache pour {CACHE_TTL}s.")
            return cookies

        finally:
            await browser.close()

# ==========================================
# ENDPOINTS API
# ==========================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "MonLycee Auth Relay (Hugging Face)",
        "cache_active": cached_cookies is not None and (time.time() - cache_timestamp < CACHE_TTL)
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "has_cached_session": cached_cookies is not None,
        "cache_age_seconds": round(time.time() - cache_timestamp, 1) if cached_cookies else None
    }

@app.post("/clear-cache")
async def clear_cache(authorization: str = Header(None)):
    global cached_cookies, cache_timestamp
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Non autorisé : Clé API invalide")
    cached_cookies = None
    cache_timestamp = 0
    return {"status": "ok", "message": "Cache réinitialisé"}

@app.get("/get-cookies")
async def get_cookies(authorization: str = Header(None), force: bool = False):
    # 1. Vérification de la clé secrète
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Non autorisé : Clé API invalide")

    # 2. Vérification des règles horaires (Discipline / Cold Turkey)
    if not is_within_allowed_hours():
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé par les règles horaires (autorisé de {ALLOWED_START_HOUR}h à {ALLOWED_END_HOUR}h)."
        )

    # 3. Vérification du cache mémoire (si force=False)
    now = time.time()
    if not force and cached_cookies and (now - cache_timestamp < CACHE_TTL):
        return {
            "status": "ok",
            "source": "cache",
            "age_seconds": round(now - cache_timestamp, 1),
            "cookies": cached_cookies
        }

    # 4. Verrouillage pour générer une nouvelle session propre
    async with login_lock:
        if not force and cached_cookies and (time.time() - cache_timestamp < CACHE_TTL):
            return {
                "status": "ok",
                "source": "cache",
                "cookies": cached_cookies
            }

        try:
            cookies = await fetch_fresh_cookies()
            return {
                "status": "ok",
                "source": "fresh",
                "cookies": cookies
            }
        except Exception as e:
            print(f"[ERREUR] Échec de récupération de session: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur d'authentification: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
