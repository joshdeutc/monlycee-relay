# Image officielle Microsoft Playwright avec Chromium préinstallé
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# Hugging Face exige que le conteneur tourne avec l'utilisateur UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copie des dépendances et installation
COPY --chown=user requirements.txt $HOME/app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code du serveur
COPY --chown=user . $HOME/app/

# Port standard exposé par Hugging Face Spaces (7860)
EXPOSE 7860

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
