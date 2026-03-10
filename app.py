from flask import Flask, render_template, request, jsonify
from supabase import create_client

app = Flask(__name__)

# =========================
# CONFIGURACIÓN SUPABASE
# =========================
SUPABASE_URL = "https://jxmrznqppddabuqtbufq.supabase.co"
SUPABASE_KEY = "sb_publishable_3Shj63dB3uBAL_TVvqfBRw_3RyTRZ1U"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return render_template("home.html")

# =========================
# ESCUELAS (NO SE TOCA)
# =========================
@app.route("/escuelas")
def escuelas():
    return render_template("escuelas.html")

@app.route("/api/escuelas")
def api_escuelas():
    q = request.args.get("q", "").strip().lower()
    sede = request.args.get("sede", "").strip().lower()
    if len(q) < 2:
        return jsonify([])
    query = (
        supabase
        .table("directorio_escuelas_umayor")
        .select("""
            nombre,
            cargo,
            correo_director,
            secretaria,
            correo_secretaria,
            escuela_busqueda,
            sede,
            campus,
            anexo_director,
            anexo_secretaria,
            consultar_antes_de_entregar_contactos
        """)
        .or_(f"nombre.ilike.%{q}%,cargo.ilike.%{q}%,escuela_busqueda.ilike.%{q}%")
    )
    if sede:
        query = query.ilike("sede", f"%{sede}%")
    result = query.execute()
    return jsonify(result.data or [])

# =========================
# ACADÉMICOS (FUNCIONAL)
# =========================
@app.route("/academicos")
def academicos():
    return render_template("academicos.html")

@app.route("/api/academicos")
def api_academicos():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])
    query = (
        supabase
        .table("otros_contactos_academicos")
        .select("""
            nombre,
            cargo,
            departamento,
            correo_director,
            secretaria_nombre,
            secretaria_correo,
            anexo_director,
            anexo_secretaria,
            consultar_antes_de_entregar_contactos,
            sede
        """)
        .ilike("departamento_busqueda", f"%{q}%")
    )
    result = query.execute()
    return jsonify(result.data or [])

# =========================
# CONTACTOS ADMINISTRATIVOS
# =========================
@app.route("/contactos-administrativos")
def contactos_administrativos():
    return render_template("contactos_administrativos.html")

@app.route("/api/contactos-administrativos")
def api_contactos_administrativos():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    # ilike SIN wildcards = coincidencia exacta, insensible a mayúsculas
    # "ore" matchea "Ore", "ORE", "oRE" — pero NO "proveedores"
    query = (
        supabase
        .table("contactos_administrativos")
        .select("""
            nombre,
            cargo_rol,
            area,
            area_busqueda,
            campus,
            correo,
            anexo,
            observaciones,
            restricciones
        """)
        .ilike("area_busqueda", q)
    )
    result = query.execute()
    return jsonify(result.data or [])

# =========================
# EJECUCIÓN
# =========================
import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)








