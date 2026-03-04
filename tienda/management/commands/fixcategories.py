from django.core.management.base import BaseCommand
from tienda.models import Producto


class Command(BaseCommand):
    help = ('Corrige las categorías de los productos: borra valores inválidos y ' 
            'los reemplaza por el predeterminado actual.')

    def handle(self, *args, **options):
        valid_keys = {k for k, _ in Producto.CATEGORIAS}
        default = Producto._meta.get_field('categoria').get_default()

        productos = Producto.objects.all()
        fixed = 0
        for p in productos:
            if p.categoria not in valid_keys:
                p.categoria = default
                p.save(update_fields=['categoria'])
                fixed += 1
                self.stdout.write(f"Producto {p.id} ('{p.nombre}') cambiado a '{default}'")
        self.stdout.write(self.style.SUCCESS(f"Se actualizaron {fixed} productos."))