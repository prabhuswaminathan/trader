import http.server
import socketserver
import threading
from typing import Callable
import webbrowser
import urllib.parse
import logging

REDIRECT_PORT = 3030
logger = logging.getLogger(__name__)
# Shared variable to store code
auth_code = None


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    callback_method: Callable = None
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            try:
                qs = urllib.parse.parse_qs(parsed.query)
                auth_code = qs.get("code", [None])[0]
                # Show a success message to user in browser
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Authentication successful. You may close this window.</h2>")
                OAuthHandler.callback_method(auth_code)
            except Exception as e:
                logger.error(f"Error handling request: {e}")
        else:
            self.send_response(404)
            self.end_headers()

class AuthHandler:
    def run_local_server(self):
        with socketserver.TCPServer(("localhost", REDIRECT_PORT), OAuthHandler) as httpd:
            httpd.handle_request()  # handle only one request


    def get_auth_code(self, authorize_url, callback):
        OAuthHandler.callback_method = callback;
        global auth_code
        # Start local server in background thread
        server_thread = threading.Thread(target=self.run_local_server, daemon=True)
        server_thread.start()

        # Open browser to start auth flow
        logger.debug("Opening browser for authentication...")
        webbrowser.open(authorize_url)

        # Wait until code captured
        while auth_code is None:
            pass
        return auth_code
