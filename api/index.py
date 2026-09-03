import sys
import os

# Add root directory to sys.path for Vercel Serverless Function imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
