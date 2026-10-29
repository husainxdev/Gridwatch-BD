"""In-memory loopback SMTP sink for disposable browser tests. No external delivery."""

import json
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import StreamRequestHandler, ThreadingTCPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse


class Mailbox:
    def __init__(self):
        self.messages = {}
        self.lock = Lock()
        mailbox = self

        class SMTP(StreamRequestHandler):
            def handle(self):
                self.connection.settimeout(15)
                self.wfile.write(b"220 isolated QA SMTP\r\n")
                data = None
                while line := self.rfile.readline(65537):
                    if data is not None:
                        if line == b".\r\n":
                            msg = BytesParser(policy=policy.default).parsebytes(
                                b"".join(data)
                            )
                            with mailbox.lock:
                                mailbox.messages[str(msg["To"])] = msg.get_content()
                            data = None
                            self.wfile.write(b"250 accepted in memory\r\n")
                        else:
                            data.append(line[1:] if line.startswith(b"..") else line)
                        continue
                    command = line.split(b" ", 1)[0].strip().upper()
                    if command in (
                        b"EHLO",
                        b"HELO",
                        b"MAIL",
                        b"RCPT",
                        b"RSET",
                        b"NOOP",
                    ):
                        self.wfile.write(b"250 OK\r\n")
                    elif command == b"DATA":
                        data = []
                        self.wfile.write(b"354 End with dot\r\n")
                    elif command == b"QUIT":
                        self.wfile.write(b"221 bye\r\n")
                        return
                    else:
                        self.wfile.write(b"502 unsupported\r\n")

        class HTTP(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # Reset links must never enter request logs.

            def do_GET(self):
                recipient = parse_qs(urlparse(self.path).query).get("recipient", [""])[
                    0
                ]
                with mailbox.lock:
                    content = mailbox.messages.get(recipient)
                payload = json.dumps({"text": content}).encode()
                self.send_response(200 if content else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

        self.smtp = ThreadingTCPServer(("127.0.0.1", 0), SMTP)
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), HTTP)
        self.smtp.daemon_threads = True
        self.http.daemon_threads = True
        self.threads = []
        for server in (self.smtp, self.http):
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        for server in (self.smtp, self.http):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=2)
        self.messages.clear()
