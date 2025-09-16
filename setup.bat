@echo off
echo ===================================
echo Setup Ndeyas Shop - Windows
echo ===================================
echo.

:: Créer l'environnement virtuel
echo [1/6] Création de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate

:: Installer les dépendances
echo [2/6] Installation des dépendances...
pip install --upgrade pip
pip install -r requirements.txt

:: Créer le fichier .env si nécessaire
if not exist .env (
    echo [3/6] Création du fichier .env...
    copy .env.example .env
    echo Fichier .env créé. Veuillez le configurer avec vos paramètres.
) else (
    echo [3/6] Fichier .env déjà existant.
)

:: Migrations
echo [4/6] Application des migrations...
python manage.py makemigrations
python manage.py migrate

:: Collecter les fichiers statiques
echo [5/6] Collecte des fichiers statiques...
python manage.py collectstatic --noinput

:: Créer un superutilisateur
echo [6/6] Création du superutilisateur...
echo Veuillez créer un compte administrateur:
python manage.py createsuperuser

echo.
echo ===================================
echo Installation terminée!
echo ===================================
echo.
echo Pour démarrer le serveur:
echo   venv\Scripts\activate
echo   python manage.py runserver
echo.
pause