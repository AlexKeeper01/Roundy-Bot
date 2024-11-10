import os
import uuid
import requests
import moviepy.editor as mp
from telebot.async_telebot import AsyncTeleBot
from telebot import types

API_TOKEN = "7794555956:AAHMWRWcEbzPNjjxGdHm3tl6gtMwSv4I_PA"
bot = AsyncTeleBot(API_TOKEN)

TEMP_FOLDER = 'temp_files'
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

async def make_round_video(input_video_path, output_video_path, max_size_mb=1.5, max_duration=60):
    video_clip = mp.VideoFileClip(input_video_path)

    if video_clip.duration > max_duration:
        video_clip = video_clip.subclip(0, max_duration)

    current_resolution = video_clip.size[1]
    temp_output_path = os.path.join(TEMP_FOLDER, f"temp_video_{str(uuid.uuid4())}.mp4")


    while True:
        video_duration = video_clip.duration
        target_bitrate = int((max_size_mb * 1024 * 1024 * 8) / video_duration)


        video_clip.write_videofile(temp_output_path, codec="libx264", audio_codec='aac', bitrate=f"{target_bitrate}k",
                                   fps=25, threads=4)

        video_size_mb = os.path.getsize(temp_output_path) / (1024 * 1024)
        if video_size_mb <= max_size_mb:
            break
        elif current_resolution > 320:
            current_resolution -= 100
            video_clip = video_clip.resize(height=current_resolution)
        else:
            break

    width, height = video_clip.size
    min_size = min(width, height)
    video_clip = video_clip.crop(
        x1=(width - min_size) / 2, y1=(height - min_size) / 2,
        x2=(width + min_size) / 2, y2=(height + min_size) / 2
    )

    video_clip.write_videofile(output_video_path, codec="libx264", audio_codec='aac', fps=25, threads=4)
    video_clip.close()
    os.remove(temp_output_path)
    return output_video_path

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await bot.send_message(message.chat.id, "Привет! Отправьте мне видео, и я верну его в виде видеосообщения.")

@bot.message_handler(content_types=['video'])
async def handle_video(message: types.Message):
    await bot.send_message(message.chat.id, "Видео получено. Начинаю обработку...\nЭто займет некоторое время.")

    video_file = await bot.get_file(message.video.file_id)
    video_path = video_file.file_path
    video_url = f"https://api.telegram.org/file/bot{bot.token}/{video_path}"
    video_data = requests.get(video_url)

    unique_name = str(uuid.uuid4())
    input_video_path = os.path.join(TEMP_FOLDER, f"input_video_{unique_name}.mp4")
    with open(input_video_path, 'wb') as video_file:
        video_file.write(video_data.content)

    output_video_path = os.path.join(TEMP_FOLDER, f"round_video_{unique_name}.mp4")
    await bot.send_message(message.chat.id, "Идёт сжатие видео...")
    output_video_path = await make_round_video(input_video_path, output_video_path)
    await bot.send_message(message.chat.id, "Сжатие выполнено. Отправляю результат.")

    with open(output_video_path, 'rb') as video:
        try:
            await bot.send_video_note(message.chat.id, video)
            await bot.send_message(message.chat.id, "Если захотите преобразовать ещё одно видео, то присылайте мне.")
        except Exception:
            await bot.send_message(message.chat.id, "Извините, проблемы с файлом. Отправьте другое видео.")

    os.remove(input_video_path)
    if os.path.exists(output_video_path):
        os.remove(output_video_path)

if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.polling())
