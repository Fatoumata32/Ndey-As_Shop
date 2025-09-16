#!/bin/bash

echo "==================================="
echo "Setup Ndeyas Shop - Linux/Mac"
echo "==================================="
echo

# Créer l'environnement virtuel
echo "[1/6] Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
echo "[2/6] Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Créer le fichier .env si nécessaire
if [ ! -f .env ]; then
    echo "[3/6] Création du fichier .env..."
    cp .env.example .env
    echo "Fichier .env créé. Veuillez le configurer avec vos paramètres."
else
    echo "[3/6] Fichier .env déjà existant."
fi

# Migrations
echo "[4/6] Application des migrations..."
python manage.py makemigrations
python manage.py migrate

# Collecter les fichiers statiques
echo "[5/6] Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Créer un superutilisateur
echo "[6/6] Création du superutilisateur..."
echo "Veuillez créer un compte administrateur:"
python manage.py createsuperuser

echo
echo "==================================="
echo "Installation terminée!"
echo "==================================="
echo
echo "Pour démarrer le serveur:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo