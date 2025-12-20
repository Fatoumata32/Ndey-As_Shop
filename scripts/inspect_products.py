import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','ndeyas_shop.settings')
import django
django.setup()
from shop.models import Product
print('total', Product.objects.count())
print('on_sale', Product.objects.filter(on_sale=True).count())
for p in Product.objects.filter(on_sale=True):
    print(p.id, p.name, p.sale_price, p.price, p.sold_out)
