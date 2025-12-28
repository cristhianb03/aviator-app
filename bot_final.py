import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# 1. Configuración básica de logs para ver errores en consola
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manda el mensaje inicial con el botón de la App Móvil"""
    
    # URL de tu Paso 2 (Donde subiste tu index.html, ej: GitHub Pages)
    URL_MÓVIL = "https://cristhianb03.github.io/aviator-app-1.1/" 
    
    # Creamos el botón especial de WebApp
    boton_app = InlineKeyboardButton(
        text="🚀 ABRIR PANEL EN VIVO", 
        web_app=WebAppInfo(url=URL_MÓVIL)
    )
    
    # Lo ponemos en un teclado (puedes añadir más botones si quieres)
    keyboard = InlineKeyboardMarkup([[boton_app]])
    
    await update.message.reply_text(
        "¡Bienvenido al Analizador Aviator Pro! 🦅\n\n"
        "Presiona el botón de abajo para ver las gráficas y señales en tiempo real desde tu celular.",
        reply_markup=keyboard
    )

if __name__ == '__main__':
    # Reemplaza con tu Token real de BotFather
    TOKEN = 'TU_TOKEN_AQUÍ'
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Registramos el comando /start
    app.add_handler(CommandHandler('start', start))
    
    print("Bot encendido... Ve a Telegram y dale a /start")
    app.run_polling()