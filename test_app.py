import unittest
from app import app, get_db_connection
from werkzeug.security import generate_password_hash
import mikrotik_api

class TestMikrotikConfigApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Set up test database
        self.conn = get_db_connection()
        with self.conn.cursor() as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100), password VARCHAR(255))')
            cursor.execute('CREATE TABLE IF NOT EXISTS arp_table (id INT AUTO_INCREMENT PRIMARY KEY, ip_address VARCHAR(15), mac_address VARCHAR(17), interface VARCHAR(50), hostname VARCHAR(255), timestamp DATETIME)')
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', ('testuser', generate_password_hash('testpassword')))
        self.conn.commit()

    def tearDown(self):
        with self.conn.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS users')
            cursor.execute('DROP TABLE IF EXISTS arp_table')
        self.conn.close()

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to MikroTik Configuration Tool', response.data)

    def test_login(self):
        response = self.client.post('/login', data=dict(username='testuser', password='testpassword'), follow_redirects=True)
        self.assertIn(b'Logged in successfully', response.data)

    def test_add_arp(self):
        # Mock the MikroTik API call
        mikrotik_api.add_arp_entry = lambda ip, mac, interface, hostname: (True, "ARP entry added successfully")

        self.client.post('/login', data=dict(username='testuser', password='testpassword'))
        response = self.client.post('/add_arp', data=dict(
            ip_address='192.168.1.100',
            mac_address='00:11:22:33:44:55',
            interface='ether1',
            hostname='test-device'
        ), follow_redirects=True)
        self.assertIn(b'ARP entry added successfully', response.data)

    def test_logout(self):
        self.client.post('/login', data=dict(username='testuser', password='testpassword'))
        response = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'Logged out successfully', response.data)

    def test_isp_management(self):
        # Mock the MikroTik API call
        mikrotik_api.get_current_isp = lambda: ('ether1-geni', None)

        self.client.post('/login', data=dict(username='testuser', password='testpassword'))
        response = self.client.get('/isp_management')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ISP Management', response.data)
        self.assertIn(b'ether1-geni', response.data)

    def test_change_isp(self):
        # Mock the MikroTik API call
        mikrotik_api.change_isp = lambda interface: (True, f"Successfully changed ISP to {interface}")

        self.client.post('/login', data=dict(username='testuser', password='testpassword'))
        response = self.client.post('/change_isp', data=dict(new_interface='ether3-VM'), follow_redirects=True)
        self.assertIn(b'Successfully changed ISP to ether3-VM', response.data)

if __name__ == '__main__':
    unittest.main()

