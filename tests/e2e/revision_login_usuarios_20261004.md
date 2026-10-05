# Revisión de login y gestión de usuarios — 04/10/2026

## Comprobado visualmente con servidores locales

- Cierre de sesión de `medico.demo` y apertura del login.
- Formulario vacío: mensajes de usuario y contraseña obligatorios.
- ADMIN con contraseña incorrecta: mensaje genérico «Usuario o contraseña inválidos»; no se abre sesión.
- ADMIN con credenciales válidas: acceso a Personal y cuentas, Auditoría y configuración; sin navegación clínica.
- Panel Cuentas de usuario: listado de `admin` y `medico.demo`, roles, profesional vinculado, estado y último acceso.
- Roles de ADMIN: PROFESIONAL deshabilitado cuando no hay profesional vinculado. Guardar una selección vacía muestra un error sin modificar los roles.
- Alta de usuario vacía: exige nombre, contraseña, confirmación y al menos un rol.
- Cuenta propia: Dar de baja y restablecimiento administrativo de contraseña deshabilitados. El cambio propio sigue disponible en la opción Contraseña de la cuenta.
- Acceso directo de ADMIN a `/admision?patientId=16`: redirigido a inicio.
- Acceso a `/configuracion/personal` sin sesión: redirigido a login con el destino original.
- Login de `medico.demo` con ese destino administrativo: redirigido a inicio, con navegación clínica y sin opciones de administración.
- El mensaje largo debajo de P/E, T/E y P/T fue retirado; con 80 kg y 180 cm se muestra solamente `IMC: 24.691 · Normal`. Los estados de carga y los mensajes de datos incompletos/error se conservan.

No se crearon, desactivaron ni cambiaron permisos o contraseñas de cuentas en la base local del servidor. Los cambios de credenciales y de usuarios se ejercitaron en las pruebas aisladas siguientes.

## Fallos corregidos

1. Los errores del alta, roles y restablecimiento aparecían en el panel detrás del modal. Ahora se muestran dentro del diálogo activo. Se confirmó visualmente el error de roles y se agregaron regresiones para roles y rechazo del alta por el servidor.
2. El panel ofrecía restablecer administrativamente la contraseña de la cuenta actual, aunque el backend rechaza ese flujo. Se deshabilitó esa acción sobre la propia cuenta; tiene su flujo de cambio propio.

## Pruebas automatizadas

- Frontend: **47 aprobadas** en LoginAccessForm, LoginView, PersonalView, UsersPanel, router y AdmisionView.
- Backend: **26 aprobadas** en integración MySQL de autenticación/usuarios y pruebas unitarias de autorización/listado. Incluyen creación, duplicados, roles, cuentas inactivas, baja propia rechazada, restablecimiento y cambio de contraseña, invalidación de credenciales anteriores, protección de endpoints y auditoría.
- Base aislada creada para esta revisión: `ipress_test_auth_20261004_5887e2d0`. Las fixtures migraron y retiraron exclusivamente sus tablas; no usaron la base clínica local.
- La primera ejecución parcial disparó el umbral global de cobertura del proyecto (47.63 % frente a 90 %) pese a aprobar los 26 casos. La comprobación de esta selección se repitió con `--no-cov` y terminó con código 0. No se afirma cobertura global del proyecto.
- `npm run type-check`: aprobado.
- ESLint: aprobado (`node node_modules/eslint/bin/eslint.js .`).
- `npm run lint:check`: no pudo completarse porque Control de aplicaciones de Windows bloqueó el módulo nativo de Oxlint. No se cambiaron políticas del sistema ni dependencias para eludirlo.
- `git diff --check`: sin errores de espacios. Detector Impeccable: sin hallazgos.

## Evidencias

- [Error de roles dentro del modal](evidence_auth_20261004/roles-validacion.png)
- [Validación del alta](evidence_auth_20261004/alta-validacion.png)
- [Valoración sin mensaje largo](evidence_auth_20261004/valoracion-sin-mensaje.png)
