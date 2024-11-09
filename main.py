import telebot
import moviepy.editor as mp
import os
import uuid
import requests

# Инициализация бота
bot = telebot.TeleBot("7794555956:AAHMWRWcEbzPNjjxGdHm3tl6gtMwSv4I_PA")

# Папка для временных файлов
TEMP_FOLDER = 'temp_files'
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# Функция для создания круглого видео с соблюдением требований Telegram
def make_round_video(input_video_path, output_video_path, max_size_mb=1.5, max_duration=60):
    # Загружаем исходное видео с помощью moviepy
    video_clip = mp.VideoFileClip(input_video_path)

    # Ограничиваем длительность видео
    if video_clip.duration > max_duration:
        video_clip = video_clip.subclip(0, max_duration)

    # Проверяем и изменяем разрешение, если оно больше 640x640
    if video_clip.size[0] > 640 or video_clip.size[1] > 640:
        video_clip = video_clip.resize(height=640)

    # Делаем видео квадратным
    width, height = video_clip.size
    min_size = min(width, height)
    video_clip = video_clip.crop(
        x1=(width - min_size) / 2, y1=(height - min_size) / 2,
        x2=(width + min_size) / 2, y2=(height + min_size) / 2
    )

    # Добавляем аудио и проверяем размер временного файла
    audio = video_clip.audio
    video_clip = video_clip.set_audio(audio)
    unique_name = str(uuid.uuid4())
    temp_output_path = os.path.join(TEMP_FOLDER, f"temp_video_{unique_name}.mp4")
    video_clip.write_videofile(temp_output_path, codec="libx264", audio_codec='aac', fps=25, threads=4)

    # Проверяем размер файла и сжимаем, если превышает max_size_mb
    video_size_mb = os.path.getsize(temp_output_path) / (1024 * 1024)  # размер в МБ
    if video_size_mb > max_size_mb:
        bitrate = int((max_size_mb * 1024 * 1024 * 8) / video_size_mb)
        video_clip.write_videofile(output_video_path, codec="libx264", audio_codec='aac', bitrate=f"{bitrate}k", fps=25, threads=4)
    else:
        os.rename(temp_output_path, output_video_path)

    video_clip.close()
    return output_video_path

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет! Отправьте мне видео, и я верну его в виде видеосообщения.")

# Обработчик получения видео от пользователя
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Видео получено. Начинаю обработку...\nЭто займет около 5 секунд.")
    # Скачиваем видео
    video_file = bot.get_file(message.video.file_id)
    video_path = video_file.file_path
    video_url = f"https://api.telegram.org/file/bot{bot.token}/{video_path}"
    video_data = requests.get(video_url)

    # Генерируем уникальное имя для временного файла
    unique_name = str(uuid.uuid4())
    input_video_path = os.path.join(TEMP_FOLDER, f"input_video_{unique_name}.mp4")
    with open(input_video_path, 'wb') as video_file:
        video_file.write(video_data.content)

    # Путь к сохраненному видео
    output_video_path = os.path.join(TEMP_FOLDER, f"round_video_{unique_name}.mp4")

    # Создаем круглый видеофайл с ограничением по размеру и длительности
    output_video_path = make_round_video(input_video_path, output_video_path)

    # Отправляем преобразованное видео как видеосообщение
    with open(output_video_path, 'rb') as video:
        bot.send_video_note(message.chat.id, video)
        bot.send_message(message.chat.id, "Если захотите преобразовать ещё одно видео, то присылайте мне.")

    # Удаляем временные файлы
    os.remove(input_video_path)
    os.remove(output_video_path)

# Запуск бота
bot.polling()
