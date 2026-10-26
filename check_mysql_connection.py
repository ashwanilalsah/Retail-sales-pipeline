import getpass
import mysql.connector

connection = None
cursor = None

try:
    password = getpass.getpass("MySQL root password (input hidden): ")

    connection = mysql.connector.connect(
        user="root",
        password=password,
        unix_socket="/tmp/mysql.sock",
        connection_timeout=5,
    )

    print("MySQL connection successful!")

    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    print("MySQL version:", cursor.fetchone()[0])

except mysql.connector.Error as error:
    print("MySQL connection failed:", error)

finally:
    if cursor is not None:
        cursor.close()

    if connection is not None and connection.is_connected():
        connection.close()
        print("Connection closed safely.")