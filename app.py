from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "banco_secreto_2026")

def get_connection():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        result = urlparse(database_url)
        return psycopg2.connect(
            host=result.hostname,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            port=result.port
        )
    else:
        return psycopg2.connect(
            host="localhost",
            database="bbanco_r",
            user="postgres",
            password="a123"
        )
    
@app.route('/nueva_solicitud_credito', methods=['GET', 'POST'])
def nueva_solicitud_credito():
    if 'rol' not in session or session['rol'].lower() != 'colaborador':
        return redirect(url_for('inicio'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        idcliente = request.form['idcliente']
        monto = request.form['monto']
        plazo = request.form['plazo']

        cur.execute("""
            INSERT INTO tbsolicitudcredit (idcliente, fechasolicitud, montosolicitado, plazomeses, estadosolicitud)
            VALUES (%s, CURRENT_DATE, %s, %s, 'Pendiente')
        """, (idcliente, monto, plazo))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('colaborador'))

    cur.execute("""
        SELECT idcliente, primernombre, primerapellido
        FROM tbcliente
        ORDER BY primernombre, primerapellido
    """)
    clientes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('new_credit.html', clientes=clientes)


@app.route('/nueva_solicitud_cuenta', methods=['GET', 'POST'])
def nueva_solicitud_cuenta():
    if 'rol' not in session or session['rol'].lower() != 'colaborador':
        return redirect(url_for('inicio'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        idcliente = request.form['idcliente']
        tipo = request.form['tipo']

        cur.execute("""
            INSERT INTO tbsolicitudacc (idcliente, fechasolicitud, tipocuenta, estadosolicitud)
            VALUES (%s, CURRENT_DATE, %s, 'Pendiente')
        """, (idcliente, tipo))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('colaborador'))

    cur.execute("""
        SELECT idcliente, primernombre, primerapellido
        FROM tbcliente
        ORDER BY primernombre, primerapellido
    """)
    clientes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('new_acc.html', clientes=clientes)

@app.route('/')
def inicio():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    nombre_usuario = request.form['nombreUsuario']
    contrasena = request.form['contrasena']

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT u.idusuario, u.nombreusuario, u.contrasena, u.estado, 
               r.nombrerol, u.idcliente
        FROM tbusuario u
        INNER JOIN tbrol r ON u.idrol = r.idrol
        WHERE u.nombreusuario = %s AND u.contrasena = %s AND u.estado = TRUE
    """
    cur.execute(query, (nombre_usuario, contrasena))
    usuario = cur.fetchone()

    cur.close()
    conn.close()

    if usuario:
        session['idusuario'] = usuario[0]
        session['nombreusuario'] = usuario[1]
        session['rol'] = usuario[4]
        session['idcliente'] = usuario[5]

        if usuario[4].lower() == 'cliente':
            return redirect(url_for('cliente'))
        elif usuario[4].lower() == 'colaborador':
            return redirect(url_for('colaborador'))
    else:
        return render_template('login.html', error="Usuario o contraseña incorrectos")

@app.route('/cliente')
def cliente():
    if 'rol' not in session or session['rol'].lower() != 'cliente':
        return redirect(url_for('inicio'))

    idcliente = session['idcliente']
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT primernombre, primerapellido
        FROM tbcliente
        WHERE idcliente = %s
    """, (idcliente,))
    cliente_data = cur.fetchone()

    cur.execute("""
        SELECT numerocuenta, tipocuenta, saldo, estadocuenta, fechaapertura
        FROM tbcuenta
        WHERE idcliente = %s
        ORDER BY idcuenta
    """, (idcliente,))
    cuentas = cur.fetchall()

    cur.execute("""
        SELECT tipoobligacion, descripcion, montooriginal, saldopendiente, 
               fechainicio, fechavencimiento, estadoobligacion
        FROM tbobligacion
        WHERE idcliente = %s
        ORDER BY idobligacion
    """, (idcliente,))
    obligaciones = cur.fetchall()

    cur.execute("""
        SELECT p.fechapago, p.fechavencimiento, p.montopago, p.estadopago, o.tipoobligacion
        FROM tbpago p
        INNER JOIN tbobligacion o ON p.idobligacion = o.idobligacion
        WHERE o.idcliente = %s
        ORDER BY p.fechavencimiento
    """, (idcliente,))
    pagos = cur.fetchall()

    cur.execute("""
        SELECT fechasolicitud, tipocuenta, estadosolicitud
        FROM tbsolicitudacc
        WHERE idcliente = %s
        ORDER BY idsolicitudacc DESC
    """, (idcliente,))
    solicitudes_cuenta = cur.fetchall()

    cur.execute("""
        SELECT fechasolicitud, montosolicitado, plazomeses, estadosolicitud
        FROM tbsolicitudcredit
        WHERE idcliente = %s
        ORDER BY idsolicitudcredit DESC
    """, (idcliente,))
    solicitudes_credito = cur.fetchall()

    cur.close()
    conn.close()

    nombre_completo = f"{cliente_data[0]} {cliente_data[1]}" if cliente_data else session['nombreusuario']

    return render_template(
        'client.html',
        nombre_completo=nombre_completo,
        cuentas=cuentas,
        obligaciones=obligaciones,
        pagos=pagos,
        solicitudes_cuenta=solicitudes_cuenta,
        solicitudes_credito=solicitudes_credito
    )

@app.route('/colaborador')
def colaborador():
    if 'rol' not in session or session['rol'].lower() != 'colaborador':
        return redirect(url_for('inicio'))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.primernombre, c.primerapellido, o.tipoobligacion,
               p.fechavencimiento, p.montopago, p.estadopago
        FROM tbpago p
        INNER JOIN tbobligacion o ON p.idobligacion = o.idobligacion
        INNER JOIN tbcliente c ON o.idcliente = c.idcliente
        WHERE p.estadopago IN ('Pendiente', 'Por vencer')
        ORDER BY p.fechavencimiento
    """)
    pagos_por_vencer = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'collab.html',
        nombreusuario=session['nombreusuario'],
        pagos_por_vencer=pagos_por_vencer
    )

@app.route('/buscar_cliente', methods=['GET', 'POST'])
def buscar_cliente():
    if 'rol' not in session or session['rol'].lower() != 'colaborador':
        return redirect(url_for('inicio'))

    resultado_cliente = None
    cuentas = []
    obligaciones = []

    if request.method == 'POST':
        texto_busqueda = request.form['texto_busqueda'].strip()

        conn = get_connection()
        cur = conn.cursor()

        # Buscar por nombre, apellido o nombre completo
        cur.execute("""
            SELECT idcliente, primernombre, primerapellido
            FROM tbcliente
            WHERE primernombre ILIKE %s
               OR primerapellido ILIKE %s
               OR (primernombre || ' ' || primerapellido) ILIKE %s
            ORDER BY primernombre, primerapellido
            LIMIT 1
        """, (f"%{texto_busqueda}%", f"%{texto_busqueda}%", f"%{texto_busqueda}%"))

        resultado_cliente = cur.fetchone()

        if resultado_cliente:
            idcliente = resultado_cliente[0]

            # Cuentas del cliente
            cur.execute("""
                SELECT numerocuenta, tipocuenta, saldo, estadocuenta
                FROM tbcuenta
                WHERE idcliente = %s
                ORDER BY idcuenta
            """, (idcliente,))
            cuentas = cur.fetchall()

            # Obligaciones del cliente
            cur.execute("""
                SELECT tipoobligacion, descripcion, saldopendiente, estadoobligacion
                FROM tbobligacion
                WHERE idcliente = %s
                ORDER BY idobligacion
            """, (idcliente,))
            obligaciones = cur.fetchall()

        cur.close()
        conn.close()

    return render_template(
        'search_client.html',
        resultado_cliente=resultado_cliente,
        cuentas=cuentas,
        obligaciones=obligaciones
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)