# shop/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Category, ProductImage, Size


class MultipleFileInput(forms.ClearableFileInput):
    """Widget personnalisé pour upload multiple de fichiers"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Champ personnalisé pour gérer plusieurs fichiers"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ProductForm(forms.ModelForm):
    """Formulaire principal pour les produits"""
    
    # Champ pour upload multiple d'images
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control'
        }),
        label='Images du produit',
        help_text='Sélectionnez une ou plusieurs images. La première sera l\'image principale.'
    )
    
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'sale_price', 'on_sale', 
                  'category', 'quantity', 'sizes', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du produit...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Description détaillée du produit...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0',
                'placeholder': 'Prix en F CFA'
            }),
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0',
                'placeholder': 'Prix en solde (optionnel)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Quantité en stock'
            }),
            'on_sale': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sizes': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emoji ou icône (optionnel)'
            })
        }
        labels = {
            'name': 'Nom du produit',
            'description': 'Description',
            'price': 'Prix (F CFA)',
            'sale_price': 'Prix en solde (F CFA)',
            'category': 'Catégorie',
            'quantity': 'Quantité en stock',
            'on_sale': 'En solde',
            'sizes': 'Tailles disponibles',
            'icon': 'Icône'
        }
        help_texts = {
            'quantity': 'Nombre d\'unités disponibles',
            'sale_price': 'Laissez vide si pas en solde',
            'icon': 'Emoji ou caractère pour représenter le produit'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre certains champs obligatoires
        self.fields['name'].required = True
        self.fields['description'].required = True
        self.fields['price'].required = True
        self.fields['category'].required = True
        self.fields['quantity'].required = True
        
        # Ajouter un placeholder pour la catégorie
        self.fields['category'].empty_label = "-- Sélectionnez une catégorie --"
        
        # Filtrer les tailles selon la catégorie si on modifie un produit existant
        if self.instance.pk and self.instance.category:
            self.fields['sizes'].queryset = self.instance.category.available_sizes.all()
        else:
            self.fields['sizes'].queryset = Size.objects.all()
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError('Le prix doit être supérieur à 0.')
        return price
    
    def clean_sale_price(self):
        sale_price = self.cleaned_data.get('sale_price')
        price = self.cleaned_data.get('price')
        
        if sale_price is not None:
            if sale_price <= 0:
                raise ValidationError('Le prix en solde doit être supérieur à 0.')
            if price and sale_price >= price:
                raise ValidationError('Le prix en solde doit être inférieur au prix normal.')
        
        return sale_price
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise ValidationError('La quantité ne peut pas être négative.')
        return quantity
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        on_sale = cleaned_data.get('on_sale')
        sale_price = cleaned_data.get('sale_price')
        
        # Si en solde, vérifier qu'il y a un prix de solde
        if on_sale and not sale_price:
            self.add_error('sale_price', 'Le prix en solde est requis si le produit est en solde.')
        
        # Si pas en solde, effacer le prix de solde
        if not on_sale:
            cleaned_data['sale_price'] = None
        
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Formulaire pour les catégories"""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la catégorie...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Description de la catégorie (optionnel)...'
            }),
        }
        labels = {
            'name': 'Nom de la catégorie',
            'description': 'Description',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('Le nom de la catégorie est requis.')
        
        # Vérifier l'unicité (en excluant l'instance actuelle si modification)
        queryset = Category.objects.filter(name__iexact=name.strip())
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError('Une catégorie avec ce nom existe déjà.')
        
        return name.strip()


class ProductImageForm(forms.ModelForm):
    """Formulaire pour une image individuelle de produit"""
    
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'alt_text', 'order']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Texte alternatif pour l\'image'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            })
        }
        labels = {
            'image': 'Image',
            'is_primary': 'Image principale',
            'alt_text': 'Texte alternatif',
            'order': 'Ordre d\'affichage'
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            # Vérifier la taille (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('L\'image ne peut pas dépasser 5MB.')
            
            # Vérifier le type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(image, 'content_type'):
                if image.content_type not in allowed_types:
                    raise ValidationError(
                        'Format non supporté. Utilisez JPG, PNG, GIF ou WebP.'
                    )
        
        return image


# Formset pour gérer plusieurs images d'un produit existant
ProductImageFormSet = forms.modelformset_factory(
    ProductImage,
    form=ProductImageForm,
    extra=1,
    can_delete=True,
    can_order=False
)


class BulkActionForm(forms.Form):
    """Formulaire pour les actions en masse sur les produits"""
    
    ACTION_CHOICES = [
        ('', '-- Sélectionnez une action --'),
        ('mark_sold_out', 'Marquer comme épuisé'),
        ('mark_available', 'Marquer comme disponible'),
        ('apply_discount', 'Appliquer une remise'),
        ('delete', 'Supprimer'),
        ('change_category', 'Changer de catégorie'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Action à effectuer'
    )
    
    discount_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'ex: 10.50',
            'min': 0,
            'max': 100
        }),
        label='Pourcentage de remise (%)'
    )
    
    new_category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nouvelle catégorie',
        empty_label='-- Sélectionnez une catégorie --'
    )
    
    product_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'apply_discount':
            discount = cleaned_data.get('discount_percent')
            if not discount:
                self.add_error('discount_percent', 'Le pourcentage de remise est requis.')
            elif discount <= 0 or discount >= 100:
                self.add_error('discount_percent', 'Le pourcentage doit être entre 0 et 100.')
        
        elif action == 'change_category':
            new_category = cleaned_data.get('new_category')
            if not new_category:
                self.add_error('new_category', 'Veuillez sélectionner une catégorie.')
        
        return cleaned_data


class SearchForm(forms.Form):
    """Formulaire de recherche simple"""
    
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher un produit...'
        }),
        label='Recherche'
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Catégorie',
        empty_label='Toutes les catégories'
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix min',
            'min': '0'
        }),
        label='Prix minimum'
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix max',
            'min': '0'
        }),
        label='Prix maximum'
    )
    
    in_stock_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='En stock uniquement'
    )
    
    active_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Produits non épuisés uniquement',
        initial=True
    )