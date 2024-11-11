import os
import subprocess
import telebot

# Укажите ваш токен Telegram бота
API_TOKEN = '7794555956:AAHMWRWcEbzPNjjxGdHm3tl6gtMwSv4I_PA'

# Путь к ffmpeg
FFMPEG_PATH = r'E:\ffmpeg-7.1-full_build\bin\ffmpeg.exe'  # Замените на свой путь

# Создаем объект бота
bot = telebot.TeleBot(API_TOKEN)

# Максимальные параметры для видео
MAX_SIZE_MB = 1.5  # Максимальный размер видео в мегабайтах
MAX_DURATION = 59  # Максимальная продолжительность видео в секундах

# Путь к папке для временных файлов
TEMP_FILES_DIR = os.path.join(os.path.dirname(__file__), 'temp_files')

# Убедимся, что папка для временных файлов существует
if not os.path.exists(TEMP_FILES_DIR):
    os.makedirs(TEMP_FILES_DIR)


def get_video_duration(input_video_path):
    """Получаем длительность видео с помощью ffmpeg"""
    try:
        # Запускаем ffmpeg для получения метаданных
        result = subprocess.run([FFMPEG_PATH, '-i', input_video_path], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        output = result.stderr.decode()

        # Ищем строку с информацией о длительности
        for line in output.split('\n'):
            if 'Duration' in line:
                # Извлекаем длительность в формате hh:mm:ss.xx
                duration_str = line.split('Duration:')[1].split(',')[0].strip()

                # Преобразуем в часы, минуты и секунды
                hours, minutes, seconds = map(float, duration_str.split(':'))
                return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"Ошибка при получении длительности: {e}")
    return 0


def get_video_size(input_video_path):
    """Получаем размер видео в мегабайтах"""
    return os.path.getsize(input_video_path) / (1024 * 1024)  # Размер в МБ


def compress_video(input_video_path, output_video_path, max_size_mb=MAX_SIZE_MB):
    """Сжимаем видео, если его размер больше max_size_mb"""
    video_size = get_video_size(input_video_path)
    if video_size > max_size_mb:
        print(f"Видео слишком большое: {video_size:.2f} MB. Преобразование...")
        compressed_video_path = output_video_path.replace('.mp4', '_compressed.mp4')
        # Команда для сжатия видео
        subprocess.run([FFMPEG_PATH, '-i', input_video_path, '-vcodec', 'libx264', '-crf', '28', compressed_video_path])
        return compressed_video_path
    return output_video_path


def convert_video(input_video_path, output_video_path):
    """Преобразование видео в формат для видеосообщения в Telegram"""
    # Получаем длительность видео
    video_duration = get_video_duration(input_video_path)
    temp_trimmed_path = input_video_path.replace('.mp4', '_trimmed.mp4')

    if video_duration > MAX_DURATION:
        # Обрезаем видео до MAX_DURATION и сохраняем в временный файл
        subprocess.run(
            [FFMPEG_PATH, '-i', input_video_path, '-t', str(MAX_DURATION), '-c', 'copy', '-y', temp_trimmed_path])
        input_video_path = temp_trimmed_path  # Используем обрезанное видео для дальнейших шагов

    # Преобразуем видео в нужный формат и делаем его квадратным
    # Видео будет квадратным с центровкой
    subprocess.run([FFMPEG_PATH, '-i', input_video_path,
                    '-vf', 'scale=320:320:force_original_aspect_ratio=increase,crop=320:320',
                    '-vcodec', 'libx264', '-acodec', 'aac', '-y', output_video_path])

    # Удаляем временный файл, если он был создан
    if os.path.exists(temp_trimmed_path):
        os.remove(temp_trimmed_path)

    # После преобразования сжимаем видео, если оно слишком большое
    return compress_video(output_video_path, output_video_path)


@bot.message_handler(content_types=['video'])
def handle_video(message):
    try:
        # Получаем информацию о видео
        file_info = bot.get_file(message.video.file_id)
        input_video_path = os.path.join(TEMP_FILES_DIR, f"{file_info.file_id}.mp4")
        print(f"Получено видео, путь: {input_video_path}")

        # Загружаем видео
        downloaded_file = bot.download_file(file_info.file_path)
        with open(input_video_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Создаем уникальное имя для выходного файла
        output_video_path = os.path.join(TEMP_FILES_DIR, f'{file_info.file_id}_output.mp4')

        # Преобразуем видео
        final_video_path = convert_video(input_video_path, output_video_path)

        # Отправляем обработанное видео как видеосообщение
        with open(final_video_path, 'rb') as video:
            bot.send_video_note(message.chat.id, video)

        # Удаляем временные файлы
        os.remove(input_video_path)
        os.remove(final_video_path)

    except Exception as e:
        print(f"Ошибка при обработке видео: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке видео.")


# Запуск бота
print("Бот запущен...")
bot.polling(non_stop=True)
