# Telegram Contest Platform

Python asosidagi Telegram bot + Database loyihasi.

Web App butunlay olib tashlangan. Hozir barcha asosiy oqimlar bot ichida ishlaydi.

## Nimalar bor

- `/start` orqali foydalanuvchini ro'yxatdan o'tkazish
- Majburiy kanallarga obuna tekshiruvi
- Telefon raqamni olish va Telegram ID ga bog'lash
- Profilni bot ichida to'ldirish
- Referral tizimi va har bir to'liq ro'yxatdan o'tgan do'st uchun `+5` ball
- Natijalarda foydalanuvchining o'rni, ochkosi va 1-o'rin
- Shaxsiy kabinet bot ichida
- Ko'p tillilik: o'zbek lotin, o'zbek kirill, rus
- Testlarni admin yaratishi, foydalanuvchi test ID bo'yicha ishlashi
- 3 ta referral shartidan keyin testga kirish
- Bir testga bir martalik urinish
- Testni qo'lda yoki vaqt bo'yicha avtomatik yopish
- Test yopilgach bot orqali to'g'ri/xato javoblarni yuborish
- Tanlov nizomi va kitoblarini admin paneldan boshqarish
- Broadcast va scheduled broadcast
- Foydalanuvchi savol yuborishi va admin javob berishi
- Telegram admin panel: `/admin`

## Stack

- `FastAPI`
- `aiogram 3`
- `SQLAlchemy async`
- `PostgreSQL` (`Railway`)

## Railway deploy

1. Railway'da yangi project oching.
2. Shu repozitoriyani ulang.
3. Railway PostgreSQL service qo'shing.
4. Quyidagi env larni to'ldiring:

```env
BOT_TOKEN=...
BOT_USERNAME=your_bot_username
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_IDS=123456789,987654321
RUN_BOT=1
APP_TIMEZONE=Asia/Samarkand
```

5. Railway service `1 replica` bilan ishlashi tavsiya qilinadi, chunki bot polling bitta instansiyada yurishi kerak.

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
- `DATABASE_URL`: Railway PostgreSQL URL. Kod `postgres://` ni avtomatik `postgresql+asyncpg://` ga aylantiradi
- `ADMIN_IDS`: admin Telegram ID lar
- `RUN_BOT`: `1` bo'lsa polling ishlaydi

## Muhim eslatmalar

- Railway disk doimiy emas. `uploads/` ichidagi media restart yoki redeploydan keyin yo'qolishi mumkin
- production uchun keyinroq `S3`, `Cloudinary` yoki boshqa object storage ulash tavsiya qilinadi
- eski schema bilan yurayotgan bo'lsangiz, deploydan oldin yangi `PostgreSQL` bazaga toza init qilish yaxshiroq
