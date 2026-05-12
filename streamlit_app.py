# streamlit_app.py
# Thin launcher so Streamlit Cloud can find the entry point at the repo root.
# All real logic lives in src/seo_log_auditor/_app/app.py
import sys
import os

# Make the src package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Run the app
exec(open(os.path.join(os.path.dirname(__file__), "src", "seo_log_auditor", "_app", "app.py")).read())
