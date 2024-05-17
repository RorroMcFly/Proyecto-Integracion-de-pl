from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from .database.db_functions import *

routes_bp = Blueprint('routes', __name__)


@routes_bp.route('/crear-usuario', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"msg": "username y password son requeridos"}), 400

    # Obtiene la cadena de conexión de la configuración actual de la app
    connection_string = current_app.config['CONNECTION_STRING']

    # Llama a la función para crear el usuario en la base de datos
    if crear_usuario_db(connection_string, username, password):
        return jsonify({"msg": "Usuario creado exitosamente"}), 201
    else:
        return jsonify({"msg": "Error al crear usuario"}), 500

@routes_bp.route('/cambiar-rol', methods=['PUT'])
@jwt_required()
def cambiar_rol():
    data = request.get_json()
    username_para_cambiar = data.get('username')  # Cambio aquí para usar "username"
    nuevo_id_rol = data.get('nuevoIDRol')

    usuario_logueado = get_jwt_identity()  # Usuario que está realizando la acción
    if not es_administrador(current_app.config['CONNECTION_STRING'], usuario_logueado):
        return jsonify({"error": "Acción no autorizada, se requiere ser administrador"}), 403

    if cambiar_rol_usuario(current_app.config['CONNECTION_STRING'], username_para_cambiar, nuevo_id_rol):
        return jsonify({"mensaje": "Rol actualizado exitosamente"}), 200
    else:
        return jsonify({"error": "Error al actualizar el rol"}), 500


@routes_bp.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({"msg": "Faltan credenciales"}), 401
    
    connection_string = current_app.config['CONNECTION_STRING']
    
    if verify_user(connection_string, auth.username, auth.password):
        access_token = create_access_token(identity=auth.username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Nombre de usuario o contraseña incorrectos"}), 401

@routes_bp.route('/productos', methods=['GET'])
def get_productos():
    connection_string = current_app.config['CONNECTION_STRING']
    productos = get_product_info(connection_string)
    return jsonify(productos), 200

@routes_bp.route('/productos/comprar', methods=['POST'])
@jwt_required()
def comprar_producto():
    data = request.get_json()
    codigo_producto = data.get('codigo')
    cantidad = data.get('cantidad')
    if not codigo_producto or not cantidad:
        return jsonify({"msg": "Se requiere el código del producto y la cantidad"}), 400
    
    connection_string = current_app.config['CONNECTION_STRING']
    producto_original = obtener_info_producto(connection_string, codigo_producto)
    if not producto_original:
        return jsonify({"msg": "El producto no existe"}), 404

    if cantidad > producto_original['Cantidad']:
        return jsonify({"msg": f"No hay suficiente stock del producto {producto_original['Nombre']}"})
    
    if actualizar_cantidad_producto(connection_string, codigo_producto, cantidad):
        producto_comprado = {
            "Código del producto": codigo_producto,
            "Nombre": producto_original["Nombre"],
            "Cantidad comprada": cantidad
        }
        return jsonify({"msg": "Compra realizada exitosamente", "producto_comprado": producto_comprado}), 200
    else:
        return jsonify({"msg": "No se pudo completar la compra"}), 400

@routes_bp.route('/carrito/agregar', methods=['POST'])
@jwt_required()
def agregar_al_carrito():
    data = request.get_json()
    codigo = data.get('codigo')
    cantidad = data.get('cantidad')
    username = get_jwt_identity()
    
    if not codigo or not cantidad:
        return jsonify({"msg": "Se requiere el código del producto y la cantidad para agregarlo al carrito"}), 400
    
    connection_string = current_app.config['CONNECTION_STRING']
    
    # Obtener el precio del producto desde la base de datos
    precio_unitario = obtener_precio_producto(connection_string, codigo)
    if precio_unitario is None:
        return jsonify({"msg": "No se encontró el precio del producto en la base de datos"}), 404
    
    agregar_producto_al_carrito(connection_string, codigo, cantidad, precio_unitario, username)
    
    return jsonify({"msg": "Producto agregado al carrito exitosamente"}), 200

@routes_bp.route('/carrito/contenido', methods=['GET'])
@jwt_required()
def obtener_contenido_del_carrito():
    username = get_jwt_identity()
    if not username:
        return jsonify({"msg": "Usuario no encontrado en el token"}), 400

    try:
        connection_string = current_app.config['CONNECTION_STRING']
    except KeyError:
        return jsonify({"msg": "Error al acceder a la configuración de la aplicación"}), 500

    contenido_carrito = obtener_contenido_carrito(connection_string, username)

    if contenido_carrito is not None:
        return jsonify(contenido_carrito), 200
    else:
        return jsonify({"msg": "No se encontró contenido para el carrito del usuario"}), 404
    

def crear_factura(connection_string, usuario_id, detalles):
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    try:
        # Calcula el total de la factura sumando el total de cada producto en el carrito
        total = sum(item['Cantidad'] * item['PrecioUnitario'] for item in detalles)
        
        # Inserta la factura en la tabla Factura
        cursor.execute("""
            INSERT INTO Factura (UsuarioId, Total, FechaCreacion)
            VALUES (?, ?, GETDATE())
            """, (usuario_id, total))
        factura_id = cursor.execute("SELECT @@IDENTITY AS 'Identity';").fetchval()
        
        # Inserta cada detalle de factura
        for item in detalles:
            cursor.execute("""
                INSERT INTO DetalleFactura (FacturaId, IdProducto, Cantidad, PrecioUnitario)
                VALUES (?, ?, ?, ?)
                """, (factura_id, item['IdProducto'], item['Cantidad'], item['PrecioUnitario']))
            
            # Actualiza el stock de los productos
            cursor.execute("""
                UPDATE Producto
                SET Cantidad = Cantidad - ?
                WHERE IdProducto = ?
                """, (item['Cantidad'], item['IdProducto']))
        
        # Limpia el carrito
        cursor.execute("DELETE FROM Producto_Carrito WHERE UserId = ?", usuario_id)

        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear la factura: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


@routes_bp.route('/comprar', methods=['POST'])
@jwt_required()
def comprar():
    username = get_jwt_identity()
    connection_string = current_app.config['CONNECTION_STRING']
    user_id = obtener_id_usuario(connection_string, username)
    if not user_id:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    detalles = obtener_contenido_carrito(connection_string, username)
    if not detalles:
        return jsonify({"msg": "El carrito está vacío"}), 404

    if crear_factura(connection_string, user_id, detalles):
        return jsonify({"msg": "Compra realizada y factura creada exitosamente"}), 200
    else:
        return jsonify({"error": "Error al crear la factura"}), 500
    
    
@routes_bp.route('/reporte-mensual', methods=['POST'])
@jwt_required()
def reporte_mensual():
    username = get_jwt_identity()  # Obtiene el usuario autenticado
    data = request.get_json()
    mes = data.get('mes')
    año = data.get('año')

    if not mes or not año:
        return jsonify({"error": "Se requieren el mes y el año para generar el reporte"}), 400

    try:
        facturas = obtener_facturas_por_mes(current_app.config['CONNECTION_STRING'], username, mes, año)
        if isinstance(facturas, dict) and 'error' in facturas:
            return jsonify(facturas), facturas.get("error_code", 500)
        return jsonify({"facturas": facturas}), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener el reporte mensual", "mensaje": str(e)}), 500
    
@routes_bp.route("/productos/crear", methods=["POST"])
@jwt_required() 
def crear_producto_route():
    if request.method == "POST":
        data = request.get_json()
        codigo = data.get("codigo")
        marca = data.get("marca")
        nombre = data.get("nombre")
        precio = data.get("precio")
        cantidad = data.get("cantidad")

        if not codigo or not marca or not nombre or not precio or not cantidad:
            return jsonify({"msg": "Todos los campos son requeridos"}), 400

        crear_producto(codigo, marca, nombre, precio, cantidad)
        return jsonify({"msg": "Producto creado exitosamente"}), 201


@routes_bp.route("/productos/modificar", methods=["PUT"])
@jwt_required() 
def modificar_producto_route():
    if request.method == "PUT":
        data = request.get_json()
        codigo = data.get("codigo")
        nueva_marca = data.get("nueva_marca")
        nuevo_nombre = data.get("nuevo_nombre")
        nuevo_precio = data.get("nuevo_precio")
        nueva_cantidad = data.get("nueva_cantidad")

        if not codigo:
            return jsonify({"msg": "El código del producto es requerido"}), 400

        modificar_producto(codigo, nueva_marca, nuevo_nombre, nuevo_precio, nueva_cantidad)
        return jsonify({"msg": "Producto modificado exitosamente"}), 200


@routes_bp.route("/productos/eliminar", methods=["DELETE"])
@jwt_required() 
def eliminar_producto_route():
    if request.method == "DELETE":
        data = request.get_json()
        codigo = data.get("codigo")

        if not codigo:
            return jsonify({"msg": "El código del producto es requerido"}), 400

        eliminar_producto(codigo)
        return jsonify({"msg": "Producto eliminado exitosamente"}), 200