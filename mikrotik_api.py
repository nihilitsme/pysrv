import routeros_api
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# MikroTik router connection details from environment variables
MIKROTIK_HOST = os.getenv('MIKROTIK_HOST')
MIKROTIK_USERNAME = os.getenv('MIKROTIK_USER')
MIKROTIK_PASSWORD = os.getenv('MIKROTIK_PASSWORD')

def get_mikrotik_connection():
    try:
        connection = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST,
            username=MIKROTIK_USERNAME,
            password=MIKROTIK_PASSWORD,
            plaintext_login=True
        )
        api = connection.get_api()
        return api, connection
    except Exception as e:
        logger.error(f"Failed to connect to MikroTik: {str(e)}")
        return None, None

def add_arp_entry(ip_address, mac_address, interface, hostname=None):
    api, connection = get_mikrotik_connection()
    if not api:
        return False, "Failed to connect to MikroTik router"
    
    try:
        # Validate IP and MAC address format
        if not is_valid_ip(ip_address) or not is_valid_mac(mac_address):
            return False, "Invalid IP or MAC address format"

        arp_list = api.get_resource('/ip/arp')
        
        # Check if entry already exists
        existing_entries = arp_list.get(address=ip_address)
        if existing_entries:
            return False, f"ARP entry for {ip_address} already exists"

        # Prepare ARP entry parameters
        entry_params = {
            'address': ip_address,
            'mac-address': mac_address,
            'interface': interface
        }
        
        # Add hostname as comment if provided
        if hostname:
            entry_params['comment'] = hostname

        # Add the ARP entry
        arp_list.add(**entry_params)
        logger.info(f"Successfully added ARP entry for {ip_address}")
        return True, "ARP entry added successfully"

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error adding ARP entry: {error_msg}")
        return False, f"Failed to add ARP entry: {error_msg}"
    
    finally:
        if connection:
            connection.disconnect()

def is_valid_ip(ip):
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    octets = ip.split('.')
    return all(0 <= int(octet) <= 255 for octet in octets)

def is_valid_mac(mac):
    import re
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac))

def get_current_isp():
    api, connection = get_mikrotik_connection()
    if not api:
        return None, "Failed to connect to MikroTik router"
    
    try:
        mangle = api.get_resource('/ip/firewall/mangle')
        rules = mangle.get(comment='CONN-CS', chain='prerouting', action='mark-routing')
        
        if rules:
            # Get the first enabled rule with CONN-CS comment
            for rule in rules:
                if rule.get('disabled') != 'true':
                    return rule.get('new-routing-mark'), None
        
        return None, "No active ISP connection found"
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting current ISP: {error_msg}")
        return None, f"Failed to get current ISP: {error_msg}"
    finally:
        if connection:
            connection.disconnect()

def change_isp(new_routing_mark):
    api, connection = get_mikrotik_connection()
    if not api:
        return False, "Failed to connect to MikroTik router"
    
    try:
        mangle = api.get_resource('/ip/firewall/mangle')
        rules = mangle.get(comment='CONN-CS', chain='prerouting', action='mark-routing')
        
        if not rules:
            return False, "No CONN-CS rules found"
        
        # Update all CONN-CS rules to use the new routing mark
        for rule in rules:
            rule_id = rule.get('id')
            if rule_id is None:  # Add check for None rule_id
                continue
            mangle.set(id=rule_id, **{'new-routing-mark': new_routing_mark})
        
        logger.info(f"Successfully changed ISP to {new_routing_mark}")
        return True, f"Successfully changed ISP to {new_routing_mark}"
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error changing ISP: {error_msg}")
        return False, f"Failed to change ISP: {error_msg}"
    finally:
        if connection:
            connection.disconnect()
