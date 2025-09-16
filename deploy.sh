#!/bin/bash

# Script de déploiement automatisé pour Ndeyas Shop
# Usage: ./deploy.sh [platform]
# Platforms: railway, render, heroku, vps

PLATFORM=${1:-railway}

echo "🚀 Déploiement de Ndeyas Shop sur $PLATFORM..."

# Vérifications préliminaires
check_requirements() {
    echo "📋 Vérification des prérequis..."

    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 n'est pas installé"
        exit 1
    fi

    # Vérifier Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git n'est pas installé"
        exit 1
    fi

    # Vérifier le fichier .env
    if [ ! -f .env ]; then
        echo "⚠️  Fichier .env non trouvé. Création à partir du template..."
        cp .env.production .env
        echo "📝 Veuillez configurer le fichier .env avant de continuer"
        exit 1
    fi

    echo "✅ Tous les prérequis sont satisfaits"
}

# Préparation pour production
prepare_production() {
    echo "🔧 Préparation pour la production..."

    # Installer les dépendances
    pip install -r requirements.txt

    # Collecter les fichiers statiques
    python manage.py collectstatic --noinput

    # Effectuer les migrations
    python manage.py migrate

    echo "✅ Application prête pour la production"
}

# Déploiement sur Railway
deploy_railway() {
    echo "🚂 Déploiement sur Railway..."

    if ! command -v railway &> /dev/null; then
        echo "Installation de Railway CLI..."
        npm install -g @railway/cli
    fi

    railway login
    railway init
    railway add postgresql
    railway up

    echo "✅ Déployé sur Railway!"
    echo "URL: $(railway open)"
}

# Déploiement sur Render
deploy_render() {
    echo "🎨 Déploiement sur Render..."

    # Vérifier que render.yaml existe
    if [ ! -f render.yaml ]; then
        echo "❌ render.yaml non trouvé"
        exit 1
    fi

    # Initialiser Git si nécessaire
    if [ ! -d .git ]; then
        git init
        git add .
        git commit -m "Initial commit for Render deployment"
    fi

    echo "📝 Instructions pour Render:"
    echo "1. Allez sur https://render.com"
    echo "2. Connectez votre repository GitHub"
    echo "3. Sélectionnez 'New Web Service'"
    echo "4. Choisissez ce repository"
    echo "5. Render détectera automatiquement render.yaml"

    read -p "Appuyez sur Entrée une fois configuré sur Render..."

    echo "✅ Configuration Render terminée!"
}

# Déploiement sur Heroku
deploy_heroku() {
    echo "🟣 Déploiement sur Heroku..."

    if ! command -v heroku &> /dev/null; then
        echo "❌ Heroku CLI n'est pas installé"
        echo "Installez-le depuis: https://devcenter.heroku.com/articles/heroku-cli"
        exit 1
    fi

    # Créer l'application Heroku
    heroku create ndeyas-shop-$(date +%s)

    # Ajouter PostgreSQL
    heroku addons:create heroku-postgresql:mini

    # Configurer les variables d'environnement
    heroku config:set DEBUG=False
    heroku config:set SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

    # Déployer
    git push heroku main

    # Migrations et superuser
    heroku run python manage.py migrate
    heroku run python manage.py createsuperuser

    # Ouvrir l'app
    heroku open

    echo "✅ Déployé sur Heroku!"
}

# Déploiement sur VPS
deploy_vps() {
    echo "🖥️  Configuration pour VPS..."

    read -p "Entrez l'adresse IP de votre VPS: " VPS_IP
    read -p "Entrez votre nom d'utilisateur SSH: " SSH_USER

    echo "📝 Instructions pour déploiement VPS:"
    echo ""
    echo "1. Connectez-vous à votre VPS:"
    echo "   ssh $SSH_USER@$VPS_IP"
    echo ""
    echo "2. Exécutez ces commandes:"
    cat << 'EOF'
    # Mise à jour système
    sudo apt update && sudo apt upgrade -y

    # Installation des dépendances
    sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl

    # Cloner le projet
    git clone [votre-repo-url] /home/ndeyas_shop
    cd /home/ndeyas_shop

    # Environnement virtuel
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    # Configuration
    cp .env.production .env
    nano .env  # Configurer les variables

    # Django setup
    python manage.py collectstatic --noinput
    python manage.py migrate
    python manage.py createsuperuser

    # Configurer Gunicorn et Nginx (voir DEPLOYMENT_GUIDE.md)
EOF

    echo ""
    echo "📖 Consultez DEPLOYMENT_GUIDE.md pour la configuration complète de Nginx et Gunicorn"
}

# Tests post-déploiement
run_tests() {
    echo "🧪 Exécution des tests post-déploiement..."

    # Test de santé basique
    python manage.py check --deploy

    # Vérifier la collecte des statiques
    if [ -d "staticfiles" ]; then
        echo "✅ Fichiers statiques collectés"
    else
        echo "⚠️  Dossier staticfiles non trouvé"
    fi

    # Vérifier les migrations
    python manage.py showmigrations | grep -q "\[X\]"
    if [ $? -eq 0 ]; then
        echo "✅ Migrations appliquées"
    else
        echo "⚠️  Certaines migrations ne sont pas appliquées"
    fi
}

# Menu principal
main() {
    check_requirements
    prepare_production

    case $PLATFORM in
        railway)
            deploy_railway
            ;;
        render)
            deploy_render
            ;;
        heroku)
            deploy_heroku
            ;;
        vps)
            deploy_vps
            ;;
        *)
            echo "❌ Plateforme non supportée: $PLATFORM"
            echo "Plateformes disponibles: railway, render, heroku, vps"
            exit 1
            ;;
    esac

    run_tests

    echo ""
    echo "🎉 Déploiement terminé avec succès!"
    echo ""
    echo "📝 Prochaines étapes:"
    echo "1. Créer un compte staff: python manage.py createsuperuser"
    echo "2. Configurer les sauvegardes automatiques"
    echo "3. Activer HTTPS (Let's Encrypt)"
    echo "4. Configurer le monitoring (Sentry)"
    echo ""
    echo "📖 Consultez DEPLOYMENT_GUIDE.md pour plus de détails"
}

# Exécuter le script
main