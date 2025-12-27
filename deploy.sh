#!/bin/bash

# Script de déploiement pour NDEY'AS SHOP
# À exécuter sur le serveur de production

echo '🚀 Début du déploiement...'

# Activer l'environnement virtuel
source /home/FarmConnects/.virtualenvs/env/bin/activate

# Aller dans le répertoire du projet
cd /home/FarmConnects/ndeyeas_shop

# Mettre à jour le code depuis Git (si vous utilisez Git)
# git pull origin main

# Installer les dépendances
echo '📦 Installation des dépendances...'
pip install -r requirements.txt

# Collecter les fichiers statiques
echo '📁 Collecte des fichiers statiques...'
python manage.py collectstatic --noinput

# Appliquer les migrations
echo '🔄 Application des migrations...'
python manage.py migrate

# Créer les dossiers media si nécessaires
echo '📂 Création des dossiers media...'
mkdir -p media/products/images
mkdir -p media/products/videos
mkdir -p media/products/video_thumbnails

# Redémarrer le serveur
echo '♻️ Redémarrage du serveur...'
# Pour uWSGI
sudo systemctl restart uwsgi
# OU
# touch /var/www/ndeyeas_shop_uwsgi.ini

# Pour Nginx
# sudo systemctl restart nginx

echo '✅ Déploiement terminé avec succès!'
