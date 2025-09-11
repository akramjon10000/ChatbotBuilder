# Render ga Deploy Qilish Qo'llanmasi

Bu qo'llanma AI Chatbot Platformangizni Render.com ga deploy qilish uchun mo'ljallangan.

## Zarur Fayllar

✅ Loyihangizda quyidagi fayllar tayyor:
- `pyproject.toml` - Dependencies va projekt konfiguratsiyasi
- `runtime.txt` - Python versiyasi (python-3.11.13)
- `main.py` - Kirish nuqtasi
- `gunicorn.conf.py` - Gunicorn konfiguratsiyasi

## 1. Render.com ga Ro'yxatdan O'tish

1. [render.com](https://render.com) saytiga o'ting
2. GitHub akkauntingiz bilan kirish yoki yangi akkount yarating
3. Dashboard ga o'ting

## 2. Yangi Web Service Yaratish

1. **"New +"** tugmasini bosing
2. **"Web Service"** ni tanlang
3. GitHub repository ni ulang (yoki kod yuklang)

## 3. Deploy Sozlamalari

### Asosiy Sozlamalar:
- **Name**: `ai-chatbot-platform` (yoki boshqa nom)
- **Environment**: `Python 3`
- **Build Command**: `pip install .`
- **Start Command**: `gunicorn --config gunicorn.conf.py main:app`

### Environment Variables:
Quyidagi environment variables ni qo'shing:

```
DATABASE_URL=postgresql://... (Render PostgreSQL database)
GEMINI_API_KEY=your_gemini_api_key
SESSION_SECRET=your_session_secret
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
FLASK_ENV=production
```

## 4. Database Sozlash

1. **"New +"** -> **"PostgreSQL"** ni tanlang
2. Database nomini kiriting
3. Database yaratilgandan keyin **Internal Database URL** ni nusxalang
4. Web Service da `DATABASE_URL` ga qo'ying

## 5. Deploy

1. Barcha sozlamalar to'g'ri bo'lgandan keyin **"Create Web Service"** bosing
2. Deploy jarayoni 5-10 daqiqa davom etadi
3. Deploy tugagach, sizga URL beriladi

## 6. Domain Sozlash (Ixtiyoriy)

1. Web Service sahifasida **"Settings"** -> **"Custom Domains"**
2. O'z domeningizni qo'shing
3. DNS sozlamalarini o'zgartiring

## 7. SSL/HTTPS

Render avtomatik ravishda SSL sertifikat beradi va HTTPS ni yoqadi.

## 8. Monitoring

1. **"Logs"** bo'limida application loglarini ko'ring
2. **"Metrics"** da performance ko'rsatkichlarini kuzating

## Muhim Eslatmalar

- Render free plan da 750 soat/oy limit bor
- Database backups avtomatik olinadi
- Environment variables xavfsiz saqlanadi
- Auto-scaling mavjud

## Troubleshooting

### Agar deploy muvaffaqiyatsiz bo'lsa:

1. **Build Logs** ni tekshiring
2. `requirements.txt` da version conflicts borligini tekshiring
3. Environment variables to'g'ri o'rnatilganini tasdiqlang
4. Database connection stringini tekshiring

### Keng Tarqalgan Muammolar:

- **Port Error**: Render `PORT` environment variable beradi, gunicorn.conf.py da avtomatik configure qilingan
- **Database Error**: `DATABASE_URL` to'g'ri o'rnatilganini va PostgreSQL driver o'rnatilganini tekshiring
- **Static Files**: CSS/JS fayllar yuklanmasa, `FLASK_ENV=production` o'rnatilganini tekshiring

## Yakunlash

Deploy tugagach, sizning AI Chatbot Platformangiz internet orqali mavjud bo'ladi va foydalanuvchilar mobil qurilmalarida PWA sifatida o'rnatishlari mumkin!

🚀 **Muvaffaqiyatli deploy!**