#!/usr/bin/env python3
"""
Launch Script - Run tests and start the application
"""

import os
import sys
import subprocess
import time

def launch_app():
    """Launch the Streamlit application"""
    print("\n🚀 Launching the application...")
    
    app_script = os.path.join(os.path.dirname(__file__), 'app.py')
    
    # Start the app using a subprocess
    return subprocess.Popen(['streamlit', 'run', app_script])

def main():
    """Main function"""
    print("🏥 Evacuation Center Site Selection Decision Support System Launch Tool")
    print("=" * 50)
    
    # Launch the application
    app_process = launch_app()
    
    try:
        print("\nThe application is running. Press Ctrl+C to exit.")
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down the application...")
        app_process.terminate()
        app_process.wait()
        print("Closed. Thank you for using!")

if __name__ == "__main__":
    main()
