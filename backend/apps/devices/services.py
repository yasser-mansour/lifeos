import base64
import io
import json
import socket

import qrcode


def local_lan_ip() -> str:
    """Best-effort LAN IP so the pairing QR code can tell Android where to
    find this Mac. Falls back to localhost if there's no network — the user
    can still enter an IP manually (spec §73: "provide fallback manual
    IP/endpoint if discovery fails")."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def pairing_payload(pairing_token, port=8420):
    return {
        "lifeos_pairing": 1,
        "token": pairing_token.token,
        "host": local_lan_ip(),
        "port": port,
        "expires_at": pairing_token.expires_at.isoformat(),
    }


def pairing_qr_data_uri(pairing_token, port=8420) -> str:
    payload = json.dumps(pairing_payload(pairing_token, port))
    img = qrcode.make(payload, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
