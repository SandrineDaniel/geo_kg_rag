"""
run_ui.py: Entry point to launch the Streamlit UI for the RAG chatbot.
=================
command to run:
    python -m streamlit run scripts/run_ui.py
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.rag_ui_app import main

if __name__ == "__main__":
    main()