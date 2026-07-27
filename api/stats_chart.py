#!/usr/bin/env python3
import json
import mysql.connector
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont 
from pathlib import Path

# Έλεγχος και φιλτράρισμα αυτοματοποιημένων bots / scanners
user_agent = os.environ.get('HTTP_USER_AGENT', '').lower()
bad_agents = ['curl', 'wget', 'python', 'perl', 'libwww', 'go-http', 'scanner', 'bot', 'spider']

if not user_agent or any(agent in user_agent for agent in bad_agents):
    # Επιστρέφουμε έγκυρο header στον Apache για να μην βγάλει 500 Internal Server Error
    print("Content-Type: text/html\n")
    print("Access Denied: Automated tools are not allowed.")
    sys.exit(0)

# ΣΤΟΙΧΕΙΑ ΣΥΝΔΕΣΗΣ MARIAΒD (SLACKWARE)
DB_CONFIG = {
    'user': 'djemos',
    'password': 'djemos',
    'database': 'slackel_stats',
    'unix_socket': '/var/run/mysql/mysql.sock',
    'auth_plugin': 'mysql_native_password',
    'use_pure': True
}

# 1. ΣΩΣΤΗ ΕΚΤΟΥΠΩΣΗ HEADERS ΩΣ BINARY ΜΕ ΑΠΑΓΟΡΕΥΣΗ CACHE
sys.stdout.buffer.write(b"Content-Type: image/png\n")
sys.stdout.buffer.write(b"Cache-Control: no-cache, no-store, must-revalidate\n")
sys.stdout.buffer.write(b"Pragma: no-cache\n")
sys.stdout.buffer.write(b"Expires: 0\n\n")

# 2. Φόρτωση δεδομένων από τη βάση MariaDB σε Dictionary
db_rows = {}
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT DATE(timestamp) as s_date, SUM(count) as daily_count 
                      FROM searches
                      WHERE timestamp IS NOT NULL
                      GROUP BY s_date
                      ORDER BY s_date ASC''')
    
    for row in cursor.fetchall():
        if row is not None and row[0] is not None:
            # ΔΙΟΡΘΩΣΗ 1: Παίρνουμε το row[0] (το date object) και το κάνουμε string
            date_key = str(row[0])
            db_rows[date_key] = int(row[1]) if row[1] is not None else 0
            
    cursor.close()
    conn.close()
except Exception:
    pass

# --- Δημιουργούμε σταθερό παράθυρο 120 ημερών μέχρι σήμερα ---
daily_counts = []
daily_dates = []
today_date = datetime.now()

for i in range(119, -1, -1):
    target_date = today_date - timedelta(days=i)
    date_str = target_date.strftime('%Y-%m-%d')
    daily_dates.append(date_str)
    daily_counts.append(db_rows.get(date_str, 0))

# ΔΙΟΡΘΩΣΗ 2: Σωστή αρχικοποίηση αν η λίστα είναι άδεια
if not daily_counts or max(daily_counts) == 0:
    daily_counts = [0] * 120

# 3. Ρυθμίσεις γραφήματος & Padding στην Κορυφή
num_days = len(daily_counts)
bar_width = 3   
space = 2       

img_width = max(num_days * (bar_width + space), 200) + 60
img_height = 200  

padding_top = 48  
usable_height = img_height - padding_top

max_val = max(daily_counts) if max(daily_counts) > 0 else 1
scale_factor = usable_height / max_val

query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
theme_list = query.get("theme", ["light"])
theme = theme_list[0] if theme_list else "light"

red_month_color = (220, 20, 60) 

if theme == "dark":
    bg_color = (230, 245, 230)         
    bar_color = (0, 0, 0)              
    line_color = (74, 85, 104)
    avg_color = (255, 128, 200)
else:
    bg_color = (230, 245, 230)         
    bar_color = (0, 0, 0)
    line_color = (170, 190, 200)
    avg_color = (220, 20, 60)

white_bg_color = (255, 255, 255)

# 4. Σχεδίαση Εικόνας
im = Image.new("RGB", (img_width, img_height), white_bg_color)
draw = ImageDraw.Draw(im)

font = None
font_paths = [
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/X11/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/X11/TTF/LiberationSans-Bold.ttf"
]
for path in font_paths:
    try:
        font = ImageFont.truetype(path, 11)
        break
    except IOError:
        continue

if font is None:
    font = ImageFont.load_default()

blue_graph_color = (0, 102, 255)  
graph_offset_left = 35 

max_graph_x = graph_offset_left + ((num_days - 1) * (bar_width + space)) + bar_width
draw.rectangle([0, 0, max_graph_x, img_height], fill=bg_color)

scale_step = max(1, round(max_val / 5)) if max_val > 5 else 1
for i in range(scale_step, max_val + 1, scale_step):
    y_pos = img_height - int(i * scale_factor)
    draw.line([(graph_offset_left, y_pos), (max_graph_x, y_pos)], fill=blue_graph_color, width=1)
    draw.text((2, y_pos - 12), str(i), fill=blue_graph_color, font=font)

# --- Layer 2: Μπάρες Δεδομένων & Γραμμές Σαββατοκύριακου ---
weekend_line_color = (120, 200, 120)  

max_blue_y = img_height - int(max_val * scale_factor)
green_line_start_y = max_blue_y + 6 

for index, val in enumerate(daily_counts):
    x0 = graph_offset_left + (index * (bar_width + space))
    y0 = img_height - int(val * scale_factor)
    x1 = x0 + bar_width
    y1 = img_height
    
    try:
        date_str = daily_dates[index]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_of_week = date_obj.weekday()  
        
        if day_of_week == 6 and index > 0:
            draw.line([(x0 - 1, green_line_start_y), (x0 - 1, img_height)], fill=weekend_line_color, width=1)
    except Exception:
        pass
        
    draw.rectangle([x0, y0, x1, y1], fill=bar_color)
# --- Layer 3: ΔΥΟ ΚΥΜΑΤΙΣΤΕΣ ΓΡΑΜΜΕΣ ΜΕΣΟΥ ΟΡΟΥ ---
COLOR_HOT_PINK   = (255, 105, 180)  # Έντονο Ροζ
COLOR_ROYAL_BLUE = (20, 80, 200)     # Βαθύ Μπλε
COLOR_ORANGE     = (230, 100, 20)    # Έντονο Πορτοκαλί
COLOR_PURPLE     = (155, 89, 182)    # Μοβ / Βιολετί
COLOR_DARK_GRAY  = (50, 50, 50)      # Σκούρο Γκρι
COLOR_RED        = (220, 20, 60)     # Καθαρό Κόκκινο (Crimson)
COLOR_LIGHT_BLUE = (0, 180, 255)     # Φωτεινό Γαλάζιο (Sky Blue)
COLOR_DEEP_GREEN = (40, 140, 70)     # Βαθύ Πράσινο (Forest Green)

# ΕΝΕΡΓΕΣ ΕΠΙΛΟΓΕΣ: (Ρυθμισμένο στο Βαθύ Μπλε - Ροζ)
monthly_active_color = COLOR_HOT_PINK      # Χρώμα για τις 30 ημέρες (Αριστερά)
weekly_active_color  = COLOR_ROYAL_BLUE    # Χρώμα για τις 7 ημέρες (Δεξιά)


# ΒΗΜΑ A: ΚΥΜΑΤΙΣΤΗ ΓΡΑΜΜΗ ΜΗΝΙΑΙΑΣ ΤΑΣΗΣ (30 Ημερών)
points_30 = []
last_val_30 = 0

for index in range(len(daily_counts)):
    start_idx_30 = max(0, index - 29)
    current_window_30 = daily_counts[start_idx_30 : index + 1]
    window_avg_30 = sum(current_window_30) / len(current_window_30)
    
    last_val_30 = window_avg_30
    
    x = graph_offset_left + (index * (bar_width + space)) + (bar_width // 2)
    y = img_height - int(window_avg_30 * scale_factor)
    
    if y < padding_top:
        y = padding_top
    points_30.append((x, y))

if len(points_30) > 1:
    draw.line(points_30, fill=monthly_active_color, width=2)

if points_30:
    text_30 = f"─ Avg. last 30 days: {round(last_val_30)}"
    draw.text((45, 17), text_30, fill=monthly_active_color, font=font)


# ΒΗΜΑ B: ΚΥΜΑΤΙΣΤΗ ΓΡΑΜΜΗ ΕΒΔΟΜΑΔΙΑΙΑΣ ΤΑΣΗΣ (7 Ημερών)
points_7 = []
last_val_7 = 0

for index in range(len(daily_counts)):
    start_idx_7 = max(0, index - 6)
    current_window_7 = daily_counts[start_idx_7 : index + 1]
    window_avg_7 = sum(current_window_7) / len(current_window_7)
    
    last_val_7 = window_avg_7
    
    x = graph_offset_left + (index * (bar_width + space)) + (bar_width // 2)
    y = img_height - int(window_avg_7 * scale_factor)
    
    if y < padding_top:
        y = padding_top
    points_7.append((x, y))

if len(points_7) > 1:
    draw.line(points_7, fill=weekly_active_color, width=2)

if points_7:
    text_trend = f"─ Avg. last 7 days: {round(last_val_7)}"
    draw.text((img_width - 185, 17), text_trend, fill=weekly_active_color, font=font)


# --- Layer 4: Εμφάνιση Μήνα στην Κορυφή & Κατακόρυφες Γραμμές Διαχωρισμού ---
last_month = None

# ΒΗΜΑ Α: Υπολογίζουμε πόσες ημέρες έχει ο πρώτος μήνας στην αρχή του γραφήματος
first_month_name = None
first_month_days = 0

for date_str in daily_dates:
    try:
        m_name = datetime.strptime(date_str, '%Y-%m-%d').strftime('%b')
        if first_month_name is None:
            first_month_name = m_name
        if m_name == first_month_name:
            first_month_days += 1
        else:
            break  # Σταματάμε μόλις αλλάξει ο πρώτος μήνας
    except Exception:
        pass

# ΔΙΟΡΘΩΣΗ: Καλύπτουμε όλο το εύρος από 115 έως 125 ημέρες
is_full_period = (115 <= len(daily_counts) <= 125)

# ΒΗΜΑ Β: Σχεδίαση των Μηνών με βάση τους νέους κανόνες ασφαλείας
for index, date_str in enumerate(daily_dates):
    x0 = graph_offset_left + (index * (bar_width + space))
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        current_month = date_obj.strftime('%b')
        
        if current_month != last_month:
            # ΚΑΝΟΝΑΣ 1: Αν είμαστε στην πλήρη περίοδο (119-123 ημέρες) ΚΑΙ ο πρώτος μήνας 
            # έχει 8 ή λιγότερες ημέρες, τότε κάνουμε SKIP τον πρώτο μήνα (Μάρτιο).
            if is_full_period and current_month == first_month_name and first_month_days <= 8:
                last_month = current_month
                continue
                
            # ΚΑΝΟΝΑΣ 2: Σε κάθε άλλη περίπτωση (μικρότερη περίοδος), σχεδιάζουμε κανονικά όλους τους μήνες.
            draw.line([(x0, 2), (x0, img_height)], fill=red_month_color, width=1)
            draw.text((x0 + 3, 1), current_month, fill=red_month_color, font=font)
            last_month = current_month
    except Exception:
        pass

# Ασφαλής αποθήκευση και εκτύπωση της εικόνας στο stdout ως binary PNG
im.save(sys.stdout.buffer, format="PNG")
