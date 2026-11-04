# Chatbot de Telegram Inteligente con Acceso a Internet

Este bot funciona de manera autónoma como chatbot para cualquier persona, con acceso a internet para buscar información en tiempo real, sin requerir Antigravity ni una PC encendida una vez montado en la nube.

---

## 🚀 1. Probarlo Inmediatamente en Local (Tu PC)

Haz doble clic en:
```
iniciar_bot.bat
```
O desde la terminal en esta carpeta:
```bash
python bot.py
```
Abre tu Telegram y escribe `/start` a tu bot.

---

## 🧠 2. Cómo Activar la Inteligencia Artificial (Google Gemini Gratis)

El bot incluye búsqueda web nativa. Para que responda con Inteligencia Artificial avanzada (modelo `gemini-2.0-flash` con Google Search integrado):

1. Ve a [Google AI Studio](https://aistudio.google.com/) e inicia sesión con una cuenta de Google.
2. Haz clic en **"Get API key"** (Obtener clave de API) y crea una clave gratuita.
3. Abre el archivo `.env` en esta carpeta y colócala:
   ```env
   GEMINI_API_KEY=tu_clave_aqui
   ```
4. Guarda y reinicia el bot. ¡Ahora responderá cualquier consulta con IA y datos de internet en vivo!

---

## ☁️ 3. Opciones Gratuitas para Montarlo en la Nube 24/7 (Sin PC)

Si la otra persona no tiene una PC encendida para dejar corriendo el bot, estas son las mejores opciones para alojarlo gratis:

### Opción A: Render.com (Recomendado y muy sencillo)
1. Sube esta carpeta a un repositorio en **GitHub** (privado o público).
2. Crea una cuenta gratis en [render.com](https://render.com/).
3. Haz clic en **New +** > **Web Service**.
4. Conecta tu repositorio de GitHub.
5. Render detectará automáticamente el archivo `Dockerfile`.
6. En **Environment Variables**, añade:
   - `TELEGRAM_BOT_TOKEN`: Tu token de Telegram
   - `GEMINI_API_KEY`: Tu clave de Gemini (opcional pero recomendado)
7. Haz clic en **Deploy Web Service**. ¡Listo! El bot estará activo 24/7 en los servidores de Render.

### Opción B: Koyeb (Gratis con Docker)
1. Crea una cuenta gratis en [koyeb.com](https://www.koyeb.com/).
2. Conecta tu repositorio de GitHub o usa el Dockerfile.
3. El plan gratuito "Nano" mantiene tu bot en ejecución constante sin apagarse.

### Opción C: Railway.app
1. Crea una cuenta en [railway.app](https://railway.app/).
2. Conecta tu repositorio y agrega las variables de entorno. Se desplegará en segundos.

---

## 📱 Comandos del Bot

- `/start`: Bienvenida y menú de opciones.
- `/buscar <tema>`: Búsqueda manual en internet (muestra noticias, enlaces y resúmenes).
- `/limpiar`: Borra la memoria de la conversación para iniciar un tema nuevo.
- `/estado`: Muestra si la IA y el acceso a la red están activos.
- *Cualquier mensaje de texto*: El bot responde como asistente inteligente usando su memoria y la red.
