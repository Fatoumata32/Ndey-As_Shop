#!/bin/bash
# Script de correctif urgent pour le déploiement
# Exécuter sur le serveur: bash HOTFIX_DEPLOY.sh

echo "════════════════════════════════════════════════"
echo "  HOTFIX - Correction Allauth et Migration"
echo "════════════════════════════════════════════════"
echo ""

# Activation environnement
echo "1️⃣ Activation de l'environnement virtuel..."
source /home/FarmConnects/.virtualenvs/env/bin/activate
cd /home/FarmConnects/ndeyeas_shop

# Mise à jour du code
echo ""
echo "2️⃣ Mise à jour du code depuis Git..."
git pull origin master

# Correction directe du settings.py
echo ""
echo "3️⃣ Correction du fichier settings.py..."
python3 << 'PYTHON_SCRIPT'
import re

settings_path = 'ndeyas_shop/settings.py'

with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer les anciennes configurations allauth
replacements = [
    (r'ACCOUNT_LOGIN_METHODS\s*=\s*\{[^}]+\}', "ACCOUNT_LOGIN_METHODS = {'email', 'username'}"),
    (r'ACCOUNT_SIGNUP_FIELDS\s*=\s*\[[^\]]+\]', "ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']"),
    (r'ACCOUNT_USER_MODEL_USERNAME_FIELD\s*=\s*[^\n]+', "ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'"),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Settings.py corrigé")
PYTHON_SCRIPT

# Vérification
echo ""
echo "4️⃣ Vérification de la configuration..."
python manage.py check

if [ $? -eq 0 ]; then
    echo "✅ Configuration OK"
else
    echo "❌ Erreur de configuration - Vérifiez les logs ci-dessus"
    exit 1
fi

# Application des migrations
echo ""
echo "5️⃣ Application des migrations..."
python manage.py migrate shop

# Redémarrage
echo ""
echo "6️⃣ Redémarrage du serveur..."
touch /var/www/ndeyeas_shop_uwsgi.ini || sudo systemctl restart uwsgi

echo ""
echo "════════════════════════════════════════════════"
echo "  ✅ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"
echo "════════════════════════════════════════════════"
echo ""
echo "Vérifiez le site: https://www.ndeyeas.shop/"
