import os
import django
from django.conf import settings
from django.template.loader import get_template
from django.template import Context, Template

# Configure Django settings manually
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
settings.configure(
    DEBUG=True,
    SECRET_KEY='secret',
    ROOT_URLCONF=__name__,
    INSTALLED_APPS=[
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.humanize',
        'tienda',
    ],
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'tienda', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }],
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
)

django.setup()

def check_template(template_name):
    try:
        get_template(template_name)
        print(f"SUCCESS: {template_name} parsed successfully.")
    except Exception as e:
        print(f"ERROR: {template_name} failed to parse.")
        print(e)

print("Checking templates...")
check_template('tienda/home.html')
check_template('tienda/productos.html')
check_template('tienda/detalle_producto.html')
