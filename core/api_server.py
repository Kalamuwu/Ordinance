import threading
import http.server
import json

import ordinance.writer

from typing import Callable, Any, Optional, Tuple


class ApiRequestHandler(http.server.BaseHTTPRequestHandler):
    _core_ref = None

    def send_json(self, obj: Any):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        dat = json.dumps(obj)
        self.wfile.write(dat.encode() + b'\n')
    
    def send_404(self, path: Optional[str] = ""):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        if not path: path = self.path
        self.wfile.write(f"Error 404\nUnknown API path '{path}'".encode())

    def do_GET(self):
        if self.path.endswith("/"): self.path = self.path[:-1]
        
        if self.path == "/status":
            self.send_json(self.__class__._core_ref._apiserver_status())
        
        elif self.path == "/status/plugin":
            self.send_json(self.__class__._core_ref._apiserver_plugins())
        
        elif self.path.startswith("/status/plugin/"):
            qname = self.path[15:]
            if not self.__class__._core_ref.is_known_plugin(qname):
                self.send_404()
            else:
                self.send_json(self.__class__._core_ref._apiserver_status_single_plugin(qname))
        
        elif self.path == "/status/writer":
            self.send_json(self.__class__._core_ref._apiserver_writers())
        
        else: self.send_404()


class ApiServerThread(threading.Thread):
    def __init__(self, bind: Tuple[str, int], poll_interval: float = 1.0):
        super().__init__(daemon=True, name="OrdinanceApiServer_Thread")
        self.should_run = True
        self.bind = bind
        self.server = http.server.ThreadingHTTPServer(
            bind,
            ApiRequestHandler)
        self.address = ':'.join(str(c) for c in self.server.server_address)
        self.server.timeout = poll_interval
        self.server.daemon_threads = True
    
    def run(self):
        ordinance.writer.success(f"API server: online. Using {self.address}")
        while self.should_run:
            self.server.handle_request()


class ApiServer:
    def __init__(self, bind: Tuple[str, int], poll_interval: float = 1.0):
        self.interface = bind[0] if bind[0] else '127.0.0.1'
        self.port      = bind[1] if bind[1] else 0   # port 0 lets the OS assign a free port
        self.poll_interval = poll_interval
        self.server: ApiServerThread = None
        self.state_lock = threading.Lock()
    
    @property
    def running(self) -> bool:
        with self.state_lock:
            return (self.server is not None)

    def start(self):
        with self.state_lock:
            if self.server is not None: return
            try:
                self.server = ApiServerThread((self.interface, self.port), self.poll_interval)
                self.server.start()
            except Exception as e:
                ordinance.writer.critical("Failed to start API http_server, error:")
                ordinance.writer.critical(e)
    
    def stop(self):
        with self.state_lock:
            if self.server is None: return
            self.server.should_run = False
            self.server.join()
            self.server = None
