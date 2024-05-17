from flask import current_app, jsonify
import pyodbc

def get_db_connection(connection_string):
    return pyodbc.connect(connection_string)


def crear_usuario_db(connection_string, username, password):
    conn = pyodbc.connect(connection_string, autocommit=False)
    cursor = conn.cursor()
    try:
        cursor.execute("EXEC CrearUsuario @username=?, @password=?", (username, password))
        conn.commit()
        return True
    except Exception as e:
        print("Error al crear usuario:", e)
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
        
def es_administrador(connection_string, username):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    es_admin = cursor.execute("EXEC EsAdministrador @username=?", (username,)).fetchval()
    conn.close()
    return es_admin == 1


def cambiar_rol_usuario(connection_string, username, nuevo_id_rol):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    try:
        cursor.execute("EXEC CambiarRolUsuario @Username=?, @nuevoIDRol=?", (username, nuevo_id_rol))
        conn.commit()
        return True
    except Exception as e:
        print("Error al actualizar el rol:", e)
        conn.rollback()
        return False
    finally:
        conn.close()



def verify_user(connection_string, username, password):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    # Usamos la función HASHBYTES para comparar directamente la contraseña encriptada en la base de datos
    cursor.execute("SELECT 1 FROM Usuario WHERE Username = ? AND Password = HASHBYTES('SHA2_256', CONVERT(VARBINARY, ?))", (username, password))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    # Si result no es None, significa que la combinación de usuario y contraseña es correcta
    return bool(result)


def get_product_info(connection_string):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, marca, nombre, PrecioUnitario, cantidad FROM Producto")
    productos = []
    for row in cursor.fetchall():
        codigo, marca, nombre, precioUnitario, cantidad = row
        productos.append({
            "Código del producto": codigo,
            "Marca": marca,
            "Nombre": nombre,
            "PrecioUnitario": precioUnitario,
            "Cantidad": cantidad
        })
    cursor.close()
    conn.close()
    return productos

def actualizar_cantidad_producto(connection_string, codigo, cantidad):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()

    cursor.execute("SELECT Cantidad FROM Producto WHERE Codigo = ?", (codigo,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False
    
    cantidad_actual = row[0]
    nueva_cantidad = cantidad_actual - cantidad

    if nueva_cantidad >= 0:
        cursor.execute("UPDATE Producto SET Cantidad = ? WHERE Codigo = ?", (nueva_cantidad, codigo))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def obtener_info_producto(connection_string, codigo):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT Codigo, Marca, Nombre, PrecioUnitario, Cantidad FROM Producto WHERE Codigo = ?", (codigo,))
    producto = cursor.fetchone()
    conn.close()
    if producto:
        columns = ["Codigo", "Marca", "Nombre", "PrecioUnitario", "Cantidad"]
        producto_dict = dict(zip(columns, producto))
        return producto_dict
    else:
        return None

def obtener_id_usuario(connection_string, username):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT UserID FROM Usuario WHERE Username = ?", (username,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def agregar_producto_al_carrito(connection_string, codigo, cantidad, precio_unitario, username):
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    id_usuario = obtener_id_usuario(connection_string, username)
    id_producto = obtener_id_producto(connection_string, codigo)

    if id_usuario is None:
        conn.close()
        return jsonify({"msg": "Error: No se encontró el usuario"}), 404
    if id_producto is None:
        conn.close()
        return jsonify({"msg": "Error: No se encontró el producto"}), 404

    try:
        cursor.execute("INSERT INTO Producto_Carrito (UserId, IdProducto, Cantidad, PrecioUnitario, FechaCreacion) VALUES (?, ?, ?, ?, GETDATE())",
                       id_usuario,
                       id_producto,
                       cantidad,
                       precio_unitario)
        conn.commit()
        conn.close()
        return jsonify({"msg": "Producto agregado al carrito exitosamente"}), 200
    except pyodbc.Error as e:
        print("Error al agregar producto al carrito:", e)
        conn.rollback()
        conn.close()
        return jsonify({"msg": "Error al agregar producto al carrito"}), 500
    
def obtener_id_producto(connection_string, codigo):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT IdProducto FROM Producto WHERE Codigo = ?", (codigo,))
    producto_id = cursor.fetchone()
    conn.close()
    return producto_id[0] if producto_id else None

def obtener_precio_producto(connection_string, codigo):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT PrecioUnitario FROM Producto WHERE Codigo = ?", (codigo,))
        precio = cursor.fetchone()
        if precio:
            return precio[0]  # Devuelve el precio encontrado
        else:
            return None  # Si no se encuentra el precio, devuelve None
    except Exception as e:
        print("Error al obtener el precio del producto:", e)
        return None
    finally:
        if conn:
            conn.close()


def obtener_contenido_carrito(connection_string, username):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    
    UserId = obtener_id_usuario(connection_string, username)
    if UserId:
        cursor.execute("""
            SELECT pc.IdProducto, p.Codigo, p.Marca, p.Nombre, pc.Cantidad, pc.PrecioUnitario
            FROM Producto_Carrito pc
            INNER JOIN Producto p ON pc.IdProducto = p.IdProducto
            WHERE pc.UserId = ?  -- Use el campo correcto que identifica al usuario
        """, (UserId,))
        
        contenido_carrito = []
        for row in cursor.fetchall():
            id_producto, codigo, marca, nombre, cantidad, precio_unitario = row
            contenido_carrito.append({
                "IdProducto": id_producto,
                "Codigo": codigo,
                "Marca": marca,
                "Nombre": nombre,
                "Cantidad": cantidad,
                "PrecioUnitario": precio_unitario  # Asegúrate de que este nombre es consistente a lo largo del código
            })
        
        conn.close()
        return contenido_carrito if contenido_carrito else None
    else:
        conn.close()
        return None
    
def obtener_id_carrito(connection_string, user_id):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()
    
    cursor.execute("SELECT IdProducto FROM Producto_Carrito WHERE UserId = ?", (user_id,))
    id_carrito = cursor.fetchone()
    
    conn.close()
    return id_carrito[0] if id_carrito else None

def crear_factura(connection_string, usuario_id, detalles):
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    try:
        # Calcula el total de la factura sumando el total de cada producto en el carrito
        total = sum(item['Cantidad'] * item['PrecioUnitario'] for item in detalles if item['PrecioUnitario'])  # Asegúrate de que 'PrecioUnitario' esté disponible
        
        # Inserta la factura en la tabla Factura
        cursor.execute("INSERT INTO Factura (UsuarioId, Total, FechaCreacion) VALUES (?, ?, GETDATE())", (usuario_id, total))
        factura_id = cursor.execute("SELECT @@IDENTITY AS 'Identity';").fetchval()
        
        # Inserta cada detalle de factura
        for item in detalles:
            cursor.execute("INSERT INTO DetalleFactura (FacturaId, IdProducto, Cantidad, PrecioUnitario) VALUES (?, ?, ?, ?)", (factura_id, item['IdProducto'], item['Cantidad'], item['PrecioUnitario']))
        
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

def obtener_facturas_por_mes(connection_string, username, mes, año):
    conn = get_db_connection(connection_string)
    cursor = conn.cursor()

    # Primero, verifica si el usuario es contador
    cursor.execute("EXEC EsContador @Username=?", (username,))
    es_contador = cursor.fetchone()
    
    if not es_contador or es_contador[0] == 0:
        return {"error": "Acceso denegado: usuario no autorizado"}, 403

    # Si el usuario es contador, procede a buscar las facturas
    query = """
        SELECT *
        FROM Factura
        WHERE MONTH(FechaCreacion) = ? AND YEAR(FechaCreacion) = ?
    """
    cursor.execute(query, (mes, año))
    facturas = []
    for row in cursor.fetchall():
        # Asumiendo que la tabla Factura tiene columnas 'ID', 'UsuarioId', 'Total', y 'FechaCreacion'
        factura_id, usuario_id, total, fecha_creacion = row
        facturas.append({
            "FacturaID": factura_id,
            "UsuarioID": usuario_id,
            "Total": total,
            "FechaCreacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S")  # Formatea la fecha como string
        })

    conn.close()
    return facturas

def crear_producto(codigo, marca, nombre, precioUnitario, cantidad):
    conn = get_db_connection(current_app.config['CONNECTION_STRING'])
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Producto (Codigo, Marca, Nombre, PrecioUnitario, Cantidad) VALUES (?, ?, ?, ?, ?)",
                    (codigo, marca, nombre, precioUnitario, cantidad))
        conn.commit()
        return jsonify({"msg": "Producto creado exitosamente"}), 200
    except Exception as e:
        print("Error al crear el producto:", e)
        conn.rollback()
        return jsonify({"msg": "Error al crear el producto"}), 500
    finally:
        conn.close()
        
def modificar_producto(codigo, nueva_marca, nuevo_nombre, nuevo_precio, nueva_cantidad):
    conn = get_db_connection(current_app.config['CONNECTION_STRING'])
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Producto SET Marca = ?, Nombre = ?, PrecioUnitario = ?, Cantidad = ? WHERE Codigo = ?",
                    (nueva_marca, nuevo_nombre, nuevo_precio, nueva_cantidad, codigo))
        conn.commit()
        return jsonify({"msg": "Producto modificado exitosamente"}), 200
    except Exception as e:
        print("Error al modificar el producto:", e)
        conn.rollback()
        return jsonify({"msg": "Error al modificar el producto"}), 500
    finally:
        conn.close()
        
def eliminar_producto(codigo):
    conn = get_db_connection(current_app.config['CONNECTION_STRING'])
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Producto WHERE Codigo = ?", (codigo,))
        conn.commit()
        return jsonify({"msg": "Producto eliminado exitosamente"}), 200
    except Exception as e:
        print("Error al eliminar el producto:", e)
        conn.rollback()
        return jsonify({"msg": "Error al eliminar el producto"}), 500
    finally:
        conn.close()

