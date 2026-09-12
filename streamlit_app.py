# Entry point for Streamlit Community Cloud
import os
import sys

# Ensure repository root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Directly run app_ui.py
app_file = os.path.join(BASE_DIR, "app_ui.py")
with open(app_file, "r", encoding="utf-8") as f:
    code = f.read()

exec(compile(code, app_file, "exec"), globals())
