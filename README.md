# Planificador de Estudios · Backend

API REST del **Planificador de Estudios**, un proyecto educativo para organizar actividades académicas, registrar avances y distribuir la carga diaria de estudio.

**[Documentación de la API](https://planificador-estudios-backend-80p8.onrender.com/api/docs/)** · **[Demo en Vercel](https://planificador-estudios-frontend.vercel.app)** · **[Proyecto completo](https://github.com/juzer1711/Planificador_Estudios)** · **[Frontend](https://github.com/Sepul11/planificador-estudios-frontend)**

## Funcionalidades

- Registro e inicio de sesión mediante correo y contraseña, con autenticación por token.
- Gestión de actividades con título, curso, tipo, descripción, fecha y horario.
- Gestión de subtareas con fecha objetivo, horas estimadas y estado de finalización.
- Registro de avances con estados `hecho`, `pospuesto` y `deshacer`, notas e historial.
- Cálculo del progreso según las subtareas completadas de cada actividad.
- Consulta de la planificación del día y generación de eventos para el calendario.
- Configuración del límite diario de horas de estudio por usuario.
- Detección de sobrecarga y recomendaciones para redistribuir las horas.
- Reprogramación manual y búsqueda automática de fechas disponibles para las subtareas pendientes.

## Tecnologías

| Tecnología | Uso |
| --- | --- |
| Python y Django | Modelos, lógica de negocio y administración |
| Django REST Framework | API REST, serialización, permisos y tokens |
| Django ORM | Acceso a datos y relaciones entre entidades |
| PostgreSQL y psycopg2 | Persistencia en Supabase |
| SQLite | Base de datos local cuando no se define `DATABASE_URL` |
| dj-database-url | Configuración de la conexión mediante `DATABASE_URL` |
| django-cors-headers | Acceso desde el frontend |
| drf-spectacular | OpenAPI, Swagger UI y ReDoc |
| Gunicorn y Render | Ejecución y despliegue |

Las dependencias se encuentran en [requirements.txt](./requirements.txt).

## Modelo de datos

| Entidad | Responsabilidad |
| --- | --- |
| Usuario | Cuenta de acceso y propietario de las actividades |
| Actividad | Trabajo académico con fecha, horario y datos del curso |
| Subtarea | Parte de una actividad con fecha objetivo, horas y estado |
| Avance de subtarea | Registro de estado, nota y fecha de un avance |
| Perfil | Límite de horas de estudio diarias del usuario |

Los modelos de planificación están en [actividades/models.py](./actividades/models.py). La autenticación utiliza el modelo de usuario de Django.

## Lógica de planificación

El módulo [actividades/planificador.py](./actividades/planificador.py) compara las horas de las subtareas pendientes de una fecha con el límite diario del usuario, cuyo valor inicial es de seis horas.

Cuando detecta sobrecarga, genera sugerencias según la disponibilidad: mover una subtarea a otro día, dividir sus horas entre dos fechas, reducir el tiempo estimado o ajustar el límite diario. También identifica tareas vencidas, actividades con una carga elevada y próximos días con tiempo libre.

Las recomendaciones se basan en reglas, las fechas de las subtareas y los días de estudio inferidos de su historial.

## API

**URL desplegada:** `https://planificador-estudios-backend-80p8.onrender.com`

| Método | Ruta | Función |
| --- | --- | --- |
| POST | `/auth/register/` | Registrar un usuario |
| POST | `/auth/login/` | Iniciar sesión y obtener el token |
| GET, POST | `/api/actividades/` | Listar y crear actividades |
| GET, PUT, PATCH, DELETE | `/api/actividades/{id}/` | Consultar, actualizar o eliminar una actividad |
| GET | `/api/actividades/hoy/` | Consultar la planificación del día |
| GET | `/api/actividades/calendario/` | Obtener eventos para el calendario |
| GET | `/api/actividades/recomendaciones/` | Obtener recomendaciones |
| GET | `/api/actividades/{id}/progreso/` | Consultar el progreso |
| PATCH | `/api/actividades/{id}/reprogramar/` | Cambiar la fecha de la actividad o de sus subtareas pendientes |
| PATCH | `/api/actividades/{id}/auto_reprogramar/` | Buscar una fecha disponible y reprogramar |
| GET, POST | `/api/subtareas/` | Listar y crear subtareas |
| GET, PUT, PATCH, DELETE | `/api/subtareas/{id}/` | Consultar, actualizar o eliminar una subtarea |
| POST | `/api/subtareas/{id}/avance/` | Registrar un avance |
| GET, PATCH | `/api/perfil/limite` | Consultar el perfil y actualizar el límite diario |

Para consumir los endpoints protegidos, incluye el token devuelto por el inicio de sesión:

```http
Authorization: Token <token>
```

Documentación disponible: [Swagger UI](https://planificador-estudios-backend-80p8.onrender.com/api/docs/), [ReDoc](https://planificador-estudios-backend-80p8.onrender.com/api/redoc/) y [esquema OpenAPI](https://planificador-estudios-backend-80p8.onrender.com/api/schema/).

## Ejecutar en desarrollo

Necesitas Python compatible con las dependencias de [requirements.txt](./requirements.txt) y pip.

```bash
git clone https://github.com/CristianOspina03/planificador_estudios_backend.git
cd planificador_estudios_backend
python -m venv .venv
```

Activa el entorno virtual en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En Linux o macOS:

```bash
source .venv/bin/activate
```

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

### Variables de entorno

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave de Django, necesaria para iniciar la aplicación |
| `DATABASE_URL` | Conexión a PostgreSQL; si se omite, se utiliza SQLite local |

Genera una clave para la sesión de desarrollo en PowerShell:

```powershell
$env:SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

En Linux o macOS:

```bash
export SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
```

La configuración lee las variables del entorno del proceso; no carga automáticamente un archivo `.env`.

Aplica las migraciones e inicia el servidor:

```bash
python manage.py migrate
python manage.py runserver
```

La API queda disponible en `http://localhost:8000` y Swagger UI en `http://localhost:8000/api/docs/`.

Para acceder al panel de administración con una cuenta propia:

```bash
python manage.py createsuperuser
```

## Organización del código

| Carpeta o archivo | Contenido |
| --- | --- |
| [actividades/](./actividades/) | Modelos, serializadores, vistas y rutas de planificación |
| [actividades/planificador.py](./actividades/planificador.py) | Análisis de carga y recomendaciones |
| [usuarios/](./usuarios/) | Registro e inicio de sesión |
| [miniproyectoI/settings.py](./miniproyectoI/settings.py) | Base de datos, autenticación, CORS y documentación |
| [miniproyectoI/urls.py](./miniproyectoI/urls.py) | Rutas principales y documentación |
| [manage.py](./manage.py) | Comandos de administración de Django |

## Despliegue

El backend se aloja en **Render** y se conecta a **PostgreSQL en Supabase** mediante `DATABASE_URL`. Gunicorn ejecuta la aplicación WSGI:

```bash
gunicorn miniproyectoI.wsgi:application
```

El frontend se publica en **Vercel**. Su dominio y `http://localhost:5173` están incluidos en la configuración CORS del backend.

Consulta el [repositorio general](https://github.com/juzer1711/Planificador_Estudios) para conocer la arquitectura completa y acceder a ambos componentes del proyecto.
