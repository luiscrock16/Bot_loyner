import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, DEFAULT_MODEL, PORT
import ai_service
import search_service

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- MINI SERVIDOR HTTP PARA CLOUD HOSTING (RENDER / KOYEB) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot de Telegram activo y en ejecucion.")

    def log_message(self, format, *args):
        pass  # Silenciar logs http para mantener limpia la consola

def start_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
        logger.info(f"Servidor de salud HTTP iniciado en el puerto {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"No se pudo iniciar el servidor HTTP (normal si el puerto esta ocupado): {e}")

# --- UTILIDADES DE MENSAJERÍA ---
async def safe_reply(update: Update, text: str, parse_mode: str = None):
    try:
        return await update.message.reply_text(text, parse_mode=parse_mode)
    except Exception:
        return await update.message.reply_text(text, parse_mode=None)

async def send_split_message(update: Update, text: str):
    max_len = 4000
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        await safe_reply(update, chunk)

# --- COMANDOS ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "amigo"
    ai_status = "✅ Gemini IA + Búsqueda Web" if GEMINI_API_KEY else "🌐 Búsqueda Web (Modo Básico)"

    mensaje = (
        f"👋 ¡Hola, {user_name}! Soy tu asistente personal de Telegram.\n\n"
        "Puedo responder preguntas, buscar información actualizada en internet, resumir artículos y ayudarte en lo que necesites.\n\n"
        f"⚙️ *Estado:* {ai_status}\n\n"
        "✨ *Comandos útiles:*\n"
        "• `/buscar <tema>` : Realiza una búsqueda directa en internet.\n"
        "• `/limpiar` : Reinicia nuestra conversación y olvida los mensajes anteriores.\n"
        "• `/estado` : Muestra información de conexión del bot.\n\n"
        "💬 O simplemente *escríbeme lo que quieras saber* y te responderé de inmediato."
    )
    await safe_reply(update, mensaje, parse_mode=ParseMode.MARKDOWN)

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_reply(update, "ℹ️ Uso: `/buscar noticias inteligencia artificial hoy`", parse_mode=ParseMode.MARKDOWN)
        return

    query = " ".join(context.args)
    await update.message.reply_chat_action(ChatAction.TYPING)

    results = await asyncio.to_thread(search_service.search_web, query, 4)
    summary = search_service.format_search_summary(query, results)
    await send_split_message(update, summary)

async def cmd_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ai_service.clear_history(user_id)
    await safe_reply(update, "🧹 Memoria de conversación reiniciada. ¿De qué te gustaría hablar ahora?")

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tiene_ia = "Activada (Google Gemini)" if GEMINI_API_KEY else "Desactivada (Usa .env para configurarla)"
    info = (
        "🤖 *Estado del Bot:*\n\n"
        f"• *Inteligencia Artificial:* {tiene_ia}\n"
        f"• *Modelo:* `{DEFAULT_MODEL}`\n"
        "• *Acceso a la Red:* ✅ Búsqueda web activa\n"
        "• *Alojamiento:* Listo para PC o Nube (Render, Railway, Koyeb)"
    )
    await safe_reply(update, info, parse_mode=ParseMode.MARKDOWN)

# --- MANEJADOR DE MENSAJES NORMALES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prompt = update.message.text

    if not prompt:
        return

    # Indicar que el bot está escribiendo
    await update.message.reply_chat_action(ChatAction.TYPING)

    # Consultar IA / Búsqueda web
    respuesta = await ai_service.ask_chatbot(user_id, prompt)
    await send_split_message(update, respuesta)

# --- MANEJADOR DE ERRORES ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error en bot2:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ Ocurrió un inconveniente al procesar tu mensaje. Intenta de nuevo.")
        except Exception:
            pass

def main():
    print("Iniciando Chatbot de Telegram para la nube/local...")

    # Iniciar servidor HTTP en segundo plano para health checks en la nube
    threading.Thread(target=start_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("limpiar", cmd_limpiar))
    app.add_handler(CommandHandler("reset", cmd_limpiar))
    app.add_handler(CommandHandler("estado", cmd_estado))

    # Texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Manejador de errores
    app.add_error_handler(error_handler)

    print("[OK] Chatbot activo y escuchando mensajes en Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
