#!/usr/bin/env python3
"""
Standalone script to permanently delete a CADEN license and its logs from the database.
Usage: python3 delete_license.py <device_id_or_license_id>
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "caden.db")

def delete_license(identifier):
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if identifier is a numeric license ID or a device_id string
    if identifier.isdigit():
        lic = cursor.execute("SELECT id, device_id FROM LICENSES WHERE id=?", (int(identifier),)).fetchone()
    else:
        lic = cursor.execute("SELECT id, device_id FROM LICENSES WHERE device_id=?", (identifier,)).fetchone()
        
    if not lic:
        print(f"No license found for identifier: {identifier}")
        conn.close()
        sys.exit(1)
        
    lic_id, device_id = lic
    print(f"Deleting License ID {lic_id} (Device: {device_id})...")
    
    cursor.execute("DELETE FROM LICENSES WHERE id=?", (lic_id,))
    cursor.execute("DELETE FROM UNIFIED_LOGS WHERE device_id=?", (device_id,))
    cursor.execute("DELETE FROM REMINDER_LOG WHERE license_id=?", (lic_id,))
    
    conn.commit()
    conn.close()
    print(f"✅ Successfully deleted license {lic_id} and all associated logs.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 delete_license.py <device_id_or_license_id>")
        sys.exit(1)
    delete_license(sys.argv[1])
