# 💳 Integración Mercado Pago - Guía de Configuración

## 📋 Resumen

Tu aplicación ahora soporta pagos con **Mercado Pago**. Los usuarios pueden elegir entre:
1. **Mercado Pago** - Múltiples métodos (transferencia, tarjeta, efectivo, billetera)
2. **Tarjeta local** - Simulación para pruebas

## 🔧 Pasos para configurar

### 1. Obtener credenciales de Mercado Pago

1. Ve a [Mercado Pago Developer Panel](https://www.mercadopago.com.ar/developers/panel)
2. Inicia sesión con tu cuenta de Mercado Pago (crear una si no tienes)
3. En el panel, busca **"Credenciales"** o **"Apps"**
4. Copia tu **Access Token** (encontrarás dos: uno de TEST y uno de PRODUCCIÓN)
   - Para desarrollo: usa el token de TEST
   - Para producción: usa el token de PRODUCCIÓN

### 2. Actualizar settings.py

Abre `marketplace/settings.py` y busca la sección **"CONFIGURACIÓN DE MERCADO PAGO"** (línea ~189)

Reemplaza:
```python
MERCADOPAGO_ACCESS_TOKEN = 'APP_USR-XXXXXXXXXXXXXXXX-XXXXXXXXXXXXXXXX'
```

Con tu token real:
```python
MERCADOPAGO_ACCESS_TOKEN = 'APP_USR-1234567890-abcdefg...'  # Tu token de Mercado Pago
```

### 3. Configurar URLs de retorno (producción)

En `marketplace/settings.py`, si vas a deployar a producción, actualiza:

```python
# Para desarrollo (localhost):
MERCADOPAGO_SUCCESS_URL = 'http://127.0.0.1:8000/pago-exitoso/'
MERCADOPAGO_FAILURE_URL = 'http://127.0.0.1:8000/pago-fallido/'
MERCADOPAGO_PENDING_URL = 'http://127.0.0.1:8000/pago-pendiente/'

# Para producción (reemplaza tu-dominio.com):
MERCADOPAGO_SUCCESS_URL = 'https://tu-dominio.com/pago-exitoso/'
MERCADOPAGO_FAILURE_URL = 'https://tu-dominio.com/pago-fallido/'
MERCADOPAGO_PENDING_URL = 'https://tu-dominio.com/pago-pendiente/'
```

### 4. Configurar URLs de retorno en Mercado Pago (producción)

1. En [Mercado Pago Developer](https://www.mercadopago.com.ar/developers/panel)
2. Ve a tu **aplicación**
3. Busca **"Configuración"** o **"Settings"**
4. Agrega las URLs de retorno:
   - Success: https://tu-dominio.com/pago-exitoso/
   - Failure: https://tu-dominio.com/pago-fallido/
   - Pending: https://tu-dominio.com/pago-pendiente/

## 🧪 Probar pagos

### Método 1: Mercado Pago (recomendado)

1. Ve a http://127.0.0.1:8000/login/ y inicia sesión
2. Agrega productos al carrito
3. Ve a **Finalizar compra** → Selecciona **"Mercado Pago"**
4. Haz clic en **"Continuar al pago"**
5. Serás redirigido a Mercado Pago
6. Usa datos de prueba (Mercado Pago proporciona tarjetas de prueba):
   - Tarjeta: **4111 1111 1111 1111**
   - Vencimiento: **11/25**
   - CVV: **123**
   - Titular: cualquier nombre

### Método 2: Tarjeta local (simulación)

1. Ve a **Finalizar compra** → Selecciona **"Tarjeta local (demo)"**
2. Completa los datos (valores de prueba aceptados)
3. El pago se procesa localmente sin conectar a Mercado Pago

## 📁 Archivos modificados/creados

### Modificados:
- `marketplace/settings.py` - Añadidas credenciales de Mercado Pago
- `tienda/views.py` - Integración con SDK de Mercado Pago
- `tienda/urls.py` - Nuevas rutas para retornos de pago
- `tienda/templates/tienda/pago.html` - Selector de métodos de pago

### Creados:
- `tienda/templates/tienda/pago_exitoso.html` - Confirmación de pago
- `tienda/templates/tienda/pago_fallido.html` - Error de pago
- `tienda/templates/tienda/pago_pendiente.html` - Pago en espera

## 🔒 Seguridad (Producción)

Para producción, recomendamos:

1. **No guardar el Access Token en settings.py**
   - Usa variables de entorno:
   ```python
   import os
   MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
   ```

2. **En tu servidor (Heroku, AWS, etc.), configura:**
   ```bash
   export MERCADOPAGO_ACCESS_TOKEN="tu_token_produccion"
   ```

3. **Implementar webhooks** para verificar pagos completados desde Mercado Pago (próxima mejora)

## 🚀 Próximas mejoras

- [ ] Implementar webhooks para notificaciones de pago
- [ ] Guardar información de pedidos en BD
- [ ] Email de confirmación automático
- [ ] Historial de compras del usuario
- [ ] Reembolsos y cancelaciones

## ❓ Solución de problemas

### Error: "Invalid access token"
→ Revisa que el token esté copiado correctamente en `MERCADOPAGO_ACCESS_TOKEN`

### Error: "Connection refused" o timeout
→ Verifica que tengas conexión a internet y que Mercado Pago esté disponible

### Pago redirige pero no vuelve
→ Asegúrate que las URLs en `settings.py` sean las correctas y accesibles desde tu navegador

## 📞 Soporte

- Documentación oficial: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/integration-configuration/how-it-works
- SDK Python: https://github.com/mercadopago/sdk-python
