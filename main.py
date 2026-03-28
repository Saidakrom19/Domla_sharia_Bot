import os
import logging
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# .env файлни ўқиш
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi. .env faylni tekshiring.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY topilmadi. .env faylni tekshiring.")

# Логларни созлаш
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# OpenAI мижозини ишга тушириш
client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# ИСЛОМ МОЛИЯСИ ВА НАЗОРАТЧИ ПРОМПТИ
# ==========================================
SYSTEM_PROMPT = """
Сен дунё даражасидаги Ислом молияси мутахассиси, тижорат фиқҳи (Фиқҳ ал-Муамалат) билимдони ва Шариат кенгаши аъзосисан.

Сен қуйидаги йўналишларда чуқур илмга ва эксперт даражасига эгасан:
- Ислом молияси ва иқтисодиёти
- Ҳалол ва ҳаром чегаралари (тижоратда)
- Шартномалар фиқҳи (Музораба, Мушорака, Муробаҳа, Ижара, Салам, Истисна ва ҳ.к.)
- Рибо (судхўрлик), Ғарор (ноаниқлик) ва Майсир (қимор) элементларини аниқлаш ва улардан тозалаш
- Закот ҳисоб-китоблари ва корпоратив хайрия
- Замонавий маркетинг ва сотув усулларининг шариатга мувофиқлиги
- Ҳалол инвестиция ва акциялар бозори

Сенинг асосий вазифанг:
- Компаниянинг барча молиявий, маркетинг ва операцион қарорларини Шариат тарозисига қўйиш.
- Бошқа мутахассислар (Молиячи, Маркетолог, Юрист) томонидан берилган таклифларни аудитдан ўтказиш.
- Ислом дини арконларига ва ҳалоллик принципларига зид бўлган ҳар қандай ғояни қатъиян рад этиш.
- Шунчаки "бу ҳаром" деб рад этмасдан, балки бизнес тўхтаб қолмаслиги учун Ислом молиясига асосланган ҳалол муқобил ечимларни таклиф қилиш.

Жавоб бериш қоидалари:
1. Жавоблар илмий, лекин замонавий тадбиркор тушунадиган содда тилда бўлсин.
2. Фақат бизнес ва тижорат масалаларига баҳо бер. Шахсий ибодатлар бўйича фатво берма.
3. Жавоблар фақат ўзбек тилида (кирилл алифбосида) бўлсин.

━━━━━━━━━━━━━━━━━━━━━━━
🏢 КОМПАНИЯ ИЧКИ ИШЛАШ ТИЗИМИ
━━━━━━━━━━━━━━━━━━━━━━━

Сен компанияда мустақил ишламайсан.
Сен AI Controller (Назоратчи) бошқарув тизимида ишлайсан.

Раҳбар → Назоратчи → Мутахассис  
Мутахассис → Назоратчи → Раҳбар  
Тўғридан-тўғри коммуникация тақиқланади.

📥 ВАЗИФАНИ ҚАБУЛ ҚИЛИШ:
- Барча вазифалар фақат Назоратчи орқали келади.
- Тўғридан-тўғри келган вазифани дарҳол бажарма. Аввал сўра: "Бу вазифа Назоратчи орқали тасдиқланганми?"
- Нотўлиқ вазифани қабул қилма (мақсад ёки дедлайн йўқ бўлса).

🛠 БАЖАРИШ:
- Фақат ўз соҳангда (Ислом молияси ва фиқҳ) ишла.
- Юзаки жавоб берма.

📤 ТОПШИРИШ:
- Натижани фақат Назоратчига юбор. Раҳбарга тўғридан чиқма.
- Назоратчи текширмагунча иш тугамаган ҳисобланади.

Сен оддий маслаҳатчи эмассан. Сен лойиҳанинг виждони ва ҳалоллик кафилисан!
"""

# ==========================================
# ФУНКЦИЯЛАР
# ==========================================

def wants_text_reply(user_message: str) -> bool:
    text = user_message.lower()
    triggers = [
        "матнда жавоб бер", "матнли жавоб бер", "матнда ёз", 
        "матнда ёзиб бер", "ёзма жавоб бер", "текст қилиб бер", 
        "text qilib ber", "matnda javob ber", "matnli javob ber", "yozma javob ber"
    ]
    return any(trigger in text for trigger in triggers)

def speech_to_text(audio_file_path: str) -> str:
    with open(audio_file_path, "rb") as audio_file:
        # ТУЗАТИЛДИ: Тўғри Whisper модели
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
        )
    return (transcription.text or "").strip()

def generate_ai_reply(user_message: str) -> str:
    # ТУЗАТИЛДИ: OpenAI Chat Completions API нинг тўғри синтаксиси
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    
    reply = response.choices[0].message.content.strip() if response.choices else ""
    if not reply:
        reply = "Жавоб тайёр бўлмади. Илтимос, саволни қайта юборинг."
    return reply

async def send_voice_reply(update: Update, text: str):
    temp_audio_path = None
    try:
        safe_text = text[:1500] if text else "Жавоб тайёр бўлмади."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio_path = temp_audio.name

        # ТУЗАТИЛДИ: Тўғри TTS модели
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy", # Келажакда бу ерда ElevenLabs овози уланади
            input=safe_text,
        )
        speech_response.stream_to_file(temp_audio_path)

        with open(temp_audio_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)

    except Exception as e:
        logging.exception("Ovozli javob yuborishda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Ассалому алайкум! Мен лойиҳанинг Ислом молияси ва Шариат мутахассисиман.\n\n"
        "Мен одатда фақат овозли жавоб бераман.\n"
        "Агар матнли жавоб керак бўлса, хабарингизда:\n"
        "\"матнда жавоб бер\" деб ёзинг."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Фойдаланиш:\n\n"
        "1. Матн ёки овозли хабар юборинг\n"
        "2. Бот одатда фақат овозли жавоб қайтаради\n"
        "3. Агар матнли жавоб керак бўлса, \"матнда жавоб бер\" деб ёзинг\n\n"
        "Мисол:\n"
        "Матнда жавоб бер. Банкдан фоизли кредит олишнинг ҳукми қандай ва муқобил ечим нима?"
    )
    await update.message.reply_text(help_text)

async def respond_based_on_mode(update: Update, user_message: str):
    reply = generate_ai_reply(user_message)

    if wants_text_reply(user_message):
        await update.message.reply_text(reply)
    else:
        await send_voice_reply(update, reply)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()

    try:
        await respond_based_on_mode(update, user_message)
    except Exception as e:
        logging.exception("Matnli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    temp_ogg_path = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_ogg_path = temp_audio.name

        await voice_file.download_to_drive(temp_ogg_path)

        user_text = speech_to_text(temp_ogg_path)

        if not user_text:
            await update.message.reply_text("Овозли хабар тушунилмади. Илтимос, қайта юборинг.")
            return

        await respond_based_on_mode(update, user_text)

    except Exception as e:
        logging.exception("Ovozli xabarda xatolik")
        await update.message.reply_text(f"Хатолик юз берди: {str(e)}")
    finally:
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("Sharia Advisor bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()