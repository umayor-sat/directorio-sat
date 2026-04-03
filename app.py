from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from supabase import create_client
import os
from datetime import datetime, timezone, timedelta

# Manejo seguro de Zona Horaria (Hora de Chile)
try:
    from zoneinfo import ZoneInfo
    TZ_CHILE = ZoneInfo("America/Santiago")
except ImportError:
    TZ_CHILE = timezone(timedelta(hours=-3)) # Fallback seguro

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "directorio-sat-clave-2026")

# =========================
# CONFIGURACIÓN SUPABASE
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jxmrznqppddabuqtbufq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp4bXJ6bnFwcGRkYWJ1cXRidWZxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjU1MDgxNywiZXhwIjoyMDg4MTI2ODE3fQ.EopCzL9iTQ0ujKFWNi4aqVUhTDeYp4_0nt8wcdk67Mo")
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
# LOGIN UNIFICADO
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
            
            if not usuario.get('activo'):
                return render_template('login.html', error="Su cuenta está inactiva. Contacte al administrador.")

            if usuario.get('login_password') == password:
                rol_db = str(usuario.get('rol', '')).lower().strip()
                nivel_crudo = usuario.get('nivel_acceso') or usuario.get('nivel de acceso') or ''
                nivel_db = str(nivel_crudo).lower().strip()

                session['username'] = usuario.get('login_user')
                session['nombre'] = usuario.get('nombre')
                session['rol'] = rol_db 
                session['nivel_acceso'] = nivel_db 

                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Usuario o contraseña incorrectos.")

        except Exception as e:
            print(f"Error BD Login: {e}")
            return render_template('login.html', error="Error de conexión con el servidor.")

    return render_template('login.html')

@app.route("/logout")
def logout():
    nombre_completo = session.get('nombre', '')
    primer_nombre = nombre_completo.split()[0] if nombre_completo else 'Equipo'
    session.clear() 
    return render_template('logout.html', nombre=primer_nombre)

# =========================
# RUTAS DE NAVEGACIÓN
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
        res_exacto = supabase.table("contactos_administrativos").select("*").ieq("area_busqueda", q).execute()
        if res_exacto.data: return jsonify(res_exacto.data)
        res_flexible = supabase.table("contactos_administrativos").select("*").ilike("nombre", f"%{q}%").execute()
        return jsonify(res_flexible.data or [])
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
    if session.get('nivel_acceso') != 'admin': return redirect(url_for('home'))
    return render_template("monitor_calidad.html")

@app.route('/reporteria-sat')
@login_required
def reporteria_sat():
    if session.get('nivel_acceso') != 'admin': return redirect(url_for('home'))
    return render_template('reporteria_sat.html')

# ==========================================
# GESTIÓN DE ENLACES (LINKS)
# ==========================================
@app.route('/api/enlaces', methods=['GET'])
@login_required
def get_enlaces():
    try:
        res = supabase.table("LINKS").select("*").order("categoria").order("orden").execute()
        return jsonify(res.data)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/enlaces/nuevo', methods=['POST'])
@login_required
def nuevo_enlace():
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("LINKS").insert({
            "nombre_link": datos.get('nombre_link'),
            "url": datos.get('url'),
            "categoria": datos.get('categoria'),
            "orden": int(datos.get('orden', 0)),
            "icono": datos.get('icono', 'fa-link'),
            "activo": True
        }).execute()
        return jsonify({"status": "success", "data": res.data})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/enlaces/editar/<int:id>', methods=['PUT'])
@login_required
def editar_enlace(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("LINKS").update({
            "nombre_link": datos.get('nombre_link'),
            "url": datos.get('url'),
            "categoria": datos.get('categoria'),
            "orden": int(datos.get('orden', 0)),
            "icono": datos.get('icono', 'fa-link')
        }).eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/enlaces/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_enlace(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        link = supabase.table("LINKS").select("activo").eq("id", id).execute()
        if not link.data: return jsonify({"error": "No encontrado"}), 404
        nuevo_estado = not link.data[0].get('activo')
        
        supabase.table("LINKS").update({"activo": nuevo_estado}).eq("id", id).execute()
        return jsonify({"status": "success", "nuevo_estado": nuevo_estado})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/enlaces/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_enlace(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        supabase.table("LINKS").delete().eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

# ==========================================
# LÓGICA DE MENSAJES ROTATIVOS (CARRUSEL)
# ==========================================
@app.route('/api/mensajes-rotativos', methods=['GET'])
@login_required
def api_mensajes_rotativos():
    try:
        # 1. Cerebro de Calendario: Obtener la fecha de HOY en Chile
        hoy_chile = datetime.now(TZ_CHILE)
        hoy_ddmm = hoy_chile.strftime("%d-%m") # Formato chileno Ej: "18-09"
        hoy_mmdd = hoy_chile.strftime("%m-%d") # Formato inglés por si acaso Ej: "09-18"

        # 2. Traemos TODOS los mensajes de la BD
        res = supabase.table("mensajes_rotativos").select("*").execute()
        todos = res.data or []
        
        mensajes_finales = []
        for m in todos:
            # ¡AQUÍ ESTÁ LA MAGIA! Ahora busca la columna correcta "estado"
            es_activo = m.get("estado", False) 
            fecha_esp = str(m.get("fecha_mmdd", "")).strip()

            # LÓGICA DE PRIORIDAD: Si es hoy, gana prioridad cero.
            if fecha_esp == hoy_ddmm or fecha_esp == hoy_mmdd:
                m['prioridad_calculada'] = 0
                mensajes_finales.append(m)
            elif es_activo:  # Validación segura (sin el "is True" estricto)
                # Si está activo manualmente, mantiene su prioridad original o se va al final (999)
                m['prioridad_calculada'] = int(m.get("prioridad") or 999)
                mensajes_finales.append(m)
        
        # 3. Los ordenamos por la prioridad calculada (Los 0 van primero)
        mensajes_finales.sort(key=lambda x: x.get("prioridad_calculada", 999))
        
        return jsonify(mensajes_finales)
    except Exception as e:
        print(f"Error al cargar mensajes rotativos: {e}")
        return jsonify([])

# --- PUERTAS CRUD PARA EL ADMINISTRADOR (MENSAJES) ---
@app.route('/api/mensajes-rotativos/nuevo', methods=['POST'])
@login_required
def nuevo_mensaje():
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("mensajes_rotativos").insert({
            "mensaje": datos.get('mensaje'),
            "estado": datos.get('estado', False),  # Corregido de activo a estado
            "prioridad": datos.get('prioridad', 1),
            "categoria": datos.get('categoria'),
            "fecha_mmdd": datos.get('fecha_mmdd'),
            "duracion_min": datos.get('duracion_min', 15)
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/mensajes-rotativos/editar/<int:id>', methods=['PUT'])
@login_required
def editar_mensaje(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("mensajes_rotativos").update({
            "mensaje": datos.get('mensaje'),
            "estado": datos.get('estado', False),  # Corregido de activo a estado
            "prioridad": datos.get('prioridad', 1),
            "categoria": datos.get('categoria'),
            "fecha_mmdd": datos.get('fecha_mmdd')
        }).eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/mensajes-rotativos/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_mensaje(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("mensajes_rotativos").update({
            "estado": datos.get('estado'),  # Corregido de activo a estado
            "duracion_min": datos.get('duracion_min')
        }).eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/mensajes-rotativos/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_mensaje(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        supabase.table("mensajes_rotativos").delete().eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

# ==========================================
# LÓGICA DE ALERTAS OPERATIVAS (CATÁLOGO)
# ==========================================
@app.route('/api/alertas-operativas', methods=['GET'])
@login_required
def api_alertas_operativas():
    try:
        ahora_utc = datetime.now(timezone.utc)
        res = supabase.table("alertas_operativas").select("*").eq("estado", True).order("prioridad").execute()
        
        todas_activas = res.data or []
        alertas_finales = []
        mensaje_default = None

        for a in todas_activas:
            if a.get("es_default"):
                mensaje_default = a
                continue

            fin_str = a.get("fecha_hora_fin")

            if not fin_str:
                alertas_finales.append(a)
            else:
                try:
                    fecha_fin = datetime.fromisoformat(fin_str.replace('Z', '+00:00'))
                    if fecha_fin > ahora_utc:
                        alertas_finales.append(a)
                except Exception as ex:
                    print(f"Error parseando fecha de alerta: {ex}")
                    alertas_finales.append(a)

        if alertas_finales:
            return jsonify(alertas_finales)
        else:
            return jsonify([mensaje_default] if mensaje_default else [])
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- PUERTAS CRUD PARA EL ADMINISTRADOR (ALERTAS) ---
@app.route('/api/alertas-operativas/nuevo', methods=['POST'])
@login_required
def nueva_alerta():
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("alertas_operativas").insert({
            "categoria": datos.get('categoria'),
            "mensaje": datos.get('mensaje'),
            "color": datos.get('color', 'rojo'),
            "estado": False, 
            "es_default": False
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/alertas-operativas/editar/<int:id>', methods=['PUT'])
@login_required
def editar_alerta(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("alertas_operativas").update({
            "categoria": datos.get('categoria'),
            "mensaje": datos.get('mensaje'),
            "color": datos.get('color', 'rojo'),
            "estado": datos.get('estado', False)
        }).eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/alertas-operativas/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_alerta(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        datos = request.json
        res = supabase.table("alertas_operativas").update({
            "estado": datos.get('estado'),
            "fecha_hora_inicio": datos.get('fecha_hora_inicio'),
            "fecha_hora_fin": datos.get('fecha_hora_fin')
        }).eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/alertas-operativas/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_alerta(id):
    if session.get('nivel_acceso') != 'admin': return jsonify({"error": "No autorizado"}), 403
    try:
        supabase.table("alertas_operativas").delete().eq("id", id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

# ==========================================
# BUSCADOR UNIVERSAL
# ==========================================
def normalizar(texto):
    """Elimina tildes y convierte a minúsculas para búsqueda flexible."""
    reemplazos = {
        'á':'a','é':'e','í':'i','ó':'o','ú':'u',
        'ä':'a','ë':'e','ï':'i','ö':'o','ü':'u',
        'à':'a','è':'e','ì':'i','ò':'o','ù':'u',
        'â':'a','ê':'e','î':'i','ô':'o','û':'u',
        'ñ':'n'
    }
    t = texto.lower()
    for k, v in reemplazos.items():
        t = t.replace(k, v)
    return t

@app.route('/api/buscar-universal', methods=['GET'])
@login_required
def buscar_universal():
    q_raw = request.args.get('q', '').strip()
    q = q_raw.lower()
    q_norm = normalizar(q_raw)  # versión sin tildes para búsqueda flexible
    filtro = request.args.get('filtro', 'todo').strip().lower()
    sede_filtro = request.args.get('sede', '').strip().lower()  # filtro opcional de sede

    if len(q) < 2:
        return jsonify([])

    resultados = []

    try:
        # --- ESCUELAS ---
        if filtro in ('todo', 'escuelas'):
            # Búsqueda con tilde Y sin tilde para cubrir ambos casos
            res = supabase.table("directorio_escuelas_umayor").select("*").or_(
                f"nombre.ilike.%{q}%,"
                f"cargo.ilike.%{q}%,"
                f"escuela_busqueda.ilike.%{q}%,"
                f"secretaria.ilike.%{q}%,"
                f"sede.ilike.%{q}%,"
                f"nombre.ilike.%{q_norm}%,"
                f"escuela_busqueda.ilike.%{q_norm}%,"
                f"secretaria.ilike.%{q_norm}%"
            ).execute()

            filas = res.data or []

            # Deduplicar por si la búsqueda doble trae duplicados
            ids_vistos = set()
            filas_unicas = []
            for fila in filas:
                fid = fila.get('id')
                if fid not in ids_vistos:
                    ids_vistos.add(fid)
                    filas_unicas.append(fila)

            # Agrupamos por escuela_busqueda + sede para separar fichas por sede
            grupos = {}
            for fila in filas_unicas:
                escuela_key = (fila.get('escuela_busqueda') or fila.get('escuela') or 'sin_escuela').strip().lower()
                sede_key = (fila.get('sede') or 'sin_sede').strip().lower()
                clave = f"{escuela_key}||{sede_key}"
                if clave not in grupos:
                    grupos[clave] = []
                grupos[clave].append(fila)

            for clave, contactos in grupos.items():
                primero = contactos[0]
                sede_ficha = (primero.get('sede') or '').strip().lower()

                # Aplicar filtro de sede si viene del frontend
                if sede_filtro and sede_filtro not in ('todo', '') and sede_filtro not in sede_ficha:
                    continue

                restriccion = primero.get('consultar_antes_de_entregar_contactos') or ''

                # Titulo legible por ficha
                titulo_legible = ''
                for c in contactos:
                    t = (c.get('escuela') or '').strip()
                    if t and t.lower() not in ('no informado', '') and len(t) > 2:
                        titulo_legible = t
                        break
                if not titulo_legible:
                    titulo_legible = clave.split('||')[0]

                ficha = {
                    'tipo': 'Escuela',
                    'titulo': titulo_legible,
                    'sede': primero.get('sede') or '',
                    'campus': primero.get('campus') or '',
                    'restriccion': restriccion,
                    'contactos': []
                }

                for c in contactos:
                    # Persona principal (director, coordinador, etc.)
                    nombre = (c.get('nombre') or '').strip()
                    cargo  = (c.get('cargo') or '').strip()
                    correo = (c.get('correo_director') or '').strip()
                    anexo  = (c.get('anexo_director') or '').strip()

                    if nombre and nombre.lower() not in ('no informado', ''):
                        ficha['contactos'].append({
                            'nombre': nombre,
                            'cargo': cargo,
                            'correo': correo if correo.lower() != 'no informado' else '',
                            'anexo': anexo if anexo.lower() != 'no informado' else '',
                            'rol': 'director'
                        })

                    # Secretaria
                    sec_nombre = (c.get('secretaria') or '').strip()
                    sec_correo = (c.get('correo_secretaria') or '').strip()
                    sec_anexo  = (c.get('anexo_secretaria') or '').strip()

                    if sec_nombre and sec_nombre.lower() not in ('no informado', ''):
                        # Evitar duplicar secretarias que aparecen en múltiples filas
                        ya_existe = any(
                            ct['nombre'].lower() == sec_nombre.lower() and ct['rol'] == 'secretaria'
                            for ct in ficha['contactos']
                        )
                        if not ya_existe:
                            ficha['contactos'].append({
                                'nombre': sec_nombre,
                                'cargo': 'Secretaria',
                                'correo': sec_correo if sec_correo.lower() != 'no informado' else '',
                                'anexo': sec_anexo if sec_anexo.lower() != 'no informado' else '',
                                'rol': 'secretaria'
                            })

                resultados.append(ficha)

        # --- ACADÉMICOS (otros_contactos_academicos) ---
        if filtro in ('todo', 'academicos'):
            res = supabase.table("otros_contactos_academicos").select("*").or_(
                f"nombre.ilike.%{q}%,"
                f"departamento_busqueda.ilike.%{q}%,"
                f"nombre_busqueda.ilike.%{q}%,"
                f"cargo.ilike.%{q}%,"
                f"nombre.ilike.%{q_norm}%,"
                f"departamento_busqueda.ilike.%{q_norm}%,"
                f"nombre_busqueda.ilike.%{q_norm}%"
            ).execute()

            for r in (res.data or []):
                restriccion = r.get('consultar_antes_de_entregar_contactos') or ''
                contactos = []

                nombre = (r.get('nombre') or '').strip()
                cargo  = (r.get('cargo') or '').strip()
                correo = (r.get('correo_director') or '').strip()
                anexo  = str(r.get('anexo director') or '').strip()

                if nombre and nombre.lower() != 'no informado':
                    contactos.append({
                        'nombre': nombre,
                        'cargo': cargo,
                        'correo': correo if correo.lower() != 'no informado' else '',
                        'anexo': anexo if anexo.lower() != 'no informado' else '',
                        'rol': 'director'
                    })

                sec_nombre = (r.get('secretaria_nombre') or '').strip()
                sec_correo = (r.get('secretaria_correo') or '').strip()
                sec_anexo  = str(r.get('secretaria_anexo') or '').strip()

                if sec_nombre and sec_nombre.lower() not in ('no informado', ''):
                    contactos.append({
                        'nombre': sec_nombre,
                        'cargo': 'Secretaria',
                        'correo': sec_correo if sec_correo.lower() != 'no informado' else '',
                        'anexo': sec_anexo if sec_anexo.lower() != 'no informado' else '',
                        'rol': 'secretaria'
                    })

                resultados.append({
                    'tipo': 'Académico',
                    'titulo': r.get('departamento') or r.get('departamento_busqueda') or '',
                    'sede': r.get('sede') or '',
                    'campus': '',
                    'restriccion': restriccion,
                    'contactos': contactos
                })

        # --- ADMINISTRATIVOS ---
        if filtro in ('todo', 'administrativos'):
            res = supabase.table("contactos_administrativos").select("*").or_(
                f"nombre.ilike.%{q}%,"
                f"area_busqueda.ilike.%{q}%,"
                f"nombre.ilike.%{q_norm}%,"
                f"area_busqueda.ilike.%{q_norm}%"
            ).execute()

            for r in (res.data or []):
                restriccion = r.get('consultar_antes_de_entregar_contactos') or ''
                contactos = []

                nombre = (r.get('nombre') or '').strip()
                cargo  = (r.get('cargo') or '').strip()
                correo = (r.get('correo') or '').strip()
                anexo  = str(r.get('anexo') or '').strip()

                if nombre and nombre.lower() != 'no informado':
                    contactos.append({
                        'nombre': nombre,
                        'cargo': cargo,
                        'correo': correo if correo.lower() != 'no informado' else '',
                        'anexo': anexo if anexo.lower() != 'no informado' else '',
                        'rol': 'contacto'
                    })

                resultados.append({
                    'tipo': 'Administrativo',
                    'titulo': r.get('area') or r.get('area_busqueda') or '',
                    'sede': r.get('sede') or '',
                    'campus': '',
                    'restriccion': restriccion,
                    'contactos': contactos
                })

        return jsonify(resultados)

    except Exception as e:
        print(f"Error buscar-universal: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# RUTAS DE ADMINISTRACIÓN
# ==========================================
@app.route('/administracion')
@login_required
def administracion():
    if session.get('nivel_acceso') != 'admin': return redirect(url_for('home'))
    return render_template('administracion.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
