# Servora - Local Development Startup Guide

## First Time Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

### 2. Activate Virtual Environment

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Every Time You Open The Project

### 1. Activate Virtual Environment

```bash
.venv\Scripts\activate
```

### 2. Start Redis Docker Container

Check container:

```bash
docker ps
```

If Redis is stopped:

```bash
docker start redis-server
```

Verify:

```bash
docker exec -it redis-server redis-cli ping
```

Expected:

```text
PONG
```

### 3. Run Django Migrations

```bash
python manage.py migrate
```

### 4. Start Django Server

```bash
python manage.py runserver
```

or

```bash
python manage.py runserver 0.0.0.0:8000
```

for testing from other devices.

---

## Features Requiring Redis

* Real-time Chat
* Django Channels
* WebSocket Messaging

If Redis is not running:

```text
Chat will not work.
```

---

## Useful Commands

### Check Redis Container

```bash
docker ps
```

### Start Redis

```bash
docker start redis-server
```

### Stop Redis

```bash
docker stop redis-server
```

### Django Server

```bash
python manage.py runserver
```

### Create Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Project Requirements

* Python 3.13
* Django 6.x
* Channels 4.x
* channels_redis 4.x
* redis-py 5.2.1
* Docker Desktop
* Redis Container (redis-server)

---

## Testing Chat

Open:

* Chrome Normal Window (User A)
* Chrome Incognito Window (User B)

Send messages and verify real-time delivery without refresh.
