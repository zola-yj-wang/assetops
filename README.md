# AssetOps

AssetOps is a Django-based internal asset management platform designed for IT, HR, Office Manager, and Finance teams.

## Features

- Employee management
- Asset inventory tracking
- Asset assignment lifecycle
- Django admin interface
- Automatic asset status updates
- Modular Django apps architecture

## Tech Stack

- Python
- Django
- Django Admin
- SQLite (development)
- Django ORM

## Data Model

Employee → Assignment → Asset

## Setup

```bash
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```