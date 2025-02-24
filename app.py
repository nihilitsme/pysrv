from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_paginate import Pagination, get_page_parameter
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from datetime import datetime
import mikrotik_api
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Database connection
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'it-users'),
        password=os.getenv('DB_PASSWORD', 'dewagrup666'),
        database=os.getenv('DB_NAME', 'it_tools'),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) as count FROM arp_table')
        total = cursor.fetchone()['count']
        
        cursor.execute('SELECT * FROM arp_table ORDER BY timestamp DESC LIMIT %s OFFSET %s', (per_page, offset))
        arp_entries = cursor.fetchall()
    
    conn.close()
    
    pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')
    
    interfaces = ['ether1-geni', 'ether3-VM', 'ACC-1000', 'CS-2000', 'OTH-3000', 'GA-4000', 'VLAN-LTSC_100', 'VLAN-PROXMOX_123', 'VLAN-LXC_234', 'VLAN-FW_303', 'VLAN-HOMELAB_889' ]

    return render_template('dashboard.html', 
                           arp_entries=arp_entries, 
                           pagination=pagination, 
                           interfaces=interfaces)

@app.route('/add_arp', methods=['POST'])
def add_arp():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        ip_address = request.form['ip_address']
        mac_address = request.form['mac_address']
        interface = request.form['interface']
        hostname = request.form.get('hostname')
        
        # Add ARP entry to MikroTik router
        success, message = mikrotik_api.add_arp_entry(
            ip_address=ip_address,
            mac_address=mac_address,
            interface=interface,
            hostname=hostname
        )
        
        if success:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO arp_table 
                        (ip_address, mac_address, interface, hostname, timestamp) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (ip_address, mac_address, interface, hostname, datetime.now()))
                conn.commit()
                flash('ARP entry added successfully', 'success')
            except Exception as db_error:
                flash(f'Database error: {str(db_error)}', 'error')
            finally:
                conn.close()
        else:
            flash(message, 'error')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                flash('Logged in successfully', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Username already exists', 'error')
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
                conn.commit()
                flash('Registration successful', 'success')
                return redirect(url_for('login'))
        conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/isp_management')
def isp_management():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_isp, error = mikrotik_api.get_current_isp()
    if error:
        flash(error, 'error')
    
    routing_marks = ['ISP-PPP', 'ISP-PLDT', '0.WG-T', '0000.WG-MP', '0000.WG-WL', 'L2TP-OFFICE', 'OFFICE-MNL-DIST', 'OFFICE-MNL-SRV']
    # Removed duplicate routing_marks list
    
    return render_template('isp.html', 
                           current_isp=current_isp or 'Unknown',
                           routing_marks=routing_marks)

@app.route('/change_isp', methods=['POST'])
def change_isp():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_routing_mark = request.form.get('new_routing_mark')
    if not new_routing_mark:
        flash('Please select a routing mark', 'error')
        return redirect(url_for('isp_management'))
    
    success, message = mikrotik_api.change_isp(new_routing_mark)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('isp_management'))

@app.route('/arp/<int:id>', methods=['DELETE'])
def delete_arp(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM arp_table WHERE id = %s', (id,))
        conn.commit()
        return jsonify({'message': 'ARP entry deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/arp/<int:id>', methods=['PUT'])
def update_arp(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE arp_table 
                SET ip_address = %s, mac_address = %s, interface = %s, hostname = %s
                WHERE id = %s
            ''', (data['ip_address'], data['mac_address'], data['interface'], data['hostname'], id))
        conn.commit()
        return jsonify({'message': 'ARP entry updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
