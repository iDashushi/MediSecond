import socket
import json
import logging
import os

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=os.path.join("logs", "client.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("medisecond.client")

class Net:
    HOST = "127.0.0.1"
    PORT = 5555
    TIMEOUT = 20

    def _recv_exact(self, sock, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed by server")
            data += chunk
        return data

    def send(self, data: dict):
        action = data.get("action", "unknown")
        logger.info("Sending request: %s", action)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.TIMEOUT)
                s.connect((self.HOST, self.PORT))

                raw = json.dumps(data).encode("utf-8")
                s.sendall(len(raw).to_bytes(4, "big") + raw)

                length_bytes = self._recv_exact(s, 4)
                size = int.from_bytes(length_bytes, "big")
                if size <= 0 or size > 200_000_000:
                    raise ValueError(f"Invalid response size: {size}")

                payload = self._recv_exact(s, size)
                text = payload.decode("utf-8").strip()
                if not text:
                    raise ValueError("Empty response from server")

                response = json.loads(text)
                logger.info("Response for %s: ok=%s", action, response.get("ok"))
                return response
        except Exception as e:
            logger.exception("Network error during %s: %s", action, e)
            raise
