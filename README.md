# Eye AI Surveillance System

AI-powered surveillance system: laptop camera → YOLOv8 + facenet-pytorch → Django dashboard → real-time WebSocket streaming.

## Architecture

```
Camera ──→ AI Engine ──→ WebSocket ──→ Django Dashboard
  │              │                         │
  │              ├── Motion Detection      ├── Live Stream
  │              ├── YOLOv8 Tracking       ├── Alerts
  │              ├── Face Recognition      ├── History
  │              ├── Person Tracking       ├── Engine Control
  │              └── DB Save (threaded)    └── Admin Panel
  │
  └── 15 face images + 15 body images per session
```

## Features

| Feature | Details |
|---------|---------|
| YOLOv8 Object Detection | 80-class real-time detection |
| YOLOv8 Tracking (ByteTrack) | Persistent `track_id` across frames |
| Face Recognition | MTCNN + InceptionResnetV1 (facenet-pytorch) |
| 15 Image Capture | 15 face + 15 body images per person |
| Engine Control | Manual start/stop from admin dashboard |
| Engine Loading Page | Professional standalone loading page with countdown |
| Brute Force Protection | 5 failed attempts → 15-minute IP lockout |
| DB Resilience | Graceful handling on network failure |
| Audit Logging | All actions logged to `logs/audit.log` |
| User Management | Create users + password reset + force logout |
| WebSocket Live Stream | Real-time streaming with auto-reconnect |
| Dark UI | Professional dark theme with glassmorphism |
| CSP Security | Content Security Policy via django-csp |

## Project Structure

```
eye_ai/
├── .gitignore
├── LICENSE                     # MIT License
├── README.md
│
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Django + ASGI + Channels + Security + CSP
│   │   ├── asgi.py             # ProtocolTypeRouter (HTTP + WebSocket) + atexit shutdown
│   │   └── urls.py             # Project URLs
│   │
│   ├── surveillance/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py           # Detection + Alert models
│   │   ├── views.py            # All views (15 functions)
│   │   ├── urls.py             # App URL routing (15 patterns)
│   │   ├── forms.py            # CreateUserForm (Django password validation)
│   │   ├── consumers.py        # WebSocket consumer (live_stream group)
│   │   ├── routing.py          # WebSocket URL routing
│   │   ├── context_processors.py  # unread_count (cached, DB-safe)
│   │   ├── stream_queue.py     # Queue for camera→WebSocket (bypasses channel layer)
│   │   │
│   │   ├── ai/
│   │   │   ├── camera.py       # Camera abstraction (laptop / IP camera)
│   │   │   ├── motion.py       # Frame differencing motion detection
│   │   │   ├── detector.py     # YOLOv8 detection + tracking (ByteTrack)
│   │   │   ├── recognizer.py   # MTCNN + InceptionResnetV1 (facenet-pytorch)
│   │   │   ├── engine.py       # AI pipeline (separated stream/detection threads)
│   │   │   └── engine_instance.py  # Thread-safe engine singleton + booting state
│   │   │
│   │   ├── management/
│   │   │   ├── __init__.py
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       ├── runai.py         # Start AIEngine from terminal
│   │   │       └── cleanup_old_data.py  # Delete data older than 48h
│   │   │
│   │   └── migrations/
│   │       └── ...
│   │
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── views.py            # login_view (brute force protection)
│   │   ├── forms.py            # EyeAIAuthenticationForm
│   │   └── urls.py             # Login / Logout
│   │
│   ├── templates/
│   │   ├── base.html           # Sidebar + engine control
│   │   ├── accounts/
│   │   │   └── login.html
│   │   └── surveillance/
│   │       ├── dashboard.html      # Stats + engine control + live stream + alerts
│   │       ├── engine_loading.html # Standalone loading page (no base.html)
│   │       ├── live.html           # Full-screen live stream
│   │       ├── history.html        # Detection table + filter + image modal
│   │       ├── alerts.html         # Alert list + mark read + mark all read
│   │       └── manage_users.html   # User CRUD + password reset
│   │
│   ├── static/surveillance/
│   │   ├── js/live-stream.js       # WebSocket client (exponential backoff)
│   │   ├── style.css               # Dark theme + glassmorphism + animations
│   │   └── engine_loading.css      # Loading page styles (CSP-compliant)
│   │
│   ├── .env                    # Environment variables (not uploaded)
│   ├── .env.example            # Environment variable template
│   ├── manage.py
│   └── requirements.txt
│
└── venv/                       # Python 3.12 virtual environment (not uploaded)
```

## Pages

### Dashboard (`/`)
- **Engine Control**: Start/stop camera button (staff only)
- **Live Stream**: Real-time WebSocket stream
- **Stats Grid**: Person count today + last detection + stream status + unread alerts
- **Recent Alerts**: Last 5 alerts

### Engine Loading (`/engine/loading/`)
- **Standalone Page**: Does not extend base.html — no CSP or CSS conflicts
- **Professional Design**: Dual-ring spinner, Arabic countdown, glassmorphism card
- **Auto-Redirect**: Redirects to live stream (`/live/`) after 10 seconds
- **Dual Fallback**: Both `<meta http-equiv="refresh">` and JavaScript redirect

### Live Stream (`/live/`)
- **Full-width Stream**: Complete stream via WebSocket
- **Status Badge**: Connection status (connected/disconnected)
- **Overlay**: Person count + stream time

### History (`/history/`)
- **Detection Table**: Detection log with images
- **Class Filter**: Filter by detection class
- **Image Modal**: Full-size image preview
- **Delete All**: Delete all records (staff only, with confirmation)
- **Pagination**: 25 per page

### Alerts (`/alerts/`)
- **Alert List**: Alert log with images
- **Mark Read**: Mark single alert as read
- **Mark All Read**: Mark all as read
- **Auto-refresh**: Updates every 30 seconds
- **Image Modal**: Full-size image preview
- **Pagination**: 50 per page

### Manage Users (`/manage-users/`) — Staff only
- **Create User**: Create new user account
- **Reset Password**: Reset user password
- **Force Logout**: Force logout any user
- **Delete User**: Delete user account
- **User Cards**: User cards with colored role badges

### Login (`/accounts/login/`)
- **Brute Force Protection**: IP locked after 5 failed attempts for 15 minutes
- **Error Messages**: Clear Arabic error messages
- **Eye AI Logo**: System branding

## Security

| Feature | Implementation |
|---------|---------------|
| Brute Force Protection | Cache-based (5 attempts → 15 minutes lockout) |
| CSRF Protection | Django CSRF middleware on all POST forms |
| Session Timeout | 1 hour (3600s), expires on browser close |
| Password Validation | Django built-in validators (similarity, length, common, numeric) |
| Audit Logging | All sensitive actions logged to `logs/audit.log` |
| CSP Headers | Content Security Policy via django-csp |
| Staff-only Controls | Engine control, user management restricted to `is_staff` |
| HTTP Security | HSTS, SSL redirect, X-Frame-Options DENY (production) |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Backend | Django 6.0.6 + ASGI |
| ASGI Server | Uvicorn 0.51.0 |
| Real-time | Django Channels 4.3.2 + WebSockets |
| AI Models | YOLOv8 (ultralytics 8.4.86) + facenet-pytorch 2.0.1 |
| Face Detection | MTCNN (min_face_size=40, confidence>0.9) |
| Face Recognition | InceptionResnetV1 (vggface2 pretrained) |
| Object Tracking | ByteTrack (YOLOv8 `model.track(persist=True)`) |
| Database | PostgreSQL 18 (local) |
| Cache | Django LocMemCache |
| Channel Layer | Redis 5.0.9 (production) / InMemoryChannelLayer (dev) |
| Frontend | Bootstrap 5.3.3 + Font Awesome 6.5.1 + Custom CSS |
| WebSocket | `ws://host/ws/stream/` with exponential backoff |
| CSP | django-csp 4.0 |

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 18+ (local)
- Redis (optional, for channel layer)

### 2. Setup

```powershell
# Create virtual environment
cd eye_ai
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Copy .env.example to .env and configure
copy .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 3. Channel Layer

The project requires a channel layer for WebSocket support. Choose one:

| Option | Configuration | Requirements |
|--------|--------------|--------------|
| **InMemory** (default) | `CHANNEL_BACKEND=memory` | Nothing extra — works immediately |
| **Redis** | `CHANNEL_BACKEND=redis` | Running Redis instance (port 6379) |

### 4. Run

```powershell
cd backend
python -m uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

1. Open http://127.0.0.1:8000/
2. Login with superuser account
3. Go to Dashboard → press "Start Camera"
4. Loading page appears with 10-second countdown
5. Auto-redirects to live stream page

> **Note**: The engine loads models in a background thread (~10-15s). The loading page (`/engine/loading/`) provides a professional transition with a countdown and auto-redirect.

### Stopping the Server

Press `Ctrl+C` in the terminal. The engine is automatically stopped via `atexit` handler.

## Data Flow

```
Camera.read() [Thread 1: stream loop]
    ↓ every 6th frame (frame_skip=5)
MotionDetector.detect() → motion detected
    ↓
ObjectDetector.detect() → [person track_id=3 0.92] (ByteTrack)
    ↓
FaceRecognizer.recognize() → [face embedding + person_hash]
    ↓
_create_detection() + _create_alert() ← DB (via background thread)
    ↓
WebSocket stream_message() ← Channel Layer (real-time)

Camera.read() → JPEG encode → frame_queue.put() [Thread 1: stream only]
    ↓
LiveStreamConsumer._stream_reader() → WebSocket → Browser
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `django-insecure-change-me-in-production` | Django secret key |
| `DEBUG` | Yes | `False` | Debug mode |
| `CHANNEL_BACKEND` | No | `memory` | Channel layer: `memory` (InMemory) or `redis` (requires Redis) |
| `REDIS_HOST` | When `CHANNEL_BACKEND=redis` | `127.0.0.1` | Redis host |
| `REDIS_PORT` | When `CHANNEL_BACKEND=redis` | `6379` | Redis port |
| `DB_NAME` | Yes | — | PostgreSQL database name |
| `DB_USER` | Yes | — | PostgreSQL user |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_HOST` | Yes | — | PostgreSQL host (`127.0.0.1` for local) |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `ALLOWED_HOSTS` | Yes | `127.0.0.1,localhost` | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Yes | `http://127.0.0.1:8000,http://localhost:8000` | Comma-separated origins |
| `CORS_ALLOWED_ORIGINS` | Yes | `http://127.0.0.1:8000,http://localhost:8000` | Comma-separated origins |

## Database Resilience

The system is protected against network failures:

| Layer | Protection |
|-------|-----------|
| `settings.py` | `connect_timeout=10` + `CONN_MAX_AGE=600` |
| `context_processors.py` | try/except — no page crashes |
| `engine.py` | try/except around every DB operation |

```
Internet goes down →
  ✅ Pages still load
  ✅ Engine keeps running (buffers in memory)
  ✅ When connection returns → resumes saving to DB
```

## Management Commands

```powershell
# Start AI Engine
python manage.py runai

# Cleanup old data (older than 48h)
python manage.py cleanup_old_data
```

## License

MIT License — see [LICENSE](LICENSE) for details.
