import asyncio
import json
import getpass
from playwright.async_api import async_playwright

# L'URL d'entrée officielle qui redirige vers l'authentification Keycloak
LOGIN_URL = "https://psn.monlycee.net"

# Identifiants déportés sur le serveur AWS (sécurisé)
USERNAME = "misha.nancey"
PASSWORD = "MOT_DE_PASSE_DEPORTE_SUR_AWS"

async def main():
    print("=" * 60)
    print("  TEST DE CONNEXION AUTOMATIQUE - MONLYCEE.NET (EDGE)")
    print("=" * 60)
    username = USERNAME
    password = PASSWORD

    if not username or not password:
        print("Identifiant ou mot de passe manquant.")
        return

    print("\n[1/4] Lancement de Microsoft Edge (mode visible)...")
    async with async_playwright() as p:
        # Lancement de Microsoft Edge installé sur Windows
        browser = await p.chromium.launch(channel="msedge", headless=False, slow_mo=300)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"[2/4] Navigation vers {LOGIN_URL}...")
        await page.goto(LOGIN_URL, wait_until="networkidle")

        print(f"Page atteinte : {page.url}")
        print("[3/4] Saisie des identifiants sur le portail d'authentification...")

        try:
            # Sélecteurs exacts de la mire MonLycée / Keycloak TWIDF
            await page.wait_for_selector("#username", timeout=10000)
            await page.fill("#username", username)

            await page.wait_for_selector("#password", timeout=5000)
            await page.fill("#password", password)

            print("Clic sur le bouton de connexion (#kc-login)...")
            await page.click("#kc-login")

            # Attente de la validation et du retour sur psn.monlycee.net
            print("En attente de la redirection après connexion...")
            await page.wait_for_url(lambda url: "auth.monlycee.net" not in url, timeout=20000)
            await page.wait_for_load_state("networkidle")

            print(f"\n[SUCCES] Connecté avec succès ! URL actuelle : {page.url}")

            # 4. Récupération des cookies de session
            cookies = await context.cookies()
            print(f"[4/4] {len(cookies)} cookies de session récupérés.")

            # Sauvegarde dans un fichier local
            with open("cookies_test.json", "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print("-> Cookies sauvegardés dans 'cookies_test.json'.")

            print("\nLe navigateur Edge va rester ouvert 15 secondes pour que tu puisses voir ton espace de travail.")
            await asyncio.sleep(15)

        except Exception as e:
            print(f"\n[ERREUR] Échec de la connexion : {e}")
            print(f"URL au moment de l'erreur : {page.url}")
            print("Garde la fenêtre ouverte 10 secondes pour observer...")
            await asyncio.sleep(10)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
