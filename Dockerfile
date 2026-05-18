# استخدام نسخة بايثون خفيفة
FROM python:3.10-slim

# هذا السطر هو البديل لحرف -u (يمنع كتم السجلات ويظهرها فوراً في Railway)
ENV PYTHONUNBUFFERED=1

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ ملف المتطلبات وتثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع (مثل main.py)
COPY . .

# أمر تشغيل البوت
CMD ["python", "main.py"]
