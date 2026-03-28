from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
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
# DECORADOR DE SEGURIDAD
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("username"):
            # Si es una petición API, devolver JSON de error
            if request.path.startswith('/api/'):
                return jsonify({"error": "No autorizado"}), 401
            # Si es una página web, redirigir al login
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =========================
# LOGIN UNIFICADO (REAL BD)
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        checkbox = request.form.get('terminos')

        # 1. Validación del checkbox
        if not checkbox or checkbox != 'on':
            return render_template('login.html', error="Es obligatorio aceptar la declaración de responsabilidad.")

        try:
            # 2. Consultar a Supabase si existe el usuario
            response = supabase.table('ejecutivos').select('*').eq('login_user', username).execute()
            usuarios = response.data

            # 3. Si el usuario no existe en la BD
            if not usuarios:
                return render_template('login.html', error="Usuario o contraseña incorrectos.")

            usuario = usuarios[0]

            # 4. Verificar si la cuenta está inactiva (Checkbox "Activo" en Administración)
            if not usuario.get('activo'):
                return render_template('login.html', error="Su cuenta está inactiva. Contacte al administrador.")

            # 5. Verificar la contraseña
            if usuario.get('login_password') == password:
                # ¡ÉXITO! Guardamos los datos del ejecutivo en la sesión
                session['username'] = usuario.get('login_user')
                session['nombre'] = usuario.get('nombre')
                session['rol'] = usuario.get('rol') # apoyo, staff, supervisor
                session['nivel_acceso'] = usuario.get('nivel_acceso') # usuario, admin
                
                # Regla de oro para Reportería y Administración:
                # Si en el panel le pusiste nivel "admin", forzamos el rol a admin para 
                # que Jinja y Python le den paso libre a todas las pantallas.
                if session['nivel_acceso'] == 'admin':
                    session['rol'] = 'admin'

                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Usuario o contraseña incorrectos.")

        except Exception as e:
            print(f"Error BD Login: {e}")
            return render_template('login.html', error="Error de conexión con el servidor.")

    return render_template('login.html')

# =========================
# LOGOUT DEL PORTAL
# =========================
@app.route("/logout")
def logout():
    session.clear() # Borramos todos los datos de sesión por seguridad
    return redirect(url_for('login'))

# =========================
# HOME
# =========================
@app.route("/")
@login_required
def home():
    return render_template("home.html")

# =========================
# ESCUELAS
# =========================
@app.route("/escuelas")
@login_required
def escuelas():
    return render_template("escuelas.html")

@app.route("/api/escuelas")
@login_required
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
@login_required
def academicos():
    return render_template("academicos.html")

@app.route("/api/academicos")
@login_required
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
@login_required
def contactos_administrativos():
    return render_template("contactos_administrativos.html")

@app.route("/api/contactos-administrativos")
@login_required
def api_contactos_administrativos():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    try:
        query = (
            supabase
            .table("contactos_administrativos")
            .select("*")
            .ilike("area_busqueda", q)
        )
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# BITÁCORA
# =========================
@app.route("/bitacora")
@login_required
def bitacora():
    return render_template("bitacora.html")

@app.route("/api/bitacora")
@login_required
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
@login_required
def temas_crm():
    return render_template("temas_crm.html")

# =========================
# PAUTA PMCC
# =========================
@app.route("/pauta-pmcc")
@login_required
def pauta_pmcc():
    return render_template("pmcc.html")

# =========================
# CORREOS FRECUENTES
# =========================
@app.route("/correos-frecuentes")
@login_required
def correos_frecuentes():
    return render_template("correos_frecuentes.html")

# =========================
# SOPORTE SAT
# =========================
@app.route("/soporte")
@login_required
def soporte():
    return render_template("soporte.html")

# =========================
# MONITOR DE CALIDAD
# =========================
@app.route("/monitor-calidad")
@login_required
def monitor_calidad():
    return render_template("monitor_calidad.html")

# ==========================================================
# REPORTERÍA SAT (DASHBOARD EJECUTIVO)
# ==========================================================
@app.route('/reporteria-sat')
@login_required
def reporteria_sat():
    return render_template('reporteria_sat.html')

# =========================
# ADMINISTRACION
# =========================
@app.route('/administracion')
@login_required
def administracion():
    # Validamos que solo los administradores o supervisores puedan ver esta vista 
    if session.get('nivel_acceso') != 'admin' and session.get('rol') not in ['admin', 'supervisor']:
        return redirect(url_for('home'))
    return render_template('administracion.html')

# =========================
# EJECUCIÓN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
