import os
import sys
from pyngrok import ngrok
import time

def start_tunnel():
    # Kill any existing ngrok processes to avoid conflicts
    os.system("taskkill /f /im ngrok.exe >nul 2>&1")
    
    print(" * Starting public tunnel...")
    try:
        # Open a HTTP tunnel on the default port 5000
        # If you have an authToken, you can set it with: ngrok.set_auth_token("YOUR_TOKEN")
        # Custom Domain requires Paid Plan. Reverting to random for Free Plan.
        public_url = ngrok.connect(5000).public_url
        print(f"\n========================================================")
        print(f" * YOUR LIVE URL IS: {public_url}")
        print(f"========================================================\n")
        print(" * Keep this terminal open to keep the link active.")
        print(" * Press Ctrl+C to close the tunnel.")
        
        # Keep the process alive
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error starting tunnel: {e}")
        print("\nNote: Ngrok might require an auth token for longer sessions.")
        print("Sign up at https://dashboard.ngrok.com/signup to get one.")

if __name__ == "__main__":
    start_tunnel()
