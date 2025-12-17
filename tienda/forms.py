from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'stock', 'imagen', 'categoria', 'ubicacion', 'latitud', 'longitud']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vino Malbec Reserva 750ml', 'maxlength': '100'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Características, estado, detalles importantes', 'rows': 5, 'maxlength': '500'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Unidades disponibles', 'min': '0'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Palermo, Buenos Aires', 'maxlength': '100'}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
        return nombre

    def clean_ubicacion(self):
        ubicacion = self.cleaned_data.get('ubicacion', '').strip()
        if ubicacion and len(ubicacion) < 3:
            raise forms.ValidationError('La ubicación debe tener al menos 3 caracteres.')
        return ubicacion

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if not imagen:
            return imagen
        content_type = getattr(imagen, 'content_type', '')
        if content_type not in ('image/jpeg', 'image/png'):
            raise forms.ValidationError('La imagen debe ser JPG o PNG.')
        size = getattr(imagen, 'size', 0)
        max_bytes = 5 * 1024 * 1024
        if size > max_bytes:
            raise forms.ValidationError('La imagen no puede superar 5 MB.')
        return imagen

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or int(stock) < 0:
            raise forms.ValidationError('El stock debe ser un número mayor o igual a 0.')
        return stock
