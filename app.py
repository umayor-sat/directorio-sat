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
# ESCUELAS
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
        .select("*")
        .or_(f"nombre.ilike.%{q}%,cargo.ilike.%{q}%,escuela_busqueda.ilike.%{q}%")
    )
    if sede:
        query = query.ilike("sede", f"%{sede}%")
    result = query.execute()
    return jsonify(result.data or [])

# =========================
# ACADÉMICOS
# =========================
@app.route("/academicos")
def academicos():
    return render_template("academicos.html")

@app.route("/api/academicos")
def api_academicos():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])
    try:
        query = (
            supabase
            .table("otros_contactos_academicos")
            .select("*")
            .ilike("departamento_busqueda", f"%{q}%")
        )
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    query = (
        supabase
        .table("contactos_administrativos")
        .select("*")
        .ilike("area_busqueda", q)
    )
    result = query.execute()
    return jsonify(result.data or [])

# =========================
# BITÁCORA
# =========================
@app.route("/bitacora")
def bitacora():
    return render_template("bitacora.html")

# =========================
# EJECUCIÓN
# =========================
import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
