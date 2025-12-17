import os
import django
from django.conf import settings
from django.template.loader import render_to_string
from django.template import Context, Template
import sys

# Setup Django environment
sys.path.append(r'c:\Users\Usuario\Desktop\djangoproyect')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

def check_template(template_name):
    print(f"Checking {template_name}...")
    try:
        render_to_string(template_name, {'categorias': [], 'ultimos_productos': [], 'user': None})
        print(f"PASS: {template_name}")
    except Exception as e:
        print(f"FAIL: {template_name}")
        print(e)

if __name__ == "__main__":
    check_template('tienda/home.html')
    check_template('tienda/productos.html')
