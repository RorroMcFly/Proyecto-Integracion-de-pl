# /instance/config.py

class Config:
    SECRET_KEY = 'admin1'  # Cambia esta clave en producción
    SQL_SERVER = 'L-PASANTE-TI\SQLEXPRESS'  # Asegúrate de escapar la barra invertida con otra barra invertida
    SQL_DATABASE = 'Api'
    SQL_USERNAME = 'sa'
    SQL_PASSWORD = 'jcjajplae*88'
    SQL_DRIVER = 'ODBC Driver 17 for SQL Server'
    CONNECTION_STRING = f'DRIVER={SQL_DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};UID={SQL_USERNAME};PWD={SQL_PASSWORD}'
