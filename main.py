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
            "dst_mac": data["dst_mac"],
            "packet": data["packet"]
        }
        print(f"Data Link Layer: Frame | {data['src_mac']} → {data['dst_mac']}")
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
# PACKET DELIVERED SIGNAL
# =========================

class PacketDelivered(Exception):
    pass


# =========================
# HELPERS
# =========================

def random_mac():
    return ':'.join(f'{random.randint(0, 255):02X}' for _ in range(6))


# =========================
# DEVICE CLASSES
# =========================

class Device:
    def __init__(self, name):
        self.name = name
        self.mac = random_mac()
        self.stack = build_stack()
        self.connections = []
        self.home_router = None

    def connect(self, other):
        if other not in self.connections:
            self.connections.append(other)
            other.connections.append(self)

    def send(self, data, destination):
        print(f"\n\n===== {self.name} SENDING MESSAGE TO {destination.name} =====")
        print("Starting Encapsulation...\n")
        self.stack.process(data)
        print("\n--- TRANSMISSION START ---")
        try:
            self.forward(data, destination, visited=set())
        except PacketDelivered:
            pass

    def forward(self, data, destination, visited):
        if self in visited:
            return
        visited.add(self)

        print(f"\n[{self.name}] RECEIVED FRAME")
        print(f"MAC: {data['frame']['src_mac']} → {data['frame']['dst_mac']}")
        print(f"IP: {data['packet']['src_ip']} → {data['packet']['dst_ip']}")

        if self == destination:
            print(f"\n {self.name} ACCEPTED PACKET (DESTINATION REACHED)")
            raise PacketDelivered

        if not self.connections:
            print("No connections. Packet dropped.")
            return

        self.handle_forwarding(data, destination, visited)

    def handle_forwarding(self, data, destination, visited):
        for conn in self.connections:
            if isinstance(conn, (Switch, Hub)) and conn not in visited:
                print(f"{self.name} forwarding to {conn.name}")
                conn.forward(data, destination, visited)
                return
        next_hop = random.choice(self.connections)
        print(f"{self.name} forwarding to {next_hop.name}")
        next_hop.forward(data, destination, visited)


class Router(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (ROUTER): Routing using IP")

        # Check if destination is on a directly connected segment
        for conn in self.connections:
            if isinstance(conn, (Switch, Hub)) and conn not in visited:
                for device in conn.connections:
                    if device == destination:
                        print(f"{self.name} → {conn.name} (destination on this segment)")
                        conn.forward(data, destination, visited)
                        return

        # Route toward destination's home router
        dst_router = destination.home_router
        if dst_router and dst_router not in visited:
            if dst_router in self.connections:
                print(f"{self.name} → {dst_router.name} (direct route)")
                dst_router.forward(data, destination, visited)
                return
            for conn in self.connections:
                if isinstance(conn, Router) and conn not in visited:
                    if dst_router in conn.connections:
                        print(f"{self.name} → {conn.name} (via neighbor)")
                        conn.forward(data, destination, visited)
                        return

        # Forward to any unvisited neighboring router
        router_neighbors = [c for c in self.connections if isinstance(c, Router) and c not in visited]
        if router_neighbors:
            next_hop = random.choice(router_neighbors)
            print(f"{self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited)
            return

        # Last resort: any unvisited connection
        unvisited = [c for c in self.connections if c not in visited]
        if unvisited:
            next_hop = random.choice(unvisited)
            print(f"{self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited)


class Switch(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (SWITCH): Forwarding using MAC table")

        # Check if destination is directly connected
        if destination in self.connections and destination not in visited:
            print(f"{self.name} → {destination.name} (MAC match)")
            destination.forward(data, destination, visited)
            return

        # Forward up to router
        for conn in self.connections:
            if isinstance(conn, Router) and conn not in visited:
                print(f"{self.name} → {conn.name}")
                conn.forward(data, destination, visited)
                return

        # Fallback: any unvisited connection
        unvisited = [c for c in self.connections if c not in visited]
        if unvisited:
            next_hop = random.choice(unvisited)
            print(f"{self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited)


class Hub(Device):
    def handle_forwarding(self, data, destination, visited):
        print(f"{self.name} (HUB): Broadcasting to all ports")

        # Check if destination is directly connected first
        if destination in self.connections and destination not in visited:
            print(f"{self.name} → {destination.name} (destination on this segment)")
            destination.forward(data, destination, visited)
            return

        # Broadcast to all unvisited connections
        for device in self.connections:
            if device not in visited:
                print(f"{self.name} → {device.name}")
                device.forward(data, destination, visited)


# =========================
# NETWORK SETUP
# =========================

def build_network():
    num_routers = random.randint(6, 10)
    routers = [Router(f"Router{i}") for i in range(num_routers)]

    # Each router gets between 2-5 peripherals (mix of switches and hubs)
    # We'll track how many of each we need first
    router_peripheral_counts = [random.randint(2, 5) for _ in range(num_routers)]
    total_peripherals = sum(router_peripheral_counts)

    # Randomly split peripherals into switches and hubs
    num_switches = random.randint(total_peripherals // 3, (2 * total_peripherals) // 3)
    num_hubs = total_peripherals - num_switches

    switches = [Switch(f"Switch{i}") for i in range(num_switches)]
    hubs     = [Hub(f"Hub{i}") for i in range(num_hubs)]
    peripherals_pool = switches + hubs
    random.shuffle(peripherals_pool)

    # Total devices = total_peripherals * 3
    total_devices = total_peripherals * 3
    devices = [Device(f"PC{i}") for i in range(59, 59 + total_devices)]

    pi = 0  # peripheral index
    di = 0  # device index

    for i, router in enumerate(routers):
        # Ring connection
        router.connect(routers[(i + 1) % num_routers])

        # Assign this router's peripherals
        count = router_peripheral_counts[i]
        for _ in range(count):
            peripheral = peripherals_pool[pi]
            pi += 1
            router.connect(peripheral)
            for _ in range(3):
                devices[di].home_router = router
                peripheral.connect(devices[di])
                di += 1

    # Cross-links between opposite routers
    for i in range(num_routers // 2):
        routers[i].connect(routers[i + num_routers // 2])

    print(f"Network built: {num_routers} routers, {num_switches} switches, "
          f"{num_hubs} hubs, {total_devices} end devices")

    return devices


# =========================
# DATA GENERATION
# =========================

def generate_data(sender, receiver):
    return {
        "host": "example.com",
        "path": "/",
        "src_ip": f"192.168.1.{random.randint(2, 254)}",
        "dst_ip": f"93.184.216.{random.randint(2, 254)}",
        "src_port": random.randint(40000, 60000),
        "dst_port": 80,
        "src_mac": sender.mac,
        "dst_mac": receiver.mac
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

        data = generate_data(sender, receiver)
        sender.send(data, receiver)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    simulate()