"""
Biblioteca Virtual - App de ejemplo para escaneo de vulnerabilidades.

ATENCION: esta version contiene vulnerabilidades INTENCIONALES (marcadas con
"VULN") para demostrar como las detectan Bandit, Gitleaks, OSV-Scanner y Grype.
Ver README.md -> "Corrigiendo las vulnerabilidades".
"""
import os
import sqlite3

from flask import Flask, g, redirect, render_template, request, url_for, flash

app = Flask(__name__)

# VULN 1 (Gitleaks / Bandit B105): secreto escrito directamente en el codigo
SECRET_KEY = "9fK2xLq8Zr4TmW7pVn3YdH6sJc1Ae5UbQ0wE"
app.config["SECRET_KEY"] = SECRET_KEY

DATABASE = os.environ.get("DATABASE_PATH", "biblioteca.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            anio INTEGER,
            genero TEXT,
            disponible INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    if db.execute("SELECT COUNT(*) FROM libros").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO libros (titulo, autor, anio, genero) VALUES (?, ?, ?, ?)",
            [
                ("Cien años de soledad", "Gabriel García Márquez", 1967, "Novela"),
                ("La ciudad y los perros", "Mario Vargas Llosa", 1963, "Novela"),
                ("Los ríos profundos", "José María Arguedas", 1958, "Novela"),
                ("Clean Code", "Robert C. Martin", 2008, "Programación"),
                ("El principito", "Antoine de Saint-Exupéry", 1943, "Fábula"),
            ],
        )
    db.commit()
    db.close()


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        # VULN 2 (Bandit B608): SQL Injection por concatenar la entrada del usuario
        sql = f"SELECT * FROM libros WHERE titulo LIKE '%{q}%' OR autor LIKE '%{q}%' ORDER BY titulo"
        libros = db.execute(sql).fetchall()
    else:
        libros = db.execute("SELECT * FROM libros ORDER BY titulo").fetchall()
    return render_template("index.html", libros=libros, q=q)


@app.route("/libro/nuevo", methods=["GET", "POST"])
def nuevo_libro():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        anio = request.form.get("anio") or None
        genero = request.form.get("genero", "").strip()
        if not titulo or not autor:
            flash("El título y el autor son obligatorios.", "error")
            return render_template("form.html", libro=request.form, accion="Registrar")
        db = get_db()
        db.execute(
            "INSERT INTO libros (titulo, autor, anio, genero) VALUES (?, ?, ?, ?)",
            (titulo, autor, anio, genero),
        )
        db.commit()
        flash("Libro registrado correctamente.", "ok")
        return redirect(url_for("index"))
    return render_template("form.html", libro={}, accion="Registrar")


@app.route("/libro/<int:libro_id>/editar", methods=["GET", "POST"])
def editar_libro(libro_id):
    db = get_db()
    libro = db.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
    if libro is None:
        flash("Libro no encontrado.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        anio = request.form.get("anio") or None
        genero = request.form.get("genero", "").strip()
        if not titulo or not autor:
            flash("El título y el autor son obligatorios.", "error")
            return render_template("form.html", libro=request.form, accion="Guardar")
        db.execute(
            "UPDATE libros SET titulo = ?, autor = ?, anio = ?, genero = ? WHERE id = ?",
            (titulo, autor, anio, genero, libro_id),
        )
        db.commit()
        flash("Libro actualizado.", "ok")
        return redirect(url_for("index"))
    return render_template("form.html", libro=libro, accion="Guardar")


@app.route("/libro/<int:libro_id>/prestamo", methods=["POST"])
def cambiar_prestamo(libro_id):
    db = get_db()
    db.execute(
        "UPDATE libros SET disponible = 1 - disponible WHERE id = ?", (libro_id,)
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/libro/<int:libro_id>/eliminar", methods=["POST"])
def eliminar_libro(libro_id):
    db = get_db()
    db.execute("DELETE FROM libros WHERE id = ?", (libro_id,))
    db.commit()
    flash("Libro eliminado.", "ok")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}


init_db()

if __name__ == "__main__":
    # VULN 3 (Bandit B201): modo debug activo y expuesto en todas las interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
