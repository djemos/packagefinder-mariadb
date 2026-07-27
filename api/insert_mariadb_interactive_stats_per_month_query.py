#!/usr/bin/env python3
import json
import mysql.connector
import os
import sys
import calendar
from datetime import datetime, timedelta
import random

# ΣΤΟΙΧΕΙΑ ΣΥΝΔΕΣΗΣ MARIAΒD (SLACKWARE) - Ίδια με το stats.py
DB_CONFIG = {
    'user': 'djemos',
    'password': 'djemos',
    'database': 'slackel_stats',
    'unix_socket': '/var/run/mysql/mysql.sock',
    'auth_plugin': 'mysql_native_password',
    'use_pure': True
}

def insert_interactive_data():
    print("=" * 60)
    print(" ΔΥΝΑΜΙΚΗ ΕΙΣΑΓΩΓΗ ΔΟΚΙΜΑΣΤΙΚΩΝ ΔΕΔΟΜΕΝΩΝ ΣΤΗ MARIADB")
    print("=" * 60)
    
    sample_queries = ["kernel", "firefox", "vlc", "slackel-live", "gimp", "python", "xfce", "mesa", "libreoffice", "smplayer", "thunderbird", "mixx"]
    sample_os = ["Generic Linux", "Android Mobile"]
    
    try:
        # 1. Ερωτήσεις για Ημερομηνία και Πλήθος
        year = int(input("Εισάγετε Έτος (π.χ. 2026): "))
        month = int(input("Εισάγετε Μήνα (1-12): "))
        if month < 1 or month > 12:
            print("Σφάλμα: Ο μήνας πρέπει να είναι από 1 έως 12!")
            return
            
        # Ερώτηση για την ημέρα έναρξης
        day_input = input(f"Από ποια ημέρα του μήνα να ξεκινήσει; (1-{calendar.monthrange(year, month)[1]}) [Πατήστε Enter για τη σημερινή]: ")
        if day_input.strip() == "":
            now = datetime.now()
            if now.year == year and now.month == month:
                start_day = now.day
            else:
                start_day = calendar.monthrange(year, month)[1]
        else:
            start_day = int(day_input)
            
        if start_day < 1 or start_day > calendar.monthrange(year, month)[1]:
            print("Σφάλμα: Μη έγκυρη ημέρα για τον συγκεκριμένο μήνα!")
            return

        M = int(input("Πόσες ημέρες θέλετε να εισαγάγετε συνολικά προς τα πίσω (M); "))
        K = int(input("Πόσες εγγραφές αναζητήσεων ανά ημέρα θέλετε (K); "))
        print("-" * 60)
        
        # 2. Επιλογή Συγκεκριμένου Query / Πακέτου
        print("Επιλέξτε το query που θέλετε να εισαχθεί:")
        print("0. Τυχαία επιλογή από τη λίστα")
        for idx, q in enumerate(sample_queries, 1):
            print(f"{idx}. {q}")
            
        choice = int(input(f"Εισάγετε τον αριθμό της επιλογής σας (0-{len(sample_queries)}): "))
        if choice < 0 or choice > len(sample_queries):
            print("Σφάλμα: Μη έγκυρη επιλογή!")
            return
            
        selected_query = None if choice == 0 else sample_queries[choice - 1]
        print("-" * 60)
        
    except ValueError:
        print("Σφάλμα: Παρακαλώ εισάγετε έγκυρους ακέραιους αριθμούς!")
        return

    # Η base_date ορίζεται από την ημέρα start_day που επιλέχθηκε
    base_date = datetime(year, month, start_day)

    # Δημιουργία λίστας ημερομηνιών πηγαίνοντας προς τα πίσω
    target_dates = []
    for i in range(M):
        t_date = base_date - timedelta(days=i)
        if t_date.month == month and t_date.year == year:
            target_dates.append(t_date.strftime('%Y-%m-%d'))

    if not target_dates:
        print("❌ Σφάλμα: Δεν δημιουργήθηκαν έγκυρες ημερομηνίες για αυτόν τον μήνα.")
        return

    # Σύνδεση στη MariaDB αντί για SQLite
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Αποτυχία σύνδεσης στη MariaDB: {str(e)}")
        return
    # --- ΚΑΘΑΡΙΣΜΟΣ ΜΟΝΟ ΤΩΝ ΗΜΕΡΩΝ ΠΟΥ ΘΑ ΞΑΝΑΓΡΑΦΟΥΝ ---
    print(f"Καθαρισμός παλιών δεδομένων στη MariaDB για τις {len(target_dates)} συγκεκριμένες ημέρες...")
    for date_str in target_dates:
        # ΔΙΟΡΘΩΣΗ: Χρήση %s αντί για ? κατάλληλο για τη MariaDB
        cursor.execute("DELETE FROM searches WHERE DATE(timestamp) = %s", (date_str,))
        cursor.execute("DELETE FROM visits WHERE date = %s", (date_str,))
    conn.commit()
    
    print(f"Σύνδεση στη MariaDB επιτυχής: {DB_CONFIG['database']}")
    print(f"Έναρξη εισαγωγής (πηγαίνοντας πίσω από {base_date.strftime('%Y-%m-%d')})...")
  
    # Loop για τις ημέρες
    for date_str in target_dates:
        # Εισαγωγή αναζητήσεων
        for _ in range(K):
            query = selected_query if selected_query else random.choice(sample_queries)
            count = random.randint(10, 40)
            
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            random_second = random.randint(0, 59)
            timestamp_str = f"{date_str} {random_hour:02d}:{random_minute:02d}:{random_second:02d}"
            
            # ΔΙΟΡΘΩΣΗ: Αντικατάσταση των (?, ?, ?) με (%s, %s, %s)
            cursor.execute("INSERT INTO searches (query, count, timestamp) VALUES (%s, %s, %s)", 
                           (query, count, timestamp_str))
        
        # Εισαγωγή visits
        num_visits_today = K * random.randint(3, 6)
        for _ in range(num_visits_today):
            mock_ip = f"192.168.1.{random.randint(1, 254)}"
            mock_os = random.choice(sample_os)
            
            # ΔΙΟΡΘΩΣΗ: Αντικατάσταση των (?, ?, ?) με (%s, %s, %s)
            cursor.execute("INSERT INTO visits (ip, date, country) VALUES (%s, %s, %s)", 
                           (mock_ip, date_str, mock_os))

    conn.commit()
    cursor.close()
    conn.close()
    
    query_display = selected_query if selected_query else "τυχαίων πακέτων"
    print("=" * 60)
    print(f"Επιτυχία! Προστέθηκαν δεδομένα στη MariaDB για {len(target_dates)} ημέρες του πακέτου '{query_display}' για τον {month:02d}/{year}.")
    print("Ανανεώστε τη σελίδα stats.html για να δείτε τα νέα αποτελέσματα.")
    print("=" * 60)

if __name__ == "__main__":
    insert_interactive_data()
