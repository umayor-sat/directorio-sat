from flask import Flask, render_template, request, jsonify, session
from supabase import create_client
import os
 
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "directorio-sat-clave-2026")
 
# =========================
# CONFIGURACIÓN SUPABASE
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jxmrznqppddabuqtbufq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_3Shj63dB3uBAL_TVvqfBRw_3RyTRZ1U")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
 
# =========================
# CONTRASEÑAS (desde entorno)
# =========================
PASSWORD_ADMIN    = os.environ.get("PASSWORD_ADMIN",    "SAT@UM2026")
PASSWORD_JEFATURA = os.environ.get("PASSWORD_JEFATURA", "SAT@UM2026")
 
# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/api/login-admin", methods=["POST"])
def login_admin():
    data = request.get_json(silent=True) or {}
    if data.get("password") == PASSWORD_ADMIN:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401
 
@app.route("/api/login-jefatura", methods=["POST"])
def login_jefatura():
    data = request.get_json(silent=True) or {}
    if data.get("password") == PASSWORD_JEFATURA:
        session["jefatura"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401
 
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})
 
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
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])
    try:
        query = (
            supabase
            .table("contactos_administrativos")
            .select("*")
            .or_(
                f"nombre.ilike.%{q}%,"
                f"cargo_rol.ilike.%{q}%,"
                f"area.ilike.%{q}%,"
                f"area_busqueda.ilike.%{q}%"
            )
        )
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
# =========================
# BITÁCORA
# =========================
@app.route("/bitacora")
def bitacora():
    return render_template("bitacora.html")
 
@app.route("/api/bitacora")
def api_bitacora():
    anio = request.args.get("anio", "").strip()
    mes  = request.args.get("mes",  "").strip()
    q    = request.args.get("q",    "").strip()
    try:
        query = supabase.table("Bitacora").select("*").order("fecha", desc=True)
        if anio and mes:
            query = query.gte("fecha", f"{anio}-{mes}-01").lte("fecha", f"{anio}-{mes}-31")
        elif anio:
            query = query.gte("fecha", f"{anio}-01-01").lte("fecha", f"{anio}-12-31")
        elif mes:
            query = query.filter("fecha", "like", f"%-{mes}-%")
        if q:
            query = query.ilike("evento", f"%{q}%")
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
# =========================
# ÁRBOL DE TEMAS CRM
# =========================
@app.route("/temas-crm")
def temas_crm():
    return render_template("temas_crm.html")
 
# =========================
# PAUTA PMCC
# =========================
@app.route("/pauta-pmcc")
def pauta_pmcc():
    return render_template("pmcc.html")
 
 # =========================
# CORREOS FRECUENTES
# =========================

@app.route("/correos-frecuentes")
def correos_frecuentes():
    return render_template("correos_frecuentes.html")

# =========================
# SOPORTE SAT
# =========================
@app.route("/soporte")
def soporte():
    return render_template("soporte.html")


# =========================
# EJECUCIÓN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
