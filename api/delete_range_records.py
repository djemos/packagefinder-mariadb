#!/usr/bin/env python3
import mysql.connector
import os
from datetime import date

# ΣΤΟΙΧΕΙΑ ΣΥΝΔΕΣΗΣ MARIAΒD (SLACKWARE) - Ίδια με τα υπόλοιπα script σας
DB_CONFIG = {
    'user': 'djemos',
    'password': 'djemos',
    'database': 'slackel_stats',
    'unix_socket': '/var/run/mysql/mysql.sock',
    'auth_plugin': 'mysql_native_password',
    'use_pure': True
}

def get_valid_date(prompt_message):
    print(prompt_message)
    while True:
        try:
            year = int(input("  Έτος (YYYY): "))
            month = int(input("  Μήνας (1-12): "))
            day = int(input("  Ημέρα (1-31): "))
            
            chosen_date = date(year, month, day)
            return chosen_date.strftime('%Y-%m-%d')
        except ValueError:
            print("❌ Σφάλμα: Μη έγκυρη ημερομηνία ή λανθασμένοι αριθμοί. Προσπαθήστε ξανά.")

def delete_date_range():
    print("=" * 60)
    print(" ΔΙΑΔΡΑΣΤΙΚΗ ΔΙΑΓΡΑΦΗ ΕΓΓΡΑΦΩΝ ΑΠΟ ΗΜΕΡΟΜΗΝΙΑ ΣΕ ΗΜΕΡΟΜΗΝΙΑ (MARIADB)")
    print("=" * 60)

    # 1. Εισαγωγή Ημερομηνίας Έναρξης (Από)
    start_date = get_valid_date("📅 Εισάγετε Ημερομηνία Έναρξης (ΑΠΟ):")
    print("-" * 40)
    
    # 2. Εισαγωγή Ημερομηνίας Λήξης (Έως)
    while True:
        end_date = get_valid_date("📅 Εισάγετε Ημερομηνία Λήξης (ΕΩΣ):")
        if end_date >= start_date:
            break
        print("❌ Σφάλμα: Η ημερομηνία λήξης πρέπει να είναι ίδια ή μεταγενέστερη από την έναρξη!")
        print("-" * 40)

    print("=" * 60)
    print(f"⚠️ Πρόκειται να διαγραφούν ΟΛΑ τα δεδομένα από {start_date} έως {end_date}!")
    confirm = input("Είστε σίγουροι; Πληκτρολογήστε 'yes' για επιβεβαίωση: ")
    
    if confirm.lower() != 'yes':
        print("❌ Η διαγραφή ακυρώθηκε.")
        return

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Αποτυχία σύνδεσης στη MariaDB: {str(e)}")
        return
    # 3. Υπολογισμός εγγραφών που θα διαγραφούν (για ενημέρωση του χρήστη)
    # ΔΙΟΡΘΩΣΗ: Αντικατάσταση των ? με %s και χρήση DATE() για τη MariaDB
    cursor.execute("SELECT COUNT(*) FROM searches WHERE DATE(timestamp) BETWEEN %s AND %s", (start_date, end_date))
    searches_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM visits WHERE date BETWEEN %s AND %s", (start_date, end_date))
    visits_count = cursor.fetchone()[0]
    
    # 4. Εκτέλεση της διαγραφής με BETWEEN
    # ΔΙΟΡΘΩΣΗ: Αντικατάσταση των ? με %s
    cursor.execute("DELETE FROM searches WHERE DATE(timestamp) BETWEEN %s AND %s", (start_date, end_date))
    cursor.execute("DELETE FROM visits WHERE date BETWEEN %s AND %s", (start_date, end_date))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("=" * 60)
    print("🎉 Η διαγραφή ολοκληρώθηκε με επιτυχία από τη MariaDB!")
    print(f"   • Διαγράφηκαν {searches_count} αναζητήσεις (searches).")
    print(f"   • Διαγράφηκαν {visits_count} επισκέψεις (visits).")
    print("=" * 60)
    print("Ανανεώστε τη σελίδα stats.html με Ctrl+F5 για να δείτε το ενημερωμένο γράφημα.")

if __name__ == "__main__":
    delete_date_range()
