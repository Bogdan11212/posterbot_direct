import os
from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
    Bot,
    ParseMode,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler
)

# Конфигурация
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = '@your_channel_username'  # Замените на username вашего канала

# Состояния
TITLE, CONTENT, MEDIA, CONFIRM = range(4)

# Временное хранилище данных
user_posts = {}

def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_posts[user_id] = {
        'title': None,
        'content': None,
        'media': [],
        'media_type': None
    }
    
    update.message.reply_text(
        "📝 Давайте создадим крутой пост!\n"
        "Введите заголовок поста:"
    )
    return TITLE

def title_received(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_posts[user_id]['title'] = update.message.text
    
    update.message.reply_text(
        "Отлично! Теперь введите основной текст поста:\n"
        "Поддерживается Markdown-разметка (*жирный*, _курсив_, [ссылка](https://example.com))"
    )
    return CONTENT

def content_received(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_posts[user_id]['content'] = update.message.text_markdown_v2
    
    keyboard = [
        [InlineKeyboardButton("Пропустить", callback_data='skip_media')],
        [InlineKeyboardButton("Отменить", callback_data='cancel')]
    ]
    
    update.message.reply_text(
        "📷 Пришлите медиа-файлы (фото/видео) или нажмите 'Пропустить'",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MEDIA

def media_received(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    post = user_posts[user_id]
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        post['media_type'] = 'photo'
    elif update.message.video:
        file_id = update.message.video.file_id
        post['media_type'] = 'video'
    else:
        update.message.reply_text("Пожалуйста, отправьте фото или видео")
        return MEDIA
    
    post['media'].append(file_id)
    
    if len(post['media']) < 10:  # Лимит медиа-файлов
        update.message.reply_text(
            "Медиа добавлено! Можно отправить еще или нажать 'Подтвердить'",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Подтвердить", callback_data='confirm_media')],
                [InlineKeyboardButton("Отменить", callback_data='cancel')]
            ])
        )
    else:
        update.message.reply_text("Достигнут лимит медиа-файлов (10)")
        return confirm_media(update, context)
    
    return MEDIA

def confirm_media(update: Update, context: CallbackContext) -> int:
    return show_preview(update, context)

def skip_media(update: Update, context: CallbackContext) -> int:
    return show_preview(update, context)

def show_preview(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    post = user_posts[user_id]
    
    preview_text = (
        f"*{post['title']}*\n\n"
        f"{post['content']}\n\n"
        f"Медиа-файлов: {len(post['media'])}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Опубликовать", callback_data='publish')],
        [InlineKeyboardButton("✏️ Редактировать", callback_data='edit')],
        [InlineKeyboardButton("❌ Отменить", callback_data='cancel')]
    ]
    
    if post['media']:
        media = []
        for i, file_id in enumerate(post['media']):
            if post['media_type'] == 'photo':
                media.append(InputMediaPhoto(file_id, caption=preview_text if i == 0 else None))
            else:
                media.append(InputMediaVideo(file_id, caption=preview_text if i == 0 else None))
        
        context.bot.send_media_group(
            chat_id=update.effective_chat.id,
            media=media
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=preview_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    update.callback_query.message.reply_text(
        "Предпросмотр поста:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CONFIRM

def publish_post(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    post = user_posts[user_id]
    
    try:
        if post['media']:
            media = []
            for i, file_id in enumerate(post['media']):
                caption = f"*{post['title']}*\n\n{post['content']}" if i == 0 else None
                if post['media_type'] == 'photo':
                    media.append(InputMediaPhoto(file_id, caption=caption, parse_mode=ParseMode.MARKDOWN_V2))
                else:
                    media.append(InputMediaVideo(file_id, caption=caption, parse_mode=ParseMode.MARKDOWN_V2))
            
            context.bot.send_media_group(
                chat_id=CHANNEL_ID,
                media=media
            )
        else:
            context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"*{post['title']}*\n\n{post['content']}",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        
        update.callback_query.answer("✅ Пост успешно опубликован!")
    except Exception as e:
        update.callback_query.answer(f"❌ Ошибка: {str(e)}")
    
    del user_posts[user_id]
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    if user_id in user_posts:
        del user_posts[user_id]
    
    update.callback_query.answer("❌ Создание поста отменено")
    return ConversationHandler.END

def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TITLE: [MessageHandler(Filters.text & ~Filters.command, title_received)],
            CONTENT: [MessageHandler(Filters.text & ~Filters.command, content_received)],
            MEDIA: [
                CallbackQueryHandler(skip_media, pattern='^skip_media$'),
                CallbackQueryHandler(confirm_media, pattern='^confirm_media$'),
                MessageHandler(Filters.photo | Filters.video, media_received)
            ],
            CONFIRM: [
                CallbackQueryHandler(publish_post, pattern='^publish$'),
                CallbackQueryHandler(start, pattern='^edit$'),
                CallbackQueryHandler(cancel, pattern='^cancel$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(cancel, pattern='^cancel$'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
