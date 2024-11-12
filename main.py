import os
import subprocess
import telebot

API_TOKEN = '7794555956:AAHMWRWcEbzPNjjxGdHm3tl6gtMwSv4I_PA'

FFMPEG_PATH = r'E:\ffmpeg-7.1-full_build\bin\ffmpeg.exe'

bot = telebot.TeleBot(API_TOKEN)

MAX_SIZE_MB = 1.5
MAX_DURATION = 59

TEMP_FILES_DIR = os.path.join(os.path.dirname(__file__), 'temp_files')

if not os.path.exists(TEMP_FILES_DIR):
    os.makedirs(TEMP_FILES_DIR)

def get_video_duration(input_video_path):
    try:
        # Запускаем ffmpeg для получения метаданных
        result = subprocess.run([FFMPEG_PATH, '-i', input_video_path], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        output = result.stderr.decode()

        for line in output.split('\n'):
            if 'Duration' in line:
                duration_str = line.split('Duration:')[1].split(',')[0].strip()

                hours, minutes, seconds = map(float, duration_str.split(':'))
                return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"Ошибка при получении длительности: {e}")
    return 0


def get_video_size(input_video_path):
    return os.path.getsize(input_video_path) / (1024 * 1024)

def compress_video(input_video_path, output_video_path, max_size_mb=MAX_SIZE_MB):
    video_size = get_video_size(input_video_path)
    if video_size > max_size_mb:
        print(f"Видео слишком большое: {video_size:.2f} MB. Преобразование...")
        compressed_video_path = output_video_path.replace('.mp4', '_compressed.mp4')
        subprocess.run([FFMPEG_PATH, '-i', input_video_path, '-vcodec', 'libx264', '-crf', '28', compressed_video_path])
        return compressed_video_path
    return output_video_path


def convert_video(input_video_path, output_video_path):
    video_duration = get_video_duration(input_video_path)
    temp_trimmed_path = input_video_path.replace('.mp4', '_trimmed.mp4')

    if video_duration > MAX_DURATION:
        subprocess.run(
            [FFMPEG_PATH, '-i', input_video_path, '-t', str(MAX_DURATION), '-c', 'copy', '-y', temp_trimmed_path])
        input_video_path = temp_trimmed_path  # Используем обрезанное видео для дальнейших шагов

    subprocess.run([FFMPEG_PATH, '-i', input_video_path,
                    '-vf', 'scale=320:320:force_original_aspect_ratio=increase,crop=320:320',
                    '-vcodec', 'libx264', '-acodec', 'aac', '-y', output_video_path])

    if os.path.exists(temp_trimmed_path):
        os.remove(temp_trimmed_path)

    return compress_video(output_video_path, output_video_path)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Отправь мне видео, и я сделаю из него кружочек.")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    try:
        file_info = bot.get_file(message.video.file_id)
        input_video_path = os.path.join(TEMP_FILES_DIR, f"{file_info.file_id}.mp4")
        print(f"Получено видео, путь: {input_video_path}")

        bot.send_message(message.chat.id, "Скачиваю видео...")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(input_video_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        output_video_path = os.path.join(TEMP_FILES_DIR, f'{file_info.file_id}_output.mp4')
        bot.send_message(message.chat.id, "Конвертирую и сжимаю...")
        final_video_path = convert_video(input_video_path, output_video_path)

        bot.send_message(message.chat.id, "Отправляю результат...")
        with open(final_video_path, 'rb') as video:
            bot.send_video_note(message.chat.id, video)
        bot.send_message(message.chat.id, "Отправь мне ещё видео, если захочешь.")

    except Exception as e:
        if 'file is too big' in str(e):
            bot.reply_to(message, "Произошла ошибка при обработке видео. Файл слишком большой.")
        else:
            bot.reply_to(message, "Произошла ошибка при обработке видео.")
        print(f"Ошибка при обработке видео: {e}")

    try:
        os.remove(input_video_path)
        os.remove(output_video_path)
        os.remove(final_video_path)
    except Exception:
        pass

print("Бот запущен...")
bot.polling(non_stop=True)
