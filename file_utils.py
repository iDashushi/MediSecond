import base64

def encode(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def decode(data_b64: str, path: str):
    with open(path, "wb") as f:
        f.write(base64.b64decode(data_b64.encode("utf-8")))
