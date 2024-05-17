# database.py
import pyodbc
from config import Config

def get_db_connection():
    connection = pyodbc.connect(Config.CONNECTION_STRING, autocommit=True)
    return connection

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM Usuario WHERE username = ?", username)
    user = cursor.fetchone()
    conn.close()
    if user and user.password == password:
        return True
    return False

def get_product_info():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, marca, nombre, precioUnitario, cantidad FROM Producto")
    productos = []
    for row in cursor.fetchall():
        codigo, marca, nombre, precio, cantidad = row
        productos.append({
            "Código del producto": codigo,
            "Marca": marca,
            "Nombre": nombre,
            "PrecioUnitario": precio,
            "Cantidad": cantidad
        })
    conn.close()
    return productos

def actualizar_cantidad_producto(codigo, cantidad):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta SQL para obtener la cantidad actual del producto
    cursor.execute("SELECT Cantidad FROM Producto WHERE Codigo = ?", (codigo,))
    row = cursor.fetchone()
    if row is None:
        # El producto no existe en la base de datos
        conn.close()
        return False
    
    cantidad_actual = row[0]
    nueva_cantidad = cantidad_actual - cantidad

    if nueva_cantidad >= 0:
        # La nueva cantidad es válida, actualizamos la base de datos
        cursor.execute("UPDATE Producto SET Cantidad = ? WHERE Codigo = ?", (nueva_cantidad, codigo))
        conn.commit()
        conn.close()
        return True
    else:
        # La nueva cantidad sería negativa, no se puede completar la operación
        conn.close()
        return False
    
def obtener_info_producto(codigo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Codigo, Marca, Nombre, precioUnitario, Cantidad FROM Producto WHERE Codigo = ?", (codigo,))
    producto = cursor.fetchone()
    conn.close()
    if producto:
        columns = ["Codigo", "Marca", "Nombre", "precioUnitario", "Cantidad"]
        producto_dict = dict(zip(columns, producto))
        return producto_dict
    else:
        return None
    

