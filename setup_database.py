import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    # Get database credentials from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'it-users')
    db_password = os.getenv('DB_PASSWORD', 'dewagrup666')
    db_name = os.getenv('DB_NAME', 'it_tools')

    # Connect to MySQL server
    conn = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password
    )
    
    try:
        with conn.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            cursor.execute(f"USE {db_name}")
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            ''')
            
            # Create arp_table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arp_table (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip_address VARCHAR(15) NOT NULL,
                    mac_address VARCHAR(17) NOT NULL,
                    interface VARCHAR(50) NOT NULL,
                    hostname VARCHAR(255),
                    timestamp DATETIME NOT NULL
                )
            ''')
            
        conn.commit()
        print("Database setup completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    setup_database()

