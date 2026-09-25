# KBDIpt 2026 — Deploy-ready rewrite

KBDIpt is a Django web application for tropical peatland drought monitoring and early warning. This package keeps the useful parts of the original prototype, repairs the broken application flow, separates operator/admin functions from the public mobile-first interface, and exposes an authenticated API for alarm devices.

## What is implemented

### Operator / admin

- `/management/` — operational dashboard.
- `/management/vegetation/` — create peatland sites and run vegetation-image prediction with the bundled ShuffleNetV2 checkpoint.
- `/management/kbdi/` — enter monitoring data and calculate KBDIpt.
- `/management/kbdi/alerts/` — active and historical High/Extreme alerts.
- `/django-admin/` — Django administration.

Only authenticated `is_staff` accounts may access operator pages or create readings/predictions.

### Public user interface

The public interface is mobile-first and follows the supplied industrial-design direction:

- `/` — current location/status, early warning card, large KBDIpt value, quick status reference, other monitored sites.
- `/alerts/` — active and historical High/Extreme warnings.
- `/history/` — recent KBDIpt readings.
- `/info/` — explanation of KBDIpt, status levels, alarms, and vegetation prediction.
- `/locations/<code>/` — location details and recent history.

The four public navigation items are **Home, Peringatan, Riwayat, Informasi**. Browser sound is deliberately user-triggered; it is not the primary physical alarm mechanism.

## KBDIpt classification used by the system

This rewrite uses the tropical-peatland status classes discussed for the Novitasari peatland KBDIpt implementation:

| KBDIpt | Status | EWS alarm |
| ---: | --- | --- |
| `0–200` | Low | No |
| `>200–300` | Moderate | No |
| `>300–350` | High | Yes, level 1 |
| `>350–400` | Extreme | Yes, level 2 |

The thresholds live in one backend function (`kbdis/services.py::classify_kbdi`) and are reused by the stored reading and alert workflow. Do not duplicate thresholds in IoT firmware; read the API `alarm` and `alarm_level` values instead.

## KBDIpt calculation profile

`kbdis/services.py` contains the default `NOVITASARI_2019` peatland profile:

- average annual rainfall (`R0`): `1650 mm`
- `a = 0.3614`
- `b = 0.0905`
- `c = 3.10`
- reference field capacity (`wc`): `400 mm`
- first `5.1 mm` of a continuous rainfall event is ignored before effective rainfall is applied.

The denominator is explicitly implemented as:

```text
1 + 10.88 * exp(-0.001736 * R0)
```

which fixes the operator-precedence problem in the prototype.

### Water table and vegetation

Measured water-table depth is stored with each KBDIpt observation because it is useful monitoring context. It is **not** substituted for the fixed `wc = 400 mm` term in this implementation.

Vegetation prediction is also stored as a separate monitoring feature. The bundled classifier returns `dense`, `medium`, or `bare`, plus confidence and model version. It is **not silently inserted into the KBDIpt equation**, because the selected Novitasari KBDIpt formula profile does not directly use vegetation class as an equation input.

## Early-warning lifecycle

A KBDIpt reading automatically drives the alert state:

```text
Low / Moderate -> no active alarm
High           -> active High alert
Extreme        -> active Extreme alert
Back to Low/Moderate -> active alert is cleared
```

Repeated High readings update the current High alert instead of creating duplicate active alerts. A severity change from High to Extreme closes the old active event and creates one Extreme event. The database enforces at most one active alert per site.

## EWS API

All API routes require authentication. Token authentication is recommended for a physical alarm/IoT client.

### Create a token

```bash
cd backend/kbdiproject
python manage.py drf_create_token <username>
```

The account used for `POST` operations must be staff. A read-only alarm device only needs an authenticated account.

### Read the current EWS status

```http
GET /api/v1/ews/status/1/
Authorization: Token YOUR_TOKEN
```

Example response:

```json
{
  "site": {
    "id": 1,
    "code": "liang-anggang-block-1",
    "name": "Liang Anggang Block 1",
    "location": "Banjarbaru, Kalimantan Selatan"
  },
  "status": {
    "reading_id": 37,
    "observed_at": "2026-09-25T10:42:00+08:00",
    "kbdi": 324.8,
    "level": "high",
    "level_label": "High",
    "alarm": true,
    "alarm_level": 1
  },
  "vegetation": {
    "class": "dense",
    "label": "Tinggi",
    "confidence": 0.9421,
    "predicted_at": "2026-09-24T15:30:00+08:00"
  },
  "active_alert": {}
}
```

A physical device should primarily react to `status.alarm` and `status.alarm_level` rather than recreating the KBDIpt threshold logic.

### List alerts

```http
GET /api/v1/ews/alerts/
GET /api/v1/ews/alerts/?status=cleared
GET /api/v1/ews/alerts/?site=1
Authorization: Token YOUR_TOKEN
```

### Create/list KBDIpt readings

```http
POST /api/v1/kbdi/readings/
Authorization: Token STAFF_TOKEN
Content-Type: application/json
```

```json
{
  "site": 1,
  "rainfall_today_mm": 2.3,
  "rainfall_yesterday_mm": 0,
  "max_temperature_c": 34.2,
  "water_table_depth_mm": 780
}
```

`previous_kbdi_override` is optional and intended for initialisation/correction by an operator. Normally the backend takes the most recent earlier reading automatically.

### Vegetation API

```http
GET  /api/v1/vegetation/sites/
GET  /api/v1/vegetation/predictions/
POST /api/v1/vegetation/predict/
```

The prediction endpoint is multipart form data with `site` and `image`, and requires staff permission. The model is loaded lazily once per application process, image inference is deterministic (`Resize` + `CenterCrop`, no random flip), and upload size is limited to 10 MB.

## Folder layout

```text
kbdipt-2026-deploy-ready/
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
├── nginx/
│   └── kbdipt.conf
├── requirements.txt
├── .env.example
└── backend/kbdiproject/
    ├── manage.py
    ├── kbdiproject/          # project settings, URLs, API routing
    ├── kbdis/                # KBDIpt calculation, readings, EWS alerts
    ├── peatlandcovers/       # sites + vegetation prediction
    ├── peatlandfields/       # legacy compatibility module
    ├── users/                # public UI + operator login
    ├── neuralnetworks/       # ShuffleNetV2 architecture
    ├── model_weights/        # bundled epoch75 checkpoint
    ├── templates/
    │   ├── management/       # operator/admin interface
    │   └── public/           # mobile-first public interface
    └── static/
        ├── css/
        ├── js/
        ├── icons/
        └── manifest.webmanifest
```

## Local development

Recommended: Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
cd backend/kbdiproject
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

With no `DATABASE_URL`, local development uses SQLite. Uploaded files go to `backend/kbdiproject/media/` and static source files stay separate under `static/`.

Open:

- public: `http://127.0.0.1:8000/`
- operator login: `http://127.0.0.1:8000/management/login/`
- Django admin: `http://127.0.0.1:8000/django-admin/`

## Docker deployment

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Change at minimum:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- password inside `DATABASE_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

3. Start the application:

```bash
docker compose up -d --build
```

Nginx listens on port `80`, proxies Django/Gunicorn, and serves uploaded media. WhiteNoise serves versioned static assets from Django. The entrypoint runs migrations and `collectstatic` automatically.

4. Create the first operator account:

```bash
docker compose exec web python manage.py createsuperuser
```

For a public internet deployment, terminate HTTPS/TLS in front of Nginx (or extend the Nginx config with certificates), then enable:

```env
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_SECURE_HSTS_SECONDS=31536000
```

Run the Django deployment check after HTTPS/environment configuration:

```bash
docker compose exec web python manage.py check --deploy
```

## Database compatibility

The original prototype models and their existing migrations are retained as legacy compatibility tables so an existing development database can migrate forward without destructively renaming old tables. New runtime features use `PeatlandSite`, `VegetationPrediction`, `KBDIReading`, and `AlertEvent`.

For a brand-new deployment, simply run `migrate`; all required new tables are created by the included migrations.

## Validation

Automated tests are included for:

- exact peatland threshold boundaries;
- continuous-rain effective rainfall handling;
- High -> Extreme -> cleared alert lifecycle;
- public pages;
- one real inference smoke test against the bundled ShuffleNetV2 checkpoint.

Run:

```bash
cd backend/kbdiproject
python manage.py test
```

## Deployment notes

- The browser sound button is only a usability aid. Browser autoplay restrictions mean it must not be treated as the physical EWS alarm.
- The external alarm should poll/read `/api/v1/ews/status/<site_id>/` with a dedicated token and use the returned `alarm` / `alarm_level` fields.
- Keep the model checkpoint and database backups outside a disposable container layer in any long-lived production workflow.
