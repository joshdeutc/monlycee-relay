import os
import time
import shutil
import asyncio
from datetime import datetime
from fastapi import HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import gradio as gr
import spaces

# ==========================================
# CONFIGURATION
# (À définir dans les "Secrets" du Space Hugging Face)
# ==========================================
API_KEY = os.getenv("API_KEY", "monlycee-secret-key-oracle-2026")
ENT_USER = os.getenv("ENT_USER", "misha.nancey")
ENT_PASS = os.getenv("ENT_PASS", "MOT_DE_PASSE_DEPORTE_SUR_AWS")

# Durée de validité du cache en secondes (25 minutes)
CACHE_TTL = int(os.getenv("CACHE_TTL", "1500"))

ALLOWED_START_HOUR = int(os.getenv("ALLOWED_START_HOUR", "0"))
ALLOWED_END_HOUR = int(os.getenv("ALLOWED_END_HOUR", "24"))

LOGIN_URL = "https://psn.monlycee.net"

# ==========================================
# GESTION DU CACHE
# ==========================================
cached_cookies = None
cache_timestamp = 0
login_lock = asyncio.Lock()

def is_within_allowed_hours() -> bool:
    current_hour = datetime.now().hour
    if ALLOWED_START_HOUR == 0 and ALLOWED_END_HOUR == 24:
        return True
    return ALLOWED_START_HOUR <= current_hour < ALLOWED_END_HOUR

def find_chromium_path():
    """Détecte l'exécutable Chromium installé par apt (packages.txt)."""
    candidates = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

try:
    if not find_chromium_path():
        import subprocess
        subprocess.run(["playwright", "install", "chromium"], check=False)
except Exception:
    pass

async def fetch_fresh_cookies():
    """Connexion Playwright headless pour extraire les cookies."""
    global cached_cookies, cache_timestamp

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lancement Playwright...")
    chromium_path = find_chromium_path()
    launch_kwargs = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    }
    if chromium_path:
        launch_kwargs["executable_path"] = chromium_path

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(LOGIN_URL, wait_until="networkidle", timeout=35000)
            await page.wait_for_selector("#username", timeout=15000)
            await page.fill("#username", ENT_USER)

            await page.wait_for_selector("#password", timeout=10000)
            await page.fill("#password", ENT_PASS)

            await page.click("#kc-login")
            await page.wait_for_url(lambda url: "auth.monlycee.net" not in url, timeout=25000)
            await page.wait_for_load_state("networkidle")

            cookies = await context.cookies()
            if not cookies:
                raise Exception("Aucun cookie extrait.")

            cached_cookies = cookies
            cache_timestamp = time.time()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Succès: {len(cookies)} cookies en cache.")
            return cookies
        finally:
            await browser.close()

# ==========================================
# INTERFACE VISUELLE GRADIO
# ==========================================
with gr.Blocks(title="MonLycée Auth Relay") as demo:
    gr.Markdown("# 🎓 MonLycée Auth Relay")
    gr.Markdown("Serveur d'authentification déporté sécurisé en ligne.")

    with gr.Row():
        status_box = gr.Textbox(
            label="État du service",
            value="🟢 En ligne - Prêt à relayer l'authentification",
            interactive=False
        )

    with gr.Row():
        btn_test = gr.Button("⚡ Tester la connexion MonLycée", variant="primary")
        test_output = gr.Textbox(label="Résultat du test", interactive=False)

    # Décoration obligatoire @spaces.GPU sur la fonction appelée par le bouton
    @spaces.GPU
    def gradio_test_login():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cookies = loop.run_until_complete(fetch_fresh_cookies())
            return f"✅ Succès ! {len(cookies)} cookies de session récupérés et mis en cache."
        except Exception as e:
            return f"❌ Erreur : {str(e)}"

    btn_test.click(fn=gradio_test_login, inputs=[], outputs=[test_output])

# ==========================================
# ROUTES API POUR L'EXTENSION EDGE
# ==========================================
demo.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@demo.app.get("/health")
def api_health():
    return {
        "status": "healthy",
        "has_cached_session": cached_cookies is not None,
        "cache_age_seconds": round(time.time() - cache_timestamp, 1) if cached_cookies else None
    }

@demo.app.post("/clear-cache")
async def api_clear_cache(authorization: str = Header(None)):
    global cached_cookies, cache_timestamp
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Non autorisé")
    cached_cookies = None
    cache_timestamp = 0
    return {"status": "ok", "message": "Cache réinitialisé"}

@demo.app.get("/get-cookies")
async def api_get_cookies(authorization: str = Header(None), force: bool = False):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Non autorisé : Clé API invalide")

    if not is_within_allowed_hours():
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé par les règles horaires ({ALLOWED_START_HOUR}h à {ALLOWED_END_HOUR}h)."
        )

    now = time.time()
    if not force and cached_cookies and (now - cache_timestamp < CACHE_TTL):
        return {
            "status": "ok",
            "source": "cache",
            "age_seconds": round(now - cache_timestamp, 1),
            "cookies": cached_cookies
        }

    async with login_lock:
        if not force and cached_cookies and (time.time() - cache_timestamp < CACHE_TTL):
            return {"status": "ok", "source": "cache", "cookies": cached_cookies}

        try:
            cookies = await fetch_fresh_cookies()
            return {"status": "ok", "source": "fresh", "cookies": cookies}
        except Exception as e:
            print(f"[ERREUR] {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    demo.launch()
