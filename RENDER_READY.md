# ✅ PROYECTO LISTO PARA RENDER

## 📦 Archivos Creados/Actualizados

### Archivos de Configuración
- ✅ `requirements.txt` - Dependencias actualizadas
- ✅ `build.sh` - Script de construcción para Render
- ✅ `Procfile` - Comando de inicio con gunicorn
- ✅ `render.yaml` - Configuración automática de Render
- ✅ `.gitignore` - Archivos a excluir del repositorio
- ✅ `.env.example` - Plantilla de variables de entorno

### Configuración de Django
- ✅ `settings.py` actualizado con:
  - Variables de entorno (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
  - WhiteNoise para archivos estáticos
  - Configuración de PostgreSQL con dj-database-url
  - STORAGES configurado para WhiteNoise

### Documentación
- ✅ `README_DEPLOY.md` - Guía completa de despliegue

## 🚀 Próximos Pasos

1. **Subir a GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Preparado para despliegue en Render"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```

2. **Crear cuenta en Render**: https://render.com

3. **Crear PostgreSQL Database**:
   - Dashboard → New + → PostgreSQL
   - Nombre: `marketplace-db`
   - Plan: Free
   - Guardar DATABASE_URL

4. **Crear Web Service**:
   - New + → Web Service
   - Conectar repositorio GitHub
   - Build Command: `./build.sh`
   - Start Command: `gunicorn marketplace.wsgi:application`

5. **Configurar Variables de Entorno en Render**:
   ```
   SECRET_KEY=<genera-uno-nuevo>
   DEBUG=False
   ALLOWED_HOSTS=tu-app.onrender.com
   DATABASE_URL=<de-la-database-postgres>
   MERCADOPAGO_ACCESS_TOKEN=<tu-token>
   ```

6. **Generar SECRET_KEY**:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

7. **Deploy**: Click "Create Web Service" y esperar

8. **Crear superusuario** (después del deploy):
   En Render Shell:
   ```bash
   python manage.py createsuperuser
   ```

## ⚠️ IMPORTANTE: Archivos Media

Render no guarda archivos subidos en el plan Free. Necesitas:

### Opción 1: Cloudinary (Recomendado - Free)
```bash
pip install django-cloudinary-storage
```

### Opción 2: AWS S3
```bash
pip install django-storages boto3
```

Consulta `README_DEPLOY.md` para más detalles.

## 📋 Checklist Pre-Deploy

- [ ] Código en GitHub
- [ ] Variables de entorno preparadas
- [ ] SECRET_KEY generada
- [ ] TOKEN de Mercado Pago disponible
- [ ] Cuenta en Cloudinary/AWS (para imágenes)

## 🎯 URL Final

Después del deploy: `https://tu-app-name.onrender.com`

## 💡 Tips

- El plan Free se "duerme" tras inactividad (primer request ~30s)
- Los logs están disponibles en Render Dashboard
- Puedes ejecutar comandos Django en Render Shell
- Las migraciones se ejecutan automáticamente en cada deploy

---

📖 **Documentación completa**: Ver `README_DEPLOY.md`
