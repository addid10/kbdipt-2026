# KBDIpt deployment on Coolify

Use `docker-compose.coolify.yml` for Coolify. It intentionally does not publish host ports; Coolify's proxy should expose only the `nginx` service.

## Required Coolify environment variables

- `POSTGRES_PASSWORD`: a long hex/random password with URL-safe characters.
- `DJANGO_SECRET_KEY`: a long random secret.
- `DJANGO_ALLOWED_HOSTS`: hostname only, for example `kbdipt.example.com`.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: complete HTTPS origin, for example `https://kbdipt.example.com`.
- `DJANGO_DEBUG=false`
- `DJANGO_SECURE_SSL_REDIRECT=true`
- `DJANGO_SESSION_COOKIE_SECURE=true`
- `DJANGO_CSRF_COOKIE_SECURE=true`
- `DJANGO_SECURE_HSTS_SECONDS=0` for the first deployment. Increase only after HTTPS is verified.

## Coolify application settings

- Build Pack: Docker Compose
- Base Directory: `/`
- Docker Compose Location: `/docker-compose.coolify.yml`
- Public service: `nginx`
- Domain for nginx: `https://your-domain.example.com`
- nginx internal port: `80` (there is no need to append `:80`)

The `web` and `db` services must not receive public domains.

## First operator account

After deployment, open the `web` container terminal in Coolify and run:

```bash
python manage.py createsuperuser
```

Migrations and `collectstatic` already run automatically from `docker-entrypoint.sh` each time the web container starts.

## Data persistence

The Compose file owns two named volumes:

- `postgres_data`: PostgreSQL database
- `media_data`: uploaded media / vegetation images

Configure backups in Coolify for persistent data after the first successful deployment.
