FROM python:3.11-slim

WORKDIR /app

# تنصيب أدوات النظام الأساسية والـ ffmpeg لضمان تشغيل فيديوهات الستوري ومكتبة kvsqlite
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# ⚠️ تنبيه: إذا جان اسم ملف البوت مالتك مو (main.py)، غير الاسم بالسطر الجوه أو سمّي ملفك main.py
CMD ["python", "main.py"]

