# 🚀 Guía de Despliegue en Render

## Preparación Local ✅

Tu proyecto ya está configurado para producción con:
- ✅ `gunicorn` para servidor WSGI
- ✅ `whitenoise` para archivos estáticos
- ✅ `psycopg2-binary` para PostgreSQL
- ✅ `dj-database-url` para configuración de BD
- ✅ `build.sh` script de construcción
- ✅ `requirements.txt` actualizado

## Pasos para Desplegar en Render

### 1. Crear Cuenta en Render
- Ve a [https://render.com](https://render.com)
- Crea una cuenta gratuita

### 2. Subir tu Código a GitHub
```bash
git init
git add .
git commit -m "Preparado para Render"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

### 3. Crear PostgreSQL Database en Render
1. En el Dashboard de Render, click en **"New +"** → **"PostgreSQL"**
2. Nombre: `marketplace-db`
3. Database: `marketplace`
4. User: `marketplace`
5. Plan: **Free**
6. Click **"Create Database"**
7. **Guarda la URL de conexión** que aparece (DATABASE_URL)

### 4. Crear Web Service
1. Click en **"New +"** → **"Web Service"**
2. Conecta tu repositorio de GitHub
3. Configuración:
   - **Name**: `marketplace-django`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn marketplace.wsgi:application`
   - **Plan**: Free

### 5. Configurar Variables de Entorno
En la sección **Environment** del Web Service, agrega:

```
SECRET_KEY=genera-una-clave-secreta-aleatoria-aqui
DEBUG=False
ALLOWED_HOSTS=tu-app.onrender.com
DATABASE_URL=(la URL que guardaste del paso 3)
MERCADOPAGO_ACCESS_TOKEN=tu-token-de-mercadopago
MERCADOPAGO_SUCCESS_URL=https://tu-app.onrender.com/pago-exitoso/
MERCADOPAGO_FAILURE_URL=https://tu-app.onrender.com/pago-fallido/
MERCADOPAGO_PENDING_URL=https://tu-app.onrender.com/pago-pendiente/
```

**Para generar SECRET_KEY**, ejecuta en tu terminal:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Deploy
1. Click **"Create Web Service"**
2. Render automáticamente:
   - Clona tu repositorio
   - Ejecuta `build.sh`
   - Instala dependencias
   - Colecta archivos estáticos
   - Ejecuta migraciones
   - Inicia el servidor con gunicorn

### 7. Configurar Django Admin
Después del primer deploy, ejecuta en la consola de Render:
```bash
python manage.py createsuperuser
```

### 8. Configurar SITE_ID para django-allauth
1. Accede al admin: `https://tu-app.onrender.com/admin`
2. Ve a **Sites**
3. Edita el site existente:
   - Domain name: `tu-app.onrender.com`
   - Display name: `Marketplace`
4. Anota el ID (generalmente 1)
5. Si tu SITE_ID en settings.py no coincide, actualízalo

## ⚠️ Importante: Archivos Media

Render **NO** almacena archivos subidos permanentemente en el plan Free. 

Para imágenes de productos, tienes 2 opciones:

### Opción 1: Cloudinary (Recomendado)
```bash
pip install django-cloudinary-storage
```

Configurar en `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'cloudinary_storage',
    'cloudinary',
    # ...
]

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'tu-cloud-name',
    'API_KEY': 'tu-api-key',
    'API_SECRET': 'tu-api-secret'
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

### Opción 2: AWS S3
```bash
pip install django-storages boto3
```

## 🔍 Troubleshooting

### Error: "Application failed to respond"
- Verifica que `gunicorn` esté en `requirements.txt`
- Revisa los logs en Render Dashboard

### Error: "SECRET_KEY"
- Asegúrate de haber configurado SECRET_KEY en variables de entorno

### Error de Base de Datos
- Verifica que DATABASE_URL esté correctamente configurada
- Revisa que la database de PostgreSQL esté activa

### Archivos estáticos no cargan
- Ejecuta `python manage.py collectstatic` manualmente
- Verifica que STATIC_ROOT esté configurado

## 📝 Checklist Final

- [ ] Código en GitHub
- [ ] PostgreSQL database creada
- [ ] Web service creado
- [ ] Todas las variables de entorno configuradas
- [ ] ALLOWED_HOSTS incluye tu dominio de Render
- [ ] Superusuario creado
- [ ] SITE_ID configurado correctamente
- [ ] Proveedor de almacenamiento (Cloudinary/S3) configurado para imágenes

## 🎉 ¡Listo!

Tu aplicación debería estar funcionando en:
`https://tu-app-name.onrender.com`

**Nota**: El plan Free se "duerme" después de inactividad. El primer request puede tardar ~30 segundos.
