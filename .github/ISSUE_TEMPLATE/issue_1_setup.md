title: "ISSUE-01: Configuración Inicial del Monorepo y Canalización de Ingesta Auditable"
labels: setup, arquitectura, backend
---

### Descripción
Creación e inicialización de la estructura Monorepo del Gemelo Digital Financiero, incluyendo la primera fase de ingesta de datos crudos y auditable.

### Tareas
- [x] Crear estructura de directorios (`apps/`, `packages/`, `data/`, `docs/`).
- [x] Configurar `.gitignore` y `README.md` profesional.
- [x] Documentar `canvas-v0.md` en la carpeta `docs/`[cite: 1].
- [ ] Definir el script de ingesta inicial en `packages/open_banking` que guarde archivos con hash de auditoría en `data/raw/`.
- [ ] Configurar el archivo `docker-compose.yml` básico con servicio PostgreSQL[cite: 1].

### Criterios de Aceptación (Definition of Done)
* Estructura subida al repositorio remoto en GitHub.
* Repositorio listo para recibir el desarrollo del backend de FastAPI y la capa de ingestión[cite: 1].
