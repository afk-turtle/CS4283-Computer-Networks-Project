import random
import uuid

# =========================
# OSI LAYERS
# =========================

class Layer:
    def __init__(self, next_layer=None):
        self.next_layer = next_layer

    def process(self, data):
        raise NotImplementedError


class ApplicationLayer(Layer):
    def process(self, data):
        data["app_data"] = f"GET {data['path']} HTTP/1.1 | Host: {data['host']}"
        print("Application Layer: HTTP Request Created")

        if self.next_layer:
            self.next_layer.process(data)


class PresentationLayer(Layer):
    def process(self, data):
        data["encoded"] = data["app_data"].encode("utf-8")
        print("Presentation Layer: Data Encoded")

        if self.next_layer:
            self.next_layer.process(data)


class SessionLayer(Layer):
    def process(self, data):
        data["session_id"] = str(uuid.uuid4())
        print(f"Session Layer: Session ID = {data['session_id']}")

        if self.next_layer:
            self.next_layer.process(data)


class TransportLayer(Layer):
    def process(self, data):
        data["segment"] = {
            "src_port": data["src_port"],
            "dst_port": data["dst_port"],
            "payload": data["encoded"]
        }
        print(f"Transport Layer: TCP Segment | {data['src_port']} → {data['dst_port']}")

        if self.next_layer:
            self.next_layer.process(data)


class NetworkLayer(Layer):
    def process(self, data):
        data["packet"] = {
            "src_ip": data["src_ip"],
            "dst_ip": data["dst_ip"],
            "segment": data["segment"]
        }
        print(f"Network Layer: IP Packet | {data['src_ip']} → {data['dst_ip']}")

        if self.next_layer:
            self.next_layer.process(data)


class DataLinkLayer(Layer):
    def process(self, data):
        data["frame"] = {
            "src_mac": data["src_mac"],
            "dst_mac": "FF:FF:FF:FF:FF:FF",
            "packet": data["packet"]
        }
        print(f"Data Link Layer: Frame | {data['src_mac']} → FF:FF:FF:FF:FF:FF")

        if self.next_layer:
            self.next_layer.process(data)


class PhysicalLayer(Layer):
    def process(self, data):
        print("Physical Layer: Converting to bits...")

        frame_str = str(data["frame"])
        bits = ''.join(format(b, '08b') for b in frame_str.encode())

        print("Encapsulation: HTTP → TCP → IP → Ethernet → Bits")
        print("First 64 bits:", bits[:64], "...\n")


def build_stack():
    return ApplicationLayer(
        PresentationLayer(
            SessionLayer(
                TransportLayer(
                    NetworkLayer(
                        DataLinkLayer(
                            PhysicalLayer()
                        )
                    )
                )
            )
        )
    )

# =========================
# DEVICE CLASSES
# =========================

class Device:
    def __init__(self, name):
        self.name = name
        self.stack = build_stack()
        self.connections = []

    def connect(self, other):
        if other not in self.connections:
            self.connections.append(other)
            other.connections.append(self)

    def send(self, data, destination):
        print(f"\n\n===== {self.name} SENDING MESSAGE TO {destination.name} =====")
        print("Starting Encapsulation...\n")
        self.stack.process(data)

        print("\n--- TRANSMISSION START ---")
        self.forward(data, destination, visited=set())

    def forward(self, data, destination, visited):
        if self in visited:
            return
        visited.add(self)

        print(f"\n[{self.name}] RECEIVED FRAME")
        print(f"MAC: {data['frame']['src_mac']} → {data['frame']['dst_mac']}")
        print(f"IP: {data['packet']['src_ip']} → {data['packet']['dst_ip']}")

        if self == destination:
            print(f"\n🎯 {self.name} ACCEPTED PACKET (DESTINATION REACHED)")
            return

        if not self.connections:
            print("No connections. Packet dropped.")
            return

        self.handle_forwarding(data, destination, visited)

    def handle_forwarding(self, data, destination, visited):
        next_hop = random.choice(self.connections)
        print(f"{self.name} forwarding to {next_hop.name}")
        next_hop.forward(data, destination, visited)


class Router(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (ROUTER): Routing using IP")
        next_hop = random.choice(self.connections)
        print(f"{self.name} → {next_hop.name}")
        next_hop.forward(data, destination, visited)


class Switch(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (SWITCH): Forwarding using MAC table")
        next_hop = random.choice(self.connections)
        print(f"{self.name} → {next_hop.name}")
        next_hop.forward(data, destination, visited)


class Hub(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (HUB): Broadcasting to all devices")
        for device in self.connections:
            if device not in visited:
                print(f"{self.name} → {device.name}")
                device.forward(data, destination, visited)


# =========================
# NETWORK SETUP
# =========================

def build_network():
    routers = [Router(f"Router{i}") for i in range(6)]
    switches = [Switch(f"Switch{i}") for i in range(10)]
    hubs = [Hub(f"Hub{i}") for i in range(10)]
    devices = [Device(f"PC{i}") for i in range(59, 91)]

    # Connect routers
    for r in routers:
        for _ in range(random.randint(2, 5)):
            r.connect(random.choice(switches + hubs))

    # Connect switches/hubs to devices
    for s in switches + hubs:
        for _ in range(3):
            s.connect(random.choice(devices))

    return devices


# =========================
# DATA GENERATION
# =========================

def generate_data():
    return {
        "host": "example.com",
        "path": "/",
        "src_ip": f"192.168.1.{random.randint(2,254)}",
        "dst_ip": "93.184.216.34",
        "src_port": random.randint(40000, 60000),
        "dst_port": 80,
        "src_mac": "AA:BB:CC:DD:EE:FF"
    }


# =========================
# SIMULATION
# =========================

def simulate():
    devices = build_network()

    print("\n===== NETWORK SIMULATION START =====")

    for i in range(10):
        sender = random.choice(devices)
        receiver = random.choice(devices)

        while sender == receiver:
            receiver = random.choice(devices)

        data = generate_data()
        sender.send(data, receiver)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    simulate()