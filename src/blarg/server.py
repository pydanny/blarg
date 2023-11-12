import functools
import http.server
import os
import socketserver
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def build_handler(directory: Path):
    return functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)


class MyHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        elif event.event_type in ["created", "modified"]:
            print(f"Reloading server due to file change: {event.src_path}")
            os._exit(0)


def run_server(site: Path, port: int = 8000):
    with socketserver.TCPServer(("", port), build_handler(site)) as httpd:
        print(f"Serving on port {port}")
        httpd.serve_forever()


def server(site: Path, port: int = 8000):
    # Set up the file system event handler
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, site, recursive=True)
    observer.start()

    try:
        # Run the HTTP server
        run_server(site=site, port=port)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
