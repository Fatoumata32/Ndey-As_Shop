#!/usr/bin/env python
"""
Script pour corriger les settings.py sur le serveur
À exécuter avec: python fix_settings.py
"""

import os
import re

settings_path = '/home/FarmConnects/ndeyeas_shop/ndeyas_shop/settings.py'

# Si on est en local, utiliser le chemin local
if not os.path.exists(settings_path):
    settings_path = 'ndeyas_shop/settings.py'

print(f"📝 Modification de {settings_path}...")

with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Chercher et remplacer la section allauth
old_pattern = r"# Allauth settings.*?ACCOUNT_LOGOUT_ON_GET = .*?\n"
new_settings = """# Allauth settings
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username', 'password1*', 'password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Can be 'mandatory', 'optional', or 'none'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGOUT_ON_GET = True
"""

content = re.sub(old_pattern, new_settings, content, flags=re.DOTALL)

# Sauvegarder
with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Settings corrigés avec succès!")
print("\nVeuillez maintenant exécuter:")
print("  python manage.py check")
print("  python manage.py migrate")
