"""
Middleware pour tracker le trafic du site
"""
from .models import PageView
import logging

logger = logging.getLogger(__name__)


class TrafficTrackingMiddleware:
    """Middleware pour enregistrer les pages visitées"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Exclude paths - ne pas tracker certaines pages
        self.excluded_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/.well-known/',
        ]
    
    def __call__(self, request):
        # Vérifier si le chemin ne doit pas être tracked
        is_excluded = any(request.path.startswith(path) for path in self.excluded_paths)
        
        if not is_excluded:
            try:
                # Enregistrer la visite après la réponse
                response = self.get_response(request)
                
                # Seulement tracker les GET requests avec statut 200
                if request.method == 'GET' and response.status_code == 200:
                    self.track_page_view(request)
                
                return response
            except Exception as e:
                logger.error(f"Error in TrafficTrackingMiddleware: {str(e)}")
                return self.get_response(request)
        else:
            return self.get_response(request)
    
    def track_page_view(self, request):
        """Enregistrer une visite de page"""
        try:
            page_view = PageView.objects.create(
                user=request.user if request.user.is_authenticated else None,
                page_url=request.path,
                page_title=request.META.get('HTTP_REFERER', '').split('/')[-1] or request.path,
                referrer=request.META.get('HTTP_REFERER', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                ip_address=self.get_client_ip(request),
                session_id=request.session.session_key,
            )
        except Exception as e:
            logger.error(f"Error recording page view: {str(e)}")
    
    def get_client_ip(self, request):
        """Obtenir l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
