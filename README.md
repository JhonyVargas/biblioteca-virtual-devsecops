# 📚 Biblioteca Virtual — DevSecOps con herramientas de escaneo OWASP

Aplicación web sencilla (Flask + SQLite) para gestionar libros y préstamos, usada para
demostrar **escaneo de vulnerabilidades automatizado** con herramientas de la lista de
[OWASP Vulnerability Scanning Tools](https://owasp.org/www-community/Vulnerability_Scanning_Tools)
y **despliegue automático en la nube (Render)** mediante **GitHub Actions**.

> ⚠️ La versión inicial contiene **vulnerabilidades intencionales** (marcadas con `VULN`
> en el código) para que los escáneres las detecten. Más abajo se explica cómo corregirlas.

## Funcionalidades
- Listar, buscar, registrar, editar y eliminar libros
- Marcar libros como prestados / devueltos
- Endpoint `/health` para el monitoreo del despliegue

## Herramientas de seguridad del pipeline

| Etapa | Herramienta | Tipo | Qué detecta en este proyecto |
|---|---|---|---|
| 1 | [Bandit](https://github.com/PyCQA/bandit) | SAST | SQL Injection (B608), `debug=True` (B201), bind 0.0.0.0 (B104) |
| 2 | [Gitleaks](https://github.com/gitleaks/gitleaks) | Secretos | `SECRET_KEY` escrita en el código |
| 3 | [OSV-Scanner](https://github.com/google/osv-scanner) | SCA | CVEs en Flask, Werkzeug, Jinja2 y gunicorn |
| 4 | [Grype](https://github.com/anchore/grype) | Contenedor | CVEs en la imagen Docker (SO + paquetes Python) |
| 5 | [Nuclei](https://github.com/projectdiscovery/nuclei) | DAST | Cabeceras faltantes y configuraciones débiles en la app desplegada |

## Flujo del pipeline (`.github/workflows/security-pipeline.yml`)

```
push a main ──► Bandit ─┐
               Gitleaks ├──► ¿todo OK? ──► Deploy a Render ──► Nuclei (DAST sobre la URL pública)
            OSV-Scanner ├
                  Grype ┘
```
Si **cualquier** escáner encuentra problemas, el despliegue **no se ejecuta**.

## Ejecutar localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python app.py                   # http://localhost:5000
```
Con Docker:
```bash
docker build -t biblioteca .
docker run -p 10000:10000 biblioteca   # http://localhost:10000
```

## Despliegue en Render (paso a paso)

1. Sube este proyecto a un **repositorio público** en GitHub.
2. Crea una cuenta en [render.com](https://render.com) → **New → Web Service** → conecta el repositorio.
   - Runtime: **Docker** · Plan: **Free**
   - En *Settings*, desactiva **Auto-Deploy** (el pipeline decide cuándo desplegar).
3. En Render: *Settings → Deploy Hook* → copia la URL.
4. En GitHub: *Settings → Secrets and variables → Actions*:
   - **Secret** `RENDER_DEPLOY_HOOK` = la URL del deploy hook
   - **Variable** `APP_URL` = la URL pública, por ejemplo `https://biblioteca-virtual-xxxx.onrender.com`
5. Haz un `push` a `main` y revisa la pestaña **Actions**.

## Demo: SQL Injection
En el buscador escribe:
```
zzz' OR 1=1 --
```
La consulta devuelve **todos** los libros aunque ninguno coincida con "zzz": la entrada se inyectó en el SQL.

## Corrigiendo las vulnerabilidades

**1. SQL Injection** (`app.py`, ruta `/`) — usa una consulta parametrizada:
```python
sql = "SELECT * FROM libros WHERE titulo LIKE ? OR autor LIKE ? ORDER BY titulo"
libros = db.execute(sql, (f"%{q}%", f"%{q}%")).fetchall()
```

**2. Secreto en el código** — léelo desde una variable de entorno:
```python
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)
```
Agrega `SECRET_KEY` en Render (*Environment*). Como el secreto viejo **sigue en el historial de
Git**, considéralo comprometido: genera uno nuevo y agrega la *Fingerprint* que muestra
Gitleaks al archivo `.gitleaksignore`.

**3. Modo debug**:
```python
app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
```

**4. Dependencias vulnerables** (`requirements.txt`):
```
Flask==3.1.3
Werkzeug==3.1.9
Jinja2==3.1.6
gunicorn==27.0.0
```
(Si OSV-Scanner sigue reportando algo, sube a la última versión que indique en la columna *Fixed Version*.)

**5. Paquetes del sistema operativo en la imagen** (Grype detecta, por ejemplo, `zlib1g`
vulnerable en la imagen base de Debian) — actualízalos en el `Dockerfile`, justo después de `WORKDIR /app`:
```dockerfile
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
```

Haz `push` otra vez: todos los escáneres pasan ✅ → la app se despliega en Render → Nuclei la escanea.
