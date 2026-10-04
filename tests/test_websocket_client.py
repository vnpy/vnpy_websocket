import json

from vnpy_websocket.websocket_client import WebsocketClient


class PacketClient(WebsocketClient):
    def __init__(self) -> None:
        super().__init__()
        self.packets: list[dict] = []

    def on_packet(self, packet: dict) -> None:
        self.packets.append(packet)


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> None:
        self.sent.append(text)


def test_send_packet_encodes_json() -> None:
    client: WebsocketClient = WebsocketClient()
    socket: FakeSocket = FakeSocket()
    client.wsapp = socket  # type: ignore[assignment]
    packet: dict = {"op": "subscribe", "symbol": "rb2510.SHFE"}

    client.send_packet(packet)

    assert client.active is False
    assert client.host == ""
    assert socket.sent == [json.dumps(packet)]
    assert json.loads(socket.sent[0]) == packet


def test_on_message_decodes_packet_into_callback_state() -> None:
    client: PacketClient = PacketClient()
    message: str = '{"op": "subscribe", "symbol": "rb2510.SHFE"}'

    client.on_message(message)

    assert client.packets == [{"op": "subscribe", "symbol": "rb2510.SHFE"}]
    assert client.wsapp is None
    assert client.active is False
