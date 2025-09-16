# 🛍️ Ndeyas Shop - Application E-commerce Django

## 📋 Description
Ndeyas Shop est une application e-commerce complète développée avec Django, offrant une expérience d'achat en ligne fluide et sécurisée.

## ✨ Fonctionnalités Principales

### 👥 Côté Client
- **Authentification** : Inscription, connexion, réinitialisation de mot de passe
- **Catalogue produits** : Navigation par catégories, recherche, filtres
- **Panier d'achat** : Gestion dynamique avec AJAX
- **Commandes** : Processus de checkout sécurisé
- **Contact** : Formulaire de contact

### 🔧 Côté Administration
- **Dashboard** : Vue d'ensemble des statistiques
- **Gestion des produits** : CRUD complet avec images multiples
- **Gestion des catégories** : Organisation des produits
- **Gestion des commandes** : Suivi et traitement
- **Gestion des messages** : Lecture des messages clients

## 🚀 Installation Rapide

### Prérequis
- Python 3.10+
- pip
- virtualenv (optionnel mais recommandé)

### Windows
```bash
# Exécuter le script d'installation
setup.bat
```

### Linux/Mac
```bash
# Rendre le script exécutable
chmod +x setup.sh
# Exécuter le script d'installation
./setup.sh
```

### Installation Manuelle
```bash
# 1. Créer un environnement virtuel
python -m venv venv

# 2. Activer l'environnement virtuel
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Copier et configurer le fichier .env
cp .env.example .env
# Éditer .env avec vos paramètres

# 5. Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# 6. Collecter les fichiers statiques
python manage.py collectstatic

# 7. Créer un superutilisateur
python manage.py createsuperuser

# 8. Lancer le serveur
python manage.py runserver
```

## 🔧 Configuration

### Variables d'environnement (.env)
```env
SECRET_KEY=votre-clé-secrète
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (optionnel)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-app
```

## 📁 Structure du Projet
```
ndeyas_shop/
├── ndeyas_shop/          # Configuration Django
│   ├── settings.py       # Paramètres de base
│   ├── settings_production.py  # Paramètres production
│   ├── urls.py          # URLs principales
│   └── wsgi.py          # Point d'entrée WSGI
├── shop/                # Application principale
│   ├── models.py        # Modèles de données
│   ├── views.py         # Vues et logique
│   ├── forms.py         # Formulaires
│   ├── admin.py         # Interface admin
│   ├── urls.py          # URLs de l'app
│   └── templates/       # Templates HTML
├── static/              # Fichiers statiques
├── media/               # Fichiers uploadés
├── requirements.txt     # Dépendances Python
└── manage.py           # Script de gestion Django
```

## 🔒 Sécurité

### Recommandations pour la Production
1. **Désactiver DEBUG** : `DEBUG=False` dans .env
2. **Clé secrète unique** : Générer une nouvelle SECRET_KEY
3. **HTTPS obligatoire** : Utiliser SSL/TLS
4. **Base de données** : Utiliser PostgreSQL ou MySQL
5. **Serveur** : Utiliser Gunicorn + Nginx
6. **Fichiers statiques** : Servir via CDN ou Nginx

## 🚀 Déploiement

### Avec Gunicorn et Nginx
```bash
# Installer Gunicorn
pip install gunicorn

# Lancer Gunicorn
gunicorn ndeyas_shop.wsgi:application --bind 0.0.0.0:8000

# Configuration Nginx (exemple)
server {
    listen 80;
    server_name votredomaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /chemin/vers/staticfiles/;
    }

    location /media/ {
        alias /chemin/vers/media/;
    }
}
```

## 📊 Modèles de Données

### Principaux Modèles
- **Category** : Catégories de produits avec types et tailles
- **Product** : Produits avec gestion de stock et prix
- **ProductImage** : Images multiples par produit
- **Cart** : Panier d'achat (utilisateurs et sessions)
- **CartItem** : Articles du panier
- **Order** : Commandes avec statuts
- **OrderItem** : Détails des commandes
- **Contact** : Messages de contact
- **Size** : Tailles disponibles

## 🛠️ Commandes Utiles

```bash
# Créer des migrations
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic

# Lancer le serveur de développement
python manage.py runserver

# Lancer le shell Django
python manage.py shell

# Créer une nouvelle app
python manage.py startapp nom_app

# Vérifier le projet
python manage.py check

# Exporter les données
python manage.py dumpdata > data.json

# Importer les données
python manage.py loaddata data.json
```

## 📈 Améliorations Futures

### Court terme
- [ ] Tests unitaires et d'intégration
- [ ] API REST avec Django REST Framework
- [ ] Système de notation et commentaires
- [ ] Wishlist utilisateur
- [ ] Coupons de réduction
- [ ] Factures PDF

### Long terme
- [ ] Application mobile (React Native/Flutter)
- [ ] Recommandations personnalisées (ML)
- [ ] Chat en temps réel
- [ ] Multi-langue (i18n)
- [ ] Multi-devise
- [ ] Tableau de bord analytics avancé

## 🤝 Contribution
Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence
Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support
Pour toute question ou assistance :
- Email : support@ndeyas-shop.com
- Issues : [GitHub Issues](https://github.com/votre-username/ndeyas_shop/issues)

## 🙏 Remerciements
- Django Community
- Bootstrap pour l'UI
- Font Awesome pour les icônes
- Tous les contributeurs

---
Développé avec ❤️ par l'équipe Ndeyas Shop