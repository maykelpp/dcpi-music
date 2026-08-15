# DCPI Music — despliegue permanente en Render (sin túnel)

Todo (API + frontend + bot vía webhook) corre en **un solo servicio web**, con una URL fija tipo `https://dcpi-music.onrender.com`. Ya no depende de Termux estando prendido ni de cloudflared.

## Requisitos previos

- Cuenta en https://render.com (gratis, sin tarjeta para el plan Free)
- Tu código subido a un repo de GitHub/GitLab (Render despliega desde ahí)

## 1. Subir el proyecto a GitHub

Desde Termux o donde tengas el proyecto:
```bash
cd ~/dcpi-music-py/dcpi-music-py
git init
git add .
git commit -m "DCPI Music"
```
Crea un repo vacío en GitHub y sigue las instrucciones que te da para hacer `git push`. **Antes de subirlo**, borra el token del `.env`:
```bash
echo "backend/.env" >> .gitignore
git rm --cached backend/.env
```
El `.env` real se configura en Render (paso 3), no se sube al repo.

## 2. Crear el servicio en Render

1. En Render → **New** → **Blueprint** → conecta tu repo (usa el `render.yaml` que ya está en la raíz del proyecto).
2. Si prefieres hacerlo manual en vez de Blueprint: **New** → **Web Service** → conecta el repo → Environment: **Docker** → Plan: **Free**.

## 3. Variables de entorno (en el panel de Render, no en el repo)

- `TELEGRAM_BOT_TOKEN` = tu token de BotFather
- `WEBAPP_URL` = la URL que Render te asigna (algo como `https://dcpi-music.onrender.com`) — **agrégala después del primer deploy**, cuando ya sepas la URL real
- `GENIUS_API_KEY` = opcional
- `TELEGRAM_WEBHOOK_SECRET` = cualquier cadena random que inventes (protege el webhook)

Tras el primer deploy, copia la URL que te dio Render, pégala en `WEBAPP_URL`, y Render redesplegará solo. Al arrancar, la app registra el webhook de Telegram automáticamente (`register_webhook()` en `main.py`).

## 4. Probar

```bash
curl https://dcpi-music.onrender.com/health
```
Y en Telegram: `/start` a tu bot → debería mostrar el botón "🔎 Abrir DCPI Music" ya funcional, sin depender de que tu celular/Termux esté prendido.

## Limitaciones a tener en cuenta (plan Free de Render)

- El servicio "duerme" tras ~15 min sin tráfico y tarda unos segundos en despertar con la primera petición.
- El disco es efímero: el historial/favoritos en SQLite se pierde en cada redeploy o reinicio del contenedor. Si te importa que persista, el siguiente paso sería mover esas tablas a una base de datos gestionada (Render tiene Postgres gratis) — puedo ayudarte con eso cuando quieras.

## Desarrollo local (Termux) sigue funcionando igual

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000
```
Sin `WEBAPP_URL` configurada (o con el valor placeholder), `register_webhook()` se salta solo — no rompe nada correr local sin bot conectado.
