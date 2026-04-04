# Telegram Contest Platform

Python asosidagi Telegram bot + Web App + Database loyihasi.

Railway deploy uchun tayyorlangan variant.

## Nimalar bor

- `/start` orqali foydalanuvchini ro'yxatdan o'tkazish
- Majburiy kanallarga obuna tekshiruvi
- Telefon raqamni olish va Telegram ID ga bog'lash
- Web App orqali profil to'ldirish
- Referral tizimi va har bir to'liq ro'yxatdan o'tgan do'st uchun `+5` ball
- Top 50 reyting va foydalanuvchining shaxsiy o'rni
- Shaxsiy kabinet: profil, referral, jami ball va testlar tarixi
- Ko'p tillilik: o'zbek lotin, o'zbek kirill, rus
- Testlarni admin yaratishi, foydalanuvchi test ID bo'yicha ishlashi
- 3 ta referral shartidan keyin testga kirish
- Bir testga bir martalik urinish
- Testni qo'lda yoki vaqt bo'yicha avtomatik yopish
- Test natijalarini saqlash
- Test yopilgach bot orqali to'g'ri/xato javoblarni yuborish
- Tanlov nizomi va kitoblarini admin paneldan boshqarish
- Broadcast
- Scheduled broadcast
- Foydalanuvchi savol yuborishi va admin javob berishi
- Telegram admin panel: `/admin` buyrug'i orqali

## Stack

- `FastAPI`
- `aiogram 3`
- `SQLAlchemy async`
- `Jinja2`
- `PostgreSQL` (`Railway`) 

## Railway deploy

1. Railway'da yangi project oching.
2. Shu repozitoriyani ulang.
3. Railway PostgreSQL service qo'shing.
4. Quyidagi env larni to'ldiring:

```env
BOT_TOKEN=...
BOT_USERNAME=your_bot_username
WEB_APP_BASE_URL=https://your-app.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=long-random-secret
ADMIN_IDS=123456789,987654321
RUN_BOT=1
APP_TIMEZONE=Asia/Samarkand
```

5. Telegram bot settings ichida Web App uchun shu Railway domen ishlatiladi.
6. Railway service `1 replica` bilan ishlashi tavsiya qilinadi, chunki bot polling bitta instansiyada yurishi kerak.

`railway.json` va `Procfile` qo'shilgan. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Lokal ishga tushirish

1. Virtual environment yarating:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Kutubxonalarni o'rnating:

```bash
pip install -r requirements.txt
```

3. `.env.example` dan `.env` yarating va qiymatlarni to'ldiring.

4. Serverni ishga tushiring:

```bash
uvicorn app.main:app --reload
```

## Muhim sozlamalar

- `BOT_TOKEN`: Telegram bot token
- `BOT_USERNAME`: referral link uchun bot username
- `WEB_APP_BASE_URL`: Railway bergan `https://...` domen
- `DATABASE_URL`: Railway PostgreSQL URL. Kod `postgres://` ni avtomatik `postgresql+asyncpg://` ga aylantiradi
- `ADMIN_IDS`: adminga savol yuborish va javob berish uchun Telegram ID lar
- `SECRET_KEY`: token imzolash uchun maxfiy kalit

## Muhim eslatmalar

- Telegram `Web App` uchun `localhost` emas, public `HTTPS` URL kerak
- Railway disk doimiy emas. `uploads/` ichidagi media restart yoki redeploydan keyin yo'qolishi mumkin
- production uchun keyinroq `S3`, `Cloudinary` yoki boshqa object storage ulash tavsiya qilinadi
- eski `SQLite` yoki eski schema bilan yurayotgan bo'lsangiz, deploydan oldin yangi `PostgreSQL` bazaga toza init qilish yaxshiroq

## Qo'shish mumkin bo'lgan yaxshilanishlar

- Alembic migratsiya
- Redis FSM storage
- CSV/Excel export
- Admin statistikasi
- Test vaqt limiti
- Broadcast uchun media qo'llab-quvvatlash
