# shop/forms.py
from django import forms
from .models import Product, Category, ProductImage

class ProductForm(forms.ModelForm):
    """Formulaire pour les produits"""
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'sale_price', 'on_sale', 
                  'category', 'quantity', 'sizes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'on_sale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class CategoryForm(forms.ModelForm):
    """Formulaire pour les catégories"""
    class Meta:
        model = Category
        fields = ['name', 'icon', 'category_type', 'attributes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '📦'}),
            'category_type': forms.Select(attrs={'class': 'form-control'}),
        }

class ProductImageForm(forms.ModelForm):
    """Formulaire pour les images de produits"""
    class Meta:
        model = ProductImage
        fields = ['image', 'order']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }