from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os
import requests
from telegram import ReplyKeyboardMarkup, KeyboardButton

TOKEN = '6929996860:AAG-bZmjNyKvp5aR2byVoywoA5b1V_AwS3E'

# API Gateway endpoint URL
API_URL = 'https://rp81vamf4m.execute-api.us-east-1.amazonaws.com/Test'

def start(update, context):
    languages = {
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Japanese': 'ja',
}


    keyboard = [[KeyboardButton(lang) for lang in languages.keys()]]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    context.bot.send_message(chat_id=update.effective_chat.id,text="Please select the language code:",reply_markup=reply_markup)
    context.user_data['language_code'] = None

def language_selection(update, context):
    # Get selected language from user input
    selected_language = update.message.text
    languages = {
        'English': 'en',
        'Spanish': 'es',
        'French': 'fr',
        'German': 'de',
        'Japanese': 'ja'
    }

    # Get language code corresponding to selected language
    language_code = languages.get(selected_language)

    if language_code:
        # Store selected language code in user_data
        context.user_data['language_code'] = language_code
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Language code set to {language_code}.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid language selection.")

# Add language_selection handler

def handle_audio(update, context):
    if update.message.audio:
        print(update.message.audio)
        try:
            file_id = update.message.audio.file_id
            file_path = context.bot.get_file(file_id).file_path
            bucket="skill-8-bucket-31166"
            audio_url = file_path
            language_code = context.user_data.get('language_code', 'en')  # Default to English if no language is selected
            filename = f"{update.effective_chat.id}---{language_code}---{os.path.basename(audio_url)}"  # Include language code in filename
            print(filename)
            audio_file = requests.get(audio_url)
            audio_file.raise_for_status()
            url = f"{API_URL}/{bucket}/{filename}"
            headers = {'Content-Type': 'audio/mpeg'}  # Adjust content type if needed
            print(url)
            print(url)

            try:
                response = requests.put(url, data=audio_file.content, headers=headers)
                print(response)

                response.raise_for_status()

                context.bot.send_message(chat_id=update.effective_chat.id, text='Audio uploaded successfully!\n Please wait while we process it...')
            except requests.exceptions.RequestException as e:

                context.bot.send_message(chat_id=update.effective_chat.id, text=f'An error occurred while uploading the audio: {e}')

        except Exception as e:

            context.bot.send_message(chat_id=update.effective_chat.id, text=f'An unexpected error occurred: {e}')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please send an audio file.')

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.audio, handle_audio))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, language_selection))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
