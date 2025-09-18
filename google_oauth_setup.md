# Google OAuth Setup Instructions

## 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **big-crow-472320-e6**
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Configure OAuth consent screen if not already done:
   - User Type: External
   - App name: Ndeyas Shop
   - Support email: Your email
   - Authorized domains: (leave empty for development)
   - Developer contact: Your email

6. For OAuth client ID:
   - Application type: **Web application**
   - Name: **Ndeyas Shop OAuth**
   - Authorized JavaScript origins:
     - http://localhost:8000
     - http://127.0.0.1:8000
   - Authorized redirect URIs:
     - http://localhost:8000/accounts/google/login/callback/
     - http://127.0.0.1:8000/accounts/google/login/callback/

7. Save and download the credentials

## 2. Add to .env file

Create a `.env` file in the project root with:

```
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

## 3. Configure Django Settings

The settings have been configured in settings.py to use django-allauth

## 4. Run migrations

```bash
python manage.py migrate
```

## 5. Create a social app in Django Admin

1. Go to http://127.0.0.1:8000/admin/
2. Go to **Sites** and make sure you have a site with domain `127.0.0.1:8000` (or create one)
3. Go to **Social applications**
4. Add a new social application:
   - Provider: Google
   - Name: Google OAuth
   - Client id: (from Google Console)
   - Secret key: (from Google Console)
   - Sites: Select your site

## 6. Test

Visit http://127.0.0.1:8000/ and click "Se connecter avec Google"