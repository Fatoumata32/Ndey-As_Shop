# Guide de Déploiement - Ndeyas Shop

## 🚨 Déploiement Urgent - Migration Base de Données

**IMPORTANT**: Une migration critique doit être appliquée sur le serveur de production pour supprimer le champ `quantity` des produits.

### Étapes de Déploiement Immédiat

1. **Se connecter au serveur**
   ```bash
   ssh FarmConnects@ndeyeas.shop
   ```

2. **Activer l'environnement virtuel**
   ```bash
   source /home/FarmConnects/.virtualenvs/env/bin/activate
   cd /home/FarmConnects/ndeyeas_shop
   ```

3. **Mettre à jour le code**
   ```bash
   git pull origin master
   ```

4. **Appliquer les migrations**
   ```bash
   python manage.py migrate shop
   ```

5. **Redémarrer le serveur**
   ```bash
   # Option 1: uWSGI avec touch
   touch /var/www/ndeyeas_shop_uwsgi.ini

   # Option 2: Restart systemd service
   sudo systemctl restart uwsgi

   # Si nécessaire, redémarrer Nginx
   sudo systemctl restart nginx
   ```

6. **Vérifier que tout fonctionne**
   - Visitez: https://www.ndeyeas.shop/
   - Testez l'ajout au panier
   - Vérifiez la page admin

### 🔄 Utilisation du Script de Déploiement Automatique

Un script `deploy.sh` a été créé pour automatiser le processus:

```bash
# Sur le serveur
cd /home/FarmConnects/ndeyeas_shop
chmod +x deploy.sh
./deploy.sh
```

---

## Options de Déploiement

### 1. Déploiement sur Railway (Recommandé - Gratuit pour commencer)

#### Étapes de déploiement :

1. **Créer un compte Railway**
   ```
   https://railway.app/
   ```

2. **Installer Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

3. **Initialiser le projet**
   ```bash
   railway login
   railway init
   ```

4. **Ajouter PostgreSQL**
   ```bash
   railway add
   # Choisir PostgreSQL
   ```

5. **Déployer**
   ```bash
   railway up
   ```

### 2. Déploiement sur Render (Gratuit)

#### Étapes :

1. **Créer un fichier `render.yaml`**
   ```yaml
   services:
     - type: web
       name: ndeyas-shop
       env: python
       buildCommand: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
       startCommand: gunicorn ndeyas_shop.wsgi:application
       envVars:
         - key: DJANGO_SECRET_KEY
           generateValue: true
         - key: DEBUG
           value: false
         - key: ALLOWED_HOSTS
           value: .onrender.com

   databases:
     - name: ndeyas-db
       plan: free
   ```

2. **Connecter GitHub et déployer**
   - Aller sur render.com
   - Connecter votre repo GitHub
   - Sélectionner le fichier render.yaml

### 3. Déploiement sur Heroku

#### Fichiers nécessaires :

1. **Créer `Procfile`**
   ```
   web: gunicorn ndeyas_shop.wsgi --log-file -
   ```

2. **Créer `runtime.txt`**
   ```
   python-3.11.9
   ```

3. **Commandes de déploiement**
   ```bash
   # Installer Heroku CLI
   # Créer l'app
   heroku create ndeyas-shop

   # Ajouter PostgreSQL
   heroku addons:create heroku-postgresql:mini

   # Variables d'environnement
   heroku config:set DEBUG=False
   heroku config:set SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

   # Déployer
   git push heroku master

   # Migrer la base
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

### 4. Déploiement sur VPS (DigitalOcean, Linode, etc.)

#### Installation sur Ubuntu 22.04 :

```bash
# 1. Mise à jour système
sudo apt update && sudo apt upgrade -y

# 2. Installer les dépendances
sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl

# 3. Créer la base de données
sudo -u postgres psql
CREATE DATABASE ndeyas_shop;
CREATE USER ndeyas_user WITH PASSWORD 'strong_password';
ALTER ROLE ndeyas_user SET client_encoding TO 'utf8';
ALTER ROLE ndeyas_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ndeyas_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ndeyas_shop TO ndeyas_user;
\q

# 4. Cloner le projet
cd /home
git clone https://github.com/votre-repo/ndeyas_shop.git
cd ndeyas_shop

# 5. Environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Configuration .env
cat > .env << EOF
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DATABASE_URL=postgres://ndeyas_user:strong_password@localhost/ndeyas_shop
EOF

# 7. Collecte des fichiers statiques
python manage.py collectstatic --noinput
python manage.py migrate

# 8. Créer un service systemd
sudo nano /etc/systemd/system/gunicorn.service
```

**Contenu du fichier gunicorn.service :**
```ini
[Unit]
Description=gunicorn daemon for ndeyas_shop
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/ndeyas_shop
ExecStart=/home/ndeyas_shop/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/ndeyas_shop/ndeyas_shop.sock ndeyas_shop.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Configuration Nginx :**
```nginx
server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /home/ndeyas_shop;
    }

    location /media/ {
        root /home/ndeyas_shop;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ndeyas_shop/ndeyas_shop.sock;
    }
}
```

```bash
# Activer et démarrer les services
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo ln -s /etc/nginx/sites-available/ndeyas_shop /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

### 5. Déploiement sur PythonAnywhere (Gratuit pour commencer)

1. **Créer un compte sur PythonAnywhere**
2. **Upload votre code via GitHub**
3. **Dans la console Bash :**
   ```bash
   git clone https://github.com/votre-repo/ndeyas_shop.git
   cd ndeyas_shop
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic
   ```

4. **Configurer l'app web dans le dashboard**
   - Python version: 3.11
   - Source code: /home/username/ndeyas_shop
   - Working directory: /home/username/ndeyas_shop
   - WSGI file: Modifier pour pointer vers ndeyas_shop.wsgi

## Configuration pour la Production

### 1. Variables d'environnement essentielles

Créer un fichier `.env` (ne jamais le commiter!) :

```env
# Django
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com

# Database
DATABASE_URL=postgres://user:password@host:port/dbname

# Email (optionnel)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-app

# Stripe/PayPal (pour les paiements)
STRIPE_PUBLIC_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
```

### 2. Checklist avant déploiement

- [ ] `DEBUG = False` dans settings.py
- [ ] `SECRET_KEY` unique et sécurisée
- [ ] `ALLOWED_HOSTS` configuré correctement
- [ ] Base de données PostgreSQL/MySQL (pas SQLite en production)
- [ ] Fichiers statiques collectés (`python manage.py collectstatic`)
- [ ] HTTPS activé (Let's Encrypt pour certificat gratuit)
- [ ] Sauvegardes automatiques configurées
- [ ] Monitoring mis en place (Sentry, New Relic, etc.)

### 3. Commandes post-déploiement

```bash
# Après chaque déploiement
python manage.py migrate
python manage.py collectstatic --noinput

# Créer un superuser
python manage.py createsuperuser

# Créer un utilisateur staff
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('staff', 'staff@example.com', 'password')
>>> user.is_staff = True
>>> user.save()
```

## Maintenance et Monitoring

### Sauvegardes automatiques

Script de sauvegarde quotidienne :
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/backups"

# Backup database
pg_dump ndeyas_shop > $BACKUP_DIR/db_backup_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /home/ndeyas_shop/media

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -type f -mtime +7 -delete
```

### Monitoring avec Sentry

1. Installer Sentry :
```bash
pip install sentry-sdk
```

2. Configurer dans settings.py :
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn.ingest.sentry.io/xxx",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True
)
```

## Support et Ressources

- Documentation Django : https://docs.djangoproject.com/
- Railway Docs : https://docs.railway.app/
- Render Docs : https://render.com/docs
- Heroku Docs : https://devcenter.heroku.com/
- DigitalOcean Tutorials : https://www.digitalocean.com/community/tutorials

## Contacts

Pour toute question sur le déploiement, contactez l'équipe de développement.