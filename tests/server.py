from http.server import HTTPServer, BaseHTTPRequestHandler


__all__ = ["run"]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.log_message("\"POST %s %s\"", self.path, self.protocol_version)

        print(str(self.headers).strip())
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        if body:
            print(body)

        self.send_response(204)
        self.end_headers()

class Server(HTTPServer):
    def __init__(self, host: str = "", port: int = 8000):
        super().__init__((host, port), Handler)
    

if __name__ == "__main__":
    with Server() as server:
        host, port = server.server_address
        print(f"Server listening on {host}:{port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped")
