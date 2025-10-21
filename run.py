#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# --- NEW DEBUGGING BLOCK ---
print("--- [DEBUG] ---")
print(f"Current Working Directory: {os.getcwd()}")
print(f"File path of this script: {__file__}")

# Explicitly find the .env file in the same directory as this script
script_dir = os.path.dirname(__file__)
dotenv_path = os.path.join(script_dir, '.env')

if not dotenv_path:
    dotenv_path = '.env' # Fallback to current working dir

print(f"Looking for .env file at: {dotenv_path}")

if os.path.exists(dotenv_path):
    print("Found .env file!")
else:
    print("Error: .env file NOT FOUND at that path.")

# Try to load it
load_success = load_dotenv(dotenv_path)
print(f"dotenv load_dotenv() reported: {load_success}")

# Check for the key *after* loading
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print("SUCCESS: GEMINI_API_KEY is loaded.")
else:
    print("FAILURE: GEMINI_API_KEY is still NOT FOUND after load.")

print("--- [END DEBUG] ---")
# -------------------------


"""
Main entry point for the DocuCheck application.
This allows the package to be run as a script.
"""
from Docucheck import __main__ # <-- Now __main__ imports with the key already loaded

if __name__ == "__main__":
    __main__.main()