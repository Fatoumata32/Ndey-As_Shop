import os
import re

def update_shop_template():
    """Met à jour le template shop.html avec les fonctionnalités Django"""
ECHO is off.
    template_path = 'shop/templates/shop/shop.html'
    if not os.path.exists(template_path):
        print(f"[ERREUR] {template_path} non trouvé!")
        return
ECHO is off.
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
ECHO is off.
    # Remplacer la section des produits
    products_section = '''
                <!-- Products Grid -->
                <div id="item-grid" class="item-grid">
                    {% if products %}
                        {% for product in products %}
                        <div class="product-card {% if product.sold_out %}sold-out{% endif %}" 
                             onclick="window.location.href='{% url 'shop:product_detail' product.id %}'">
                            <div class="product-image">
                                {% if product.images.first %}
                                    <img src="{{ product.images.first.image.url }}" alt="{{ product.name }}" loading="lazy">
                                {% else %}
                                    <img src="{% static 'shop/img/placeholder.jpg' %}" alt="{{ product.name }}" loading="lazy">
                                {% endif %}
                            </div>
                            <div class="product-info">
                                <div class="product-name">
                                    <i class="{{ product.icon|default:'fas fa-box' }} me-2"></i>{{ product.name }}
                                </div>
