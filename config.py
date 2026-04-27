import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "forensic_signatures.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILE_SIZE_SCAN = 500 * 1024 * 1024  # 500MB — skip larger in dir scan
MAX_DIR_FILES = 500

CHUNK_SIZE = 65536  # 64KB

# inorder to scan outside of the app directory, we need to specify allowed roots-   
# this is a security measure to prevent scanning arbitrary paths on the server.
ALLOWED_SCAN_ROOTS = [
    
    # i created a oevidence folder within the
    # same directory and allowed it for scanning, change it acc for yourself
    r"C:\Users\HP\Desktop\forenscan\evidence",
]

BLOCKED_UPLOAD_EXTENSIONS = {'.php', '.py', '.rb', '.sh', '.pl', '.cgi', '.asp', '.aspx', '.exe', '.bat', '.cmd', '.ps1'}

FORENSCAN_VERSION = "1.0"