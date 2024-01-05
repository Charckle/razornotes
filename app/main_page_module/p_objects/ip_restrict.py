import ipaddress

from app import app

def get_list_of_allowed_ips():
    return app.config['IPS_NETWORKS'].split(",")

def check_ip_match(allowed_ip, client_ip):
    try:
        allowed_ip = ipaddress.ip_address(allowed_ip)
        client_ip = ipaddress.ip_address(client_ip)
        
        if allowed_ip == client_ip:
            app.logger.info(f"Allowed IP: {allowed_ip}")
            return True
    except:
        allowed_ip = ipaddress.ip_network(allowed_ip)
        client_ip = ipaddress.ip_address(client_ip)
        
        if client_ip in allowed_ip:
            app.logger.info(f"Allowed Network: {allowed_ip}")
            return True
    
    return False


def is_ip_allowed(client_ip):
    allowed_ips = get_list_of_allowed_ips()
    
    for allowed_ip in allowed_ips:
        if check_ip_match(allowed_ip, client_ip):
            return True
        
    return False