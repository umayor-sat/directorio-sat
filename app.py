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
            if request.path.startswith('/api/'):
                return jsonify({"error": "No autorizado"}), 401
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

        if not checkbox or checkbox != 'on':
            return render_template('login.html', error="Es obligatorio aceptar la declaración de responsabilidad.")

        try:
            response = supabase.table('ejecutivos').select('*').eq('login_user', username).execute()
            usuarios = response.data

            if not usuarios:
                return render_template('login.html', error="Usuario o contraseña incorrectos.")

            usuario = usuarios[0]
            
            # --- EL "CHISMOSO" PARA LA CONSOLA DE RENDER ---
            print("========================================")
            print(f"DATOS LEÍDOS DE SUPABASE PARA: {username}")
            print(usuario) 
            print("========================================")

            if not usuario.get('activo'):
                return render_template('login.html', error="Su cuenta está inactiva. Contacte al administrador.")

            if usuario.get('login_password') == password:
                
                # Buscamos el rol y lo pasamos a minúscula
                rol_db = str(usuario.get('rol', '')).lower().strip()
                
                # Buscamos el nivel de acceso en todas sus formas posibles y lo pasamos a minúscula
                nivel_crudo = usuario.get('nivel_acceso') or usuario.get('nivel de acceso') or usuario.get('Nivel_acceso') or usuario.get('Nivel de acceso') or ''
                nivel_db = str(nivel_crudo).lower().strip()

                session['username'] = usuario.get('login_user')
                session['nombre'] = usuario.get('nombre')
                session['rol'] = rol_db 
                session['nivel_acceso'] = nivel_db 

                # --- OTRO CHISMOSO PARA VER CÓMO QUEDÓ LA SESIÓN ---
                print(f"SESIÓN CREADA -> ROL: {session['rol']} | NIVEL: {session['nivel_acceso']}")

                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Usuario o contraseña incorrectos.")

        except Exception as e:
            print(f"Error BD Login: {e}")
            return render_template('login.html', error="Error de conexión con el servidor.")

    return render_template('login.html')

# =========================
# LOGOUT DEL PORTAL (ACTUALIZADO PARA DESPEDIDA HUMANA)
# =========================
@app.route("/logout")
def logout():
    # 1. Guardamos el nombre en el bolsillo antes de borrar todo
    nombre_completo = session.get('nombre', '')
    
    # 2. Extraemos solo el primer nombre (para que sea más cercano)
    primer_nombre = nombre_completo.split()[0] if nombre_completo else 'Equipo'
    
    # 3. Destruimos la sesión por seguridad
    session.clear() 
    
    # 4. Le enviamos el nombre a tu diseño de despedida
    return render_template('logout.html', nombre=primer_nombre)

# =========================
# HOME Y DEMÁS RUTAS
# =========================
@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/escuelas")
@login_required
def escuelas():
    return render_template("escuelas.html")

@app.route("/api/escuelas")
@login_required
def api_escuelas():
    q = request.args.get("q", "").strip().lower()
    sede = request.args.get("sede", "").strip().lower()
    if len(q) < 2: return jsonify([])
    query = supabase.table("directorio_escuelas_umayor").select("*").or_(f"nombre.ilike.%{q}%,cargo.ilike.%{q}%,escuela_busqueda.ilike.%{q}%")
    if sede: query = query.ilike("sede", f"%{sede}%")
    result = query.execute()
    return jsonify(result.data or [])

@app.route("/academicos")
@login_required
def academicos():
    return render_template("academicos.html")

@app.route("/api/academicos")
@login_required
def api_academicos():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2: return jsonify([])
    try:
        query = supabase.table("otros_contactos_academicos").select("*").ilike("departamento_busqueda", f"%{q}%")
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/contactos-administrativos")
@login_required
def contactos_administrativos():
    return render_template("contactos_administrativos.html")

@app.route("/api/contactos-administrativos")
@login_required
def api_contactos_administrativos():
    q = request.args.get("q", "").strip()
    if len(q) < 2: return jsonify([])
    try:
        query = supabase.table("contactos_administrativos").select("*").ilike("area_busqueda", q)
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e: return jsonify({"error": str(e)}), 500

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
        if anio and mes: query = query.gte("fecha", f"{anio}-{mes}-01").lte("fecha", f"{anio}-{mes}-31")
        elif anio: query = query.gte("fecha", f"{anio}-01-01").lte("fecha", f"{anio}-12-31")
        elif mes: query = query.filter("fecha", "like", f"%-{mes}-%")
        if q: query = query.ilike("evento", f"%{q}%")
        result = query.execute()
        return jsonify(result.data or [])
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/temas-crm")
@login_required
def temas_crm():
    return render_template("temas_crm.html")

@app.route("/pauta-pmcc")
@login_required
def pauta_pmcc():
    return render_template("pmcc.html")

@app.route("/correos-frecuentes")
@login_required
def correos_frecuentes():
    return render_template("correos_frecuentes.html")

@app.route("/soporte")
@login_required
def soporte():
    return render_template("soporte.html")

@app.route("/monitor-calidad")
@login_required
def monitor_calidad():
    if session.get('nivel_acceso') != 'admin':
        return redirect(url_for('home'))
    return render_template("monitor_calidad.html")

@app.route('/reporteria-sat')
@login_required
def reporteria_sat():
    if session.get('nivel_acceso') != 'admin':
        return redirect(url_for('home'))
    return render_template('reporteria_sat.html')

@app.route('/administracion')
@login_required
def administracion():
    if session.get('nivel_acceso') != 'admin':
        return redirect(url_for('home'))
    return render_template('administracion.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
