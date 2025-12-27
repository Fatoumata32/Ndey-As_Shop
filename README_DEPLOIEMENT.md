# 🚀 Guide de Déploiement Rapide - NDEY'AS SHOP

## ⚠️ PROBLÈME ACTUEL

Le site https://www.ndeyeas.shop/ affiche une erreur car une migration importante doit être appliquée.

## ✅ SOLUTION RAPIDE (3 étapes)

### Étape 1: Connexion au serveur
```bash
ssh FarmConnects@ndeyeas.shop
```

### Étape 2: Copier-coller cette commande
```bash
source /home/FarmConnects/.virtualenvs/env/bin/activate && cd /home/FarmConnects/ndeyeas_shop && git pull origin master && python3 -c "
import re
with open('ndeyas_shop/settings.py', 'r') as f: content = f.read()
content = re.sub(r'ACCOUNT_LOGIN_METHODS\s*=\s*\{[^}]+\}', \"ACCOUNT_LOGIN_METHODS = {'email', 'username'}\", content)
content = re.sub(r'ACCOUNT_SIGNUP_FIELDS\s*=\s*\[[^\]]+\]', \"ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']\", content)
content = re.sub(r'ACCOUNT_USER_MODEL_USERNAME_FIELD\s*=\s*[^\n]+', \"ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'\", content)
with open('ndeyas_shop/settings.py', 'w') as f: f.write(content)
print('✅ Settings corrigé')
" && python manage.py check && python manage.py migrate shop && touch /var/www/ndeyeas_shop_uwsgi.ini && echo "✅ DÉPLOIEMENT TERMINÉ"
```

### Étape 3: Vérifier
Visitez https://www.ndeyeas.shop/ - le site devrait fonctionner!

---

## 📋 Ce qui a été modifié

✅ **Suppression de la gestion de stock** (champ `quantity`)
- Formulaire d'ajout de produit simplifié
- Plus de vérification de stock lors des commandes
- Modèle `Product` allégé

✅ **Clic sur image** pour voir le détail du produit
- Sur la page d'accueil, cliquer sur une image ouvre sa page de détail

✅ **Optimisation des performances**
- Requêtes SQL réduites avec `select_related` et `prefetch_related`
- Chargement plus rapide des pages

---

## 📂 Fichiers Disponibles

- **[COMMANDES_SERVEUR.txt](COMMANDES_SERVEUR.txt)** - 3 options de déploiement
- **[QUICK_DEPLOY.txt](QUICK_DEPLOY.txt)** - Guide détaillé étape par étape
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Documentation complète
- **[HOTFIX_DEPLOY.sh](HOTFIX_DEPLOY.sh)** - Script automatique
- **[fix_settings.py](fix_settings.py)** - Script Python de correction

---

## 🆘 Besoin d'aide?

**Méthode Alternative (Script automatique):**
```bash
ssh FarmConnects@ndeyeas.shop
source /home/FarmConnects/.virtualenvs/env/bin/activate
cd /home/FarmConnects/ndeyeas_shop
git pull origin master
chmod +x HOTFIX_DEPLOY.sh
bash HOTFIX_DEPLOY.sh
```

**En cas de problème:**
```bash
# Voir les logs
sudo journalctl -u uwsgi -n 50 --no-pager

# Redémarrer le serveur
sudo systemctl restart uwsgi
```

---

## ✨ Résultat Attendu

Après le déploiement, vous devriez avoir:
- ✅ Site fonctionnel sans erreur
- ✅ Page d'accueil avec images cliquables
- ✅ Formulaire d'ajout de produit sans champ "quantité"
- ✅ Performance améliorée

---

**Date de dernière mise à jour:** 27 Décembre 2024  
**Version:** 1.0 - Migration suppression quantity
