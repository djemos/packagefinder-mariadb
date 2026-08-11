#!/usr/bin/env python3
import json
import mysql.connector
import os
import sys
import hashlib
from datetime import datetime

# Έλεγχος και φιλτράρισμα αυτοματοποιημένων bots / scanners
user_agent = os.environ.get('HTTP_USER_AGENT', '').lower()
bad_agents = ['curl', 'wget', 'python', 'perl', 'libwww', 'go-http', 'scanner', 'bot', 'spider']

if not user_agent or any(agent in user_agent for agent in bad_agents):
    # Επιστρέφουμε έγκυρο header στον Apache για να μην βγάλει 500 Internal Server Error
    print("Content-Type: text/html\n")
    print("Access Denied: Automated tools are not allowed.")
    sys.exit(0)

# ==========================================
# SECURE PASSWORD ENCRYPTION SETTING
# ==========================================
# The password "your_password" is stored as a SHA-256 hash with salt for maximum security.
ADMIN_PASSWORD_HASH = "your_hash" # Replace with your own
PASSWORD_SALT = "your_password" # Replace with your own

ONLINE_TIMEOUT_SECONDS = 300  
MAX_ATTEMPTS = 5              # Μέγιστες αποτυχημένες προσπάθειες login
LOCKOUT_DURATION = 900        # 15 λεπτά αποκλεισμού σε δευτερόλεπτα

# ΣΤΟΙΧΕΙΑ ΣΥΝΔΕΣΗΣ MARIAΒD (SLACKWARE)
DB_CONFIG = {
    'user': 'your_user',
    'password': 'your_password',
    'database': 'slackel_stats',
    'unix_socket': '/var/run/mysql/mysql.sock',
    'auth_plugin': 'mysql_native_password',
    'use_pure': True
}

def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS searches 
                      (id INT AUTO_INCREMENT PRIMARY KEY,
                       query VARCHAR(255), 
                       count INT DEFAULT 1, 
                       timestamp DATETIME,
                       INDEX idx_searches_timestamp (timestamp)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS visits 
                      (id INT AUTO_INCREMENT PRIMARY KEY, 
                       ip VARCHAR(45), 
                       date DATE, 
                       system VARCHAR(100) DEFAULT 'Unknown',
                       INDEX idx_visits_date (date)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS online_users 
                      (ip VARCHAR(45) PRIMARY KEY, 
                       last_seen DATETIME) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS login_attempts 
                      (ip VARCHAR(45) PRIMARY KEY, 
                       attempts INT DEFAULT 0, 
                       last_attempt DATETIME) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;''')
    
    conn.commit()
    cursor.close()
    conn.close()

def get_client_ip():
    ip = os.environ.get('HTTP_X_FORWARDED_FOR', '')
    if ip:
        return ip.split(',')[0].strip()
    return os.environ.get('REMOTE_ADDR', '127.0.0.1').strip()

def check_brute_force(cursor, ip):
    """Απενεργοποιημένο Rate Limiting: Επιτρέπει πάντα την προσπάθεια login στη MariaDB."""
    return True, ""  # <-- Παρακάμπτει τον έλεγχο, άρα δεν κλειδώνει ποτέ την IP

def log_login_failure(cursor, ip):
    """Δεν καταγράφει τις αποτυχίες, εξαλείφοντας τα SQL locks και τα σφάλματα bindings."""
    pass  # <-- Δεν εκτελεί κανένα query, άρα μηδέν φόρτος στη MariaDB

def log_login_success(cursor, ip):
    """Μηδενίζει τις αποτυχημένες προσπάθειες μετά από επιτυχές login."""
    cursor.execute("DELETE FROM login_attempts WHERE ip=%s", (ip,))

def verify_password(plain_password):
    """Ελέγχει αν το hash του εισαγόμενου κωδικού ταιριάζει με το αποθηκευμένο."""
    salted = plain_password + PASSWORD_SALT
    hashed = hashlib.sha256(salted.encode('utf-8')).hexdigest()
    return hashed == ADMIN_PASSWORD_HASH

def parse_user_agent(ua_string):
    if not ua_string:
        return "Unknown System"
    ua = ua_string.lower()
    if "slackel" in ua: return "Slackel Linux"
    elif "slackware" in ua or "x11; u; linux" in ua or "slack" in ua: return "Slackware Linux"
    elif "android" in ua: return "Android Mobile"
    elif "iphone" in ua or "ipad" in ua: return "iOS (iPhone/iPad)"
    elif "linux" in ua: return "Generic Linux"
    elif "windows" in ua: return "Windows PC"
    elif "macintosh" in ua or "mac os" in ua: return "macOS"
    return "Other / Web Bot"
    
def handle_stats():
    print("Content-Type: application/json; charset=utf-8")
    print("Cache-Control: no-store, no-cache, must-revalidate")
    print("X-Content-Type-Options: nosniff\n")
    
    try:
        init_db()
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        ip = get_client_ip()
        method = os.environ.get('REQUEST_METHOD', 'GET')
        
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
        
        user_agent = os.environ.get('HTTP_USER_AGENT', '')
        detected_os = parse_user_agent(user_agent)

        # 1. Καταγραφή μοναδικής επίσκεψης ανά ημέρα
        cursor.execute("SELECT id FROM visits WHERE ip=%s AND date=%s", (ip, today))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO visits (ip, date, system) VALUES (%s, %s, %s)", (ip, today, detected_os))
        
        # 2. Καταγραφή online χρήστη & διαγραφή ανενεργών
        cursor.execute("INSERT INTO online_users (ip, last_seen) VALUES (%s, %s) ON DUPLICATE KEY UPDATE last_seen=%s", (ip, formatted_now, formatted_now))
        cursor.execute(
            "DELETE FROM online_users WHERE TIMESTAMPDIFF(SECOND, last_seen, %s) > %s", 
            (formatted_now, ONLINE_TIMEOUT_SECONDS)
        )
        conn.commit()

        # 3. Διαχείριση DELETE (Clear History)
        if method == 'DELETE' or (method == 'POST' and os.environ.get('HTTP_X_HTTP_METHOD_OVERRIDE') == 'DELETE'):
            is_allowed, error_msg = check_brute_force(cursor, ip)
            if not is_allowed:
                print(json.dumps({"status": "error", "message": error_msg}))
                conn.commit()
                cursor.close()
                conn.close()
                return

            body = sys.stdin.read()
            if body:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    print(json.dumps({"status": "error", "message": "Invalid JSON data payload."}))
                    cursor.close()
                    conn.close()
                    return

                input_password = data.get('password', '')
                if verify_password(input_password):
                    log_login_success(cursor, ip)
                    cursor.execute("TRUNCATE TABLE searches")
                    cursor.execute("TRUNCATE TABLE visits")
                    cursor.execute("TRUNCATE TABLE online_users")
                    conn.commit()
                    print(json.dumps({"status": "success", "message": "History cleared!"}))
                else:
                    log_login_failure(cursor, ip)
                    conn.commit()
                    print(json.dumps({"status": "error", "message": "Incorrect password!"}))
            
            cursor.close()
            conn.close()
            return

        # 4. Διαχείριση POST (Καταγραφή αναζήτησης)
        if method == 'POST':
            body = sys.stdin.read()
            if body:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    print(json.dumps({"status": "error", "message": "Invalid JSON data payload."}))
                    cursor.close()
                    conn.close()
                    return

                query = data.get('query', '').strip()
                if query:
                    # Έλεγχος αν υπάρχει το ίδιο query ΜΟΝΟ για τη σημερινή ημέρα
                    # ΔΙΟΡΘΩΣΗ: Χρήση %s και DATE() συμβατό με MariaDB
                    cursor.execute("SELECT count, id FROM searches WHERE query=%s AND DATE(timestamp)=%s", (query, today))
                    row = cursor.fetchone()
                    
                    if row:
                        current_count, row_id = int(row[0]), int(row[1])
                        # Ενημέρωση του count ΚΑΙ του timestamp για να έρθει η αναζήτηση στην κορυφή του "Last Searches"
                        cursor.execute("UPDATE searches SET count=%s, timestamp=%s WHERE id=%s", 
                                       (current_count + 1, formatted_now, row_id))
                    else:
                        # Αν δεν υπάρχει για σήμερα ή αν είναι άλλη μέρα, εισάγουμε νέα εγγραφή
                        cursor.execute("INSERT INTO searches (query, count, timestamp) VALUES (%s, 1, %s)", 
                                       (query, formatted_now))
                    
                    # Κρατάμε μόνο τις 1000 πιο πρόσφατες αναζητήσεις συνολικά για λόγους επιδόσεων
                    # ΔΙΟΡΘΩΣΗ: Χρήση id αντί rowid και ασφαλές διπλό subquery για τη MariaDB
                    cursor.execute("""
                        DELETE FROM searches 
                        WHERE id NOT IN (
                            SELECT id FROM (
                                SELECT id FROM (
                                    SELECT id FROM searches ORDER BY timestamp DESC LIMIT 1000
                                ) as tmp
                            ) as tmp2
                        )
                    """)
                    conn.commit()
                    print(json.dumps({"status": "success"}))
                else:
                    print(json.dumps({"status": "error", "message": "Empty query term provided."}))
            else:
                print(json.dumps({"status": "error", "message": "Missing POST data payload."}))
                
            cursor.close()
            conn.close()
            return

        # 5. Διαχείριση GET (Ανάκτηση δεδομένων)
        cursor.execute("SELECT query, count, timestamp FROM searches ORDER BY timestamp DESC LIMIT 100")
        last_searches = [{"query": row[0], "count": int(row[1]), "time": str(row[2])} for row in cursor.fetchall()]
        
        cursor.execute("SELECT query, SUM(count) as total_count, max(timestamp) as last_time FROM searches GROUP BY query ORDER BY total_count DESC, last_time DESC LIMIT 100")
        hot_queries = [{"query": row[0], "count": int(row[1]), "time": str(row[2])} for row in cursor.fetchall()]
        
        cursor.execute('''SELECT DATE(timestamp) as search_date, SUM(count) as daily_count 
                          FROM searches
                          WHERE timestamp IS NOT NULL
                          GROUP BY search_date
                          ORDER BY search_date ASC''')
        daily_analytics = [{"date": str(row[0]), "count": int(row[1])} for row in cursor.fetchall()]
        
        cursor.execute('''SELECT system, COUNT(*) as c FROM visits GROUP BY system ORDER BY c DESC LIMIT 100''')
        top_countries = [{"system": row[0], "count": int(row[1])} for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM visits")
        res_total = cursor.fetchone()
        total_visits = int(res_total[0]) if res_total and res_total[0] is not None else 0
        
        cursor.execute("SELECT COUNT(*) FROM visits WHERE date=%s", (today,))
        res_today = cursor.fetchone()
        today_visits = int(res_today[0]) if res_today and res_today[0] is not None else 0
        
        cursor.execute("SELECT COUNT(*) FROM online_users")
        res_online = cursor.fetchone()
        online_count = int(res_online[0]) if res_online and res_online[0] is not None else 0
        
        cursor.close()
        conn.close()
        
        print(json.dumps({
            "last_searches": last_searches,
            "hot_queries": hot_queries,
            "daily_analytics": daily_analytics,
            "top_countries": top_countries,
            "total_visits": total_visits,
            "today_visits": today_visits,
            "online_users": online_count
        }))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    handle_stats()
