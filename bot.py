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

from config import TELEGRAM_BOT_TOKEN, PORT
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
        pass

def start_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
        logger.info(f"Servidor de salud HTTP iniciado en el puerto {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"No se pudo iniciar el servidor HTTP: {e}")

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
    diag = ai_service.get_diagnostics()
    motor = "xAI Grok" if "Configurada" in diag["grok"] else ("Gemini" if "Configurada" in diag["gemini"] else "Búsqueda Web")

    mensaje = (
        f"👋 ¡Hola, {user_name}! Soy tu asistente personal de Telegram.\n\n"
        f"🧠 *Motor de IA:* {motor}\n\n"
        "✨ *Comandos útiles:*\n"
        "• `/estado` : Ver qué claves de IA están cargadas en Render.\n"
        "• `/limpiar` : Reiniciar la conversación actual.\n"
        "• `/buscar <tema>` : Buscar directamente en internet.\n\n"
        "💬 Escríbeme cualquier pregunta y te responderé de inmediato."
    )
    await safe_reply(update, mensaje, parse_mode=ParseMode.MARKDOWN)

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_reply(update, "ℹ️ Uso: `/buscar noticias inteligencia artificial hoy`")
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
    diag = ai_service.get_diagnostics()
    info = (
        "🤖 *Diagnóstico de Variables en Render:*\n\n"
        f"• *xAI Grok:* {diag['grok']}\n"
        f"• *Google Gemini:* {diag['gemini']}\n"
        f"• *Modelo por defecto:* `{diag['model']}`\n\n"
        "💡 Si alguna aparece como 'No configurada', agrégala en Render > Environment."
    )
    await safe_reply(update, info, parse_mode=ParseMode.MARKDOWN)

# --- MENSAJES NORMALES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prompt = update.message.text
    if not prompt:
        return

    await update.message.reply_chat_action(ChatAction.TYPING)
    respuesta = await ai_service.ask_chatbot(user_id, prompt)
    await send_split_message(update, respuesta)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error en bot2:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ Ocurrió un inconveniente al procesar tu mensaje.")
        except Exception:
            pass

def main():
    print("Iniciando Chatbot de Telegram...")
    threading.Thread(target=start_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("limpiar", cmd_limpiar))
    app.add_handler(CommandHandler("reset", cmd_limpiar))
    app.add_handler(CommandHandler("estado", cmd_estado))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("[OK] Chatbot activo y escuchando mensajes en Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
