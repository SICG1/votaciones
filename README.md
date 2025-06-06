# Sistema de votaciones

Este proyecto implementa un ejemplo simple de sistema de votación en tiempo real utilizando **FastAPI**. Existen tres tipos de usuarios:

- **admin**: administrador del sistema.
- **manager**: gestor con permisos para registrar miembros y candidatos.
- **user**: votantes comunes.

## Requisitos

- Python 3.10+
- Las dependencias enumeradas en `requirements.txt`.

Instalación de dependencias:

```bash
pip install -r requirements.txt
```

La base de datos SQLite se crea automáticamente al iniciar la aplicación.

## Uso

Ejecutar el servidor con **uvicorn**:

```bash
uvicorn main:app --reload
```

### Endpoints principales

- `POST /members` - Agregar miembros (requiere `acting_user` con rol *admin* o *manager*).
- `POST /candidates` - Registrar candidatos (requiere `acting_user` con rol *admin* o *manager*).
- `POST /vote` - Emitir un voto (`acting_user` debe existir y no haber votado antes).
- `GET /results` - Obtener el conteo actual de votos.
- `WS /ws` - WebSocket para recibir actualizaciones en tiempo real.

Los datos se almacenan de forma persistente en un archivo `database.db` mediante **SQLModel**.
