"""Bot de Telegram (prioridad baja): usa el mismo grafo del asistente con canal = "telegram".

- Si no hay TELEGRAM_TOKEN en el .env, el bot NO arranca y no rompe nada (solo avisa y termina).
- No guarda chat_id, suscripciones ni conversaciones: cada mensaje se atiende solo, sin memoria.
- Las acciones se envían como enlaces (Google Maps sin clave); nada se envía a nadie por el usuario.
- Comandos: /eventos (eventos de hoy), /itinerario (pide compartir la ubicación), /ayuda.

Uso (dentro de Docker):  docker compose --profile telegram up
"""

import sys

import config
import modelo
from api.rutas import ConsultaIn, responder
from db import conectar
from servicios import geo, grafo


def texto_de_respuesta(r: dict) -> str:
    """Respuesta de texto + enlaces para las acciones (en Telegram no se abre la navegación sola)."""
    partes = [r["respuesta"]]
    for accion in r.get("acciones", []):
        if accion["tipo"] == "abrir_navegacion":
            partes.append(f"Mapa: {geo.enlace_mapa(accion['latitud'], accion['longitud'])}")
        elif accion["tipo"] == "compartir":
            partes.append(accion["texto"])
    for fuente in r.get("fuentes", []):
        if fuente.get("url"):
            partes.append(f"Fuente: {fuente['url']}")
    return "\n".join(partes)


def consultar(pregunta: str, latitud=None, longitud=None) -> str:
    conn = conectar()
    try:
        datos = ConsultaIn(pregunta=pregunta[: config.LARGO_MAX_PREGUNTA], canal="telegram", latitud=latitud, longitud=longitud)
        return texto_de_respuesta(responder(conn, datos))
    finally:
        conn.close()


def main() -> int:
    if not config.TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN no está en el .env: el bot de Telegram no se inicia (el resto del sistema sigue igual).")
        return 0
    try:
        from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError:
        print("Falta instalar python-telegram-bot (está en asistente/requirements.txt).")
        return 1

    modelo.cargar()

    async def eventos(update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(consultar("¿Qué hay hoy?"))

    async def ayuda(update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(grafo.AYUDA)

    async def itinerario(update: Update, _: ContextTypes.DEFAULT_TYPE):
        teclado = ReplyKeyboardMarkup(
            [[KeyboardButton("Compartir mi ubicación", request_location=True)]], one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text("Comparte tu ubicación y te armo un recorrido. No la guardo.", reply_markup=teclado)

    async def ubicacion(update: Update, _: ContextTypes.DEFAULT_TYPE):
        loc = update.message.location
        await update.message.reply_text(consultar("Arma un recorrido", loc.latitude, loc.longitude))

    async def texto(update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(consultar(update.message.text or ""))

    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("eventos", eventos))
    app.add_handler(CommandHandler("itinerario", itinerario))
    app.add_handler(CommandHandler(["ayuda", "start"], ayuda))
    app.add_handler(MessageHandler(filters.LOCATION, ubicacion))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto))
    print("Bot de Telegram en marcha (sin guardar chat_id ni conversaciones).")
    app.run_polling()
    return 0


if __name__ == "__main__":
    sys.exit(main())
