#!/usr/bin/env python3
"""Entry point script for DocuCheck application."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
script_dir = os.path.dirname(__file__) or "."
dotenv_path = os.path.join(script_dir, ".env")

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Import and run the main CLI
from docucheck.__main__ import main

if __name__ == "__main__":
    main()