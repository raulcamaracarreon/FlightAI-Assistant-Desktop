import sys
import os
import base64
from io import BytesIO
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl
from dotenv import load_dotenv
from PIL import Image
from openai import OpenAI

# Cargar las variables de entorno
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("API Key is missing in the .env file")

openai = OpenAI(api_key=openai_api_key)
MODEL = "gpt-4o-mini"

# Datos de ejemplo: precios de boletos
ticket_prices = {
    "london": "$799",
    "paris": "$899",
    "tokyo": "$1400",
    "berlin": "$499"
}

# Mensaje del sistema para el asistente
system_message = (
    "You are a helpful assistant for an Airline called FlightAI. "
    "If the user asks for a ticket price, respond with the price. "
    "If the user mentions a city, generate an image of that city."
)


def get_ticket_price(destination_city):
    """Devuelve el precio del boleto según la ciudad."""
    city = destination_city.lower()
    return ticket_prices.get(city, "Unknown")


def generate_image(city):
    """Genera una imagen para la ciudad usando DALL-E."""
    image_response = openai.images.generate(
        model="dall-e-3",
        prompt=f"A vibrant pop-art style image of {city} with iconic tourist landmarks.",
        size="1024x1024",
        n=1,
        response_format="b64_json",
    )
    image_base64 = image_response.data[0].b64_json
    image_data = base64.b64decode(image_base64)
    return Image.open(BytesIO(image_data))


def generate_audio(message):
    """Genera un archivo de audio a partir de un texto."""
    response = openai.audio.speech.create(
        model="tts-1",
        voice="onyx",
        input=message
    )
    audio_stream = BytesIO(response.content)
    temp_audio_path = os.path.expanduser("~/Documents/temp_audio.mp3")
    with open(temp_audio_path, "wb") as f:
        f.write(audio_stream.read())
    return temp_audio_path


class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("FlightAI Assistant")
        self.resize(800, 600)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        layout = QVBoxLayout(central_widget)

        # Historial del chat
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        # Visualizador de imágenes
        self.image_label = QLabel()
        self.image_label.setFixedSize(256, 256)
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label)

        # Campo de entrada de texto y botones
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send)
        input_layout.addWidget(self.send_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.handle_clear)
        input_layout.addWidget(self.clear_button)

        layout.addLayout(input_layout)

        self.history = []  # Historial de mensajes para el modelo

        # Configuración del reproductor de medios
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

    def handle_send(self):
        """Envía un mensaje al asistente AI."""
        user_message = self.input_field.text().strip()
        if not user_message:
            return

        self.append_message("User", user_message)
        self.input_field.clear()

        # Generar respuesta del AI
        ai_response, image, audio_path = self.chat(user_message)
        self.append_message("FlightAI", ai_response)

        # Mostrar imagen si está disponible
        if image:
            pixmap = QPixmap()
            image.save("temp_image.png")  # Guardar imagen PIL en disco
            pixmap.load("temp_image.png")
            self.image_label.setPixmap(pixmap)

        # Reproducir audio si está disponible
        if audio_path:
            self.play_audio(audio_path)

    def handle_clear(self):
        """Limpia el historial del chat."""
        self.chat_history.clear()
        self.image_label.clear()
        self.history = []

    def append_message(self, sender, message):
        """Agrega un mensaje al historial del chat."""
        self.chat_history.append(f"<b>{sender}:</b> {message}")

    def chat(self, message):
        """Comunicación con el asistente AI."""
        self.history.append({"role": "user", "content": message})
        messages = [{"role": "system", "content": system_message}] + self.history

        # Identificar si se menciona una ciudad para generar precio y/o imagen
        image, audio_path = None, None
        reply = ""
        city_found = False

        for city in ticket_prices.keys():
            if city in message.lower():
                # Generar respuesta personalizada con el precio y generar la imagen
                price = get_ticket_price(city)
                reply = f"The ticket price to {city.capitalize()} is {price}. Would you like to proceed with the booking?"
                image = generate_image(city)
                city_found = True
                break

        if not city_found:
            # Si no se encuentra la ciudad mencionada, respuesta honesta
            reply = "I'm sorry, I don't have information about that city. Please check our website or contact customer service for more details."

        # Generar audio para la respuesta final
        audio_path = generate_audio(reply)

        self.history.append({"role": "assistant", "content": reply})
        return reply, image, audio_path


    def play_audio(self, audio_path):
        """Reproduce el audio usando QMediaPlayer."""
        self.media_player.setSource(QUrl.fromLocalFile(audio_path))
        self.media_player.play()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatApp()
    window.show()
    sys.exit(app.exec())
