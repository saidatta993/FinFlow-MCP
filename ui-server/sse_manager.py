import asyncio
import json

class SSEManager:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.queues: list[asyncio.Queue] = []
        self.loop = loop

    def connect(self) -> asyncio.Queue:
        """Adds a new client queue and returns it."""
        queue = asyncio.Queue()
        self.queues.append(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue):
        """Removes a client queue."""
        if queue in self.queues:
            self.queues.remove(queue)

    def broadcast(self, data: dict):
        """
        Puts JSON-serialized data into all active client queues.
        Thread-safe method, can be called from the MCP server thread.
        """
        message = json.dumps(data)
        
        def _put_in_queues():
            for queue in self.queues:
                queue.put_nowait(message)
                
        # Schedule the putting of messages on the main async event loop
        # This allows thread-safe communication from the main thread (MCP)
        # to the background thread (FastAPI).
        self.loop.call_soon_threadsafe(_put_in_queues)
