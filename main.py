import random
import uuid

# ============================================================
# ======================= OSI LAYERS ==========================
# ============================================================

class Layer:
    def __init__(self, next_layer=None):
        self.next_layer = next_layer

    def process(self, data):
        raise NotImplementedError


# -------------------- APPLICATION LAYER ---------------------
class ApplicationLayer(Layer):
    def process(self, data):
        v = data.get("verbose", True)

        if data.get("msg_type") == "COMBAT":
            data["app_data"] = (
                f"COMBAT/{data['combat_type']} | "
                f"From: {data['host']} | "
                f"Payload: {data['combat_payload']}"
            )
            if v:
                print(f"Application Layer: Combat Message Created [{data['combat_type']}]")
        else:
            data["app_data"] = f"GET {data['path']} HTTP/1.1 | Host: {data['host']}"
            if v:
                print("Application Layer: HTTP Request Created")

        if self.next_layer:
            self.next_layer.process(data)


# -------------------- PRESENTATION LAYER --------------------
class PresentationLayer(Layer):
    def process(self, data):
        data["encoded"] = data["app_data"].encode("utf-8")
        if data.get("verbose", True):
            print("Presentation Layer: Data Encoded")

        if self.next_layer:
            self.next_layer.process(data)


# ---------------------- SESSION LAYER -----------------------
class SessionLayer(Layer):
    def process(self, data):
        data["session_id"] = str(uuid.uuid4())
        if data.get("verbose", True):
            print(f"Session Layer: Session ID = {data['session_id']}")

        if self.next_layer:
            self.next_layer.process(data)


# --------------------- TRANSPORT LAYER ----------------------
class TransportLayer(Layer):
    def process(self, data):
        data["segment"] = {
            "src_port": data["src_port"],
            "dst_port": data["dst_port"],
            "payload": data["encoded"]
        }

        if data.get("verbose", True):
            print(f"Transport Layer: TCP Segment | {data['src_port']} → {data['dst_port']}")

        if self.next_layer:
            self.next_layer.process(data)


# ---------------------- NETWORK LAYER -----------------------
class NetworkLayer(Layer):
    def process(self, data):
        data["packet"] = {
            "src_ip": data["src_ip"],
            "dst_ip": data["dst_ip"],
            "segment": data["segment"]
        }

        if data.get("verbose", True):
            print(f"Network Layer: IP Packet | {data['src_ip']} → {data['dst_ip']}")

        if self.next_layer:
            self.next_layer.process(data)


# -------------------- DATA LINK LAYER -----------------------
class DataLinkLayer(Layer):
    def process(self, data):
        data["frame"] = {
            "src_mac": data["src_mac"],
            "dst_mac": data["dst_mac"],
            "packet": data["packet"]
        }

        if data.get("verbose", True):
            print(f"Data Link Layer: Frame | {data['src_mac']} → {data['dst_mac']}")

        if self.next_layer:
            self.next_layer.process(data)


# -------------------- PHYSICAL LAYER ------------------------
class PhysicalLayer(Layer):
    def process(self, data):
        frame_str = str(data["frame"])
        bits = ''.join(format(b, '08b') for b in frame_str.encode())

        if data.get("verbose", True):
            print("Physical Layer: Converting to bits...")
            print("Encapsulation: Combat Message → TCP → IP → Ethernet → Bits")
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


# ============================================================
# ===================== COMBAT SYSTEM =========================
# ============================================================

MOVES = ["ATTACK_RED", "ATTACK_BLUE", "ATTACK_GREEN", "BOLSTER_DEFENSE", "BOLSTER_ATTACK"]


class Fighter:
    def __init__(self, owner_name):
        self.owner = owner_name
        self.red_hp = 20
        self.blue_hp = 20
        self.green_hp = 20
        self.attack = 6
        self.defense = 0
        self.alive = True
        self.wins = 0

    def is_dead(self):
        return self.red_hp <= 0 or self.blue_hp <= 0 or self.green_hp <= 0

    def serialize(self):
        return f"R:{self.red_hp},B:{self.blue_hp},G:{self.green_hp},ATK:{self.attack},DEF:{self.defense}"

    def summary(self):
        status = "ALIVE" if self.alive else "DEAD"
        return f"{self.owner} [{status}] | HP R:{self.red_hp}/B:{self.blue_hp}/G:{self.green_hp} | ATK:{self.attack} DEF:{self.defense} | Wins:{self.wins}"

    def choose_move(self, opponent_state: dict) -> str:
        opp_r = opponent_state.get("red_hp", 20)
        opp_b = opponent_state.get("blue_hp", 20)
        opp_g = opponent_state.get("green_hp", 20)

        own_min = min(self.red_hp, self.blue_hp, self.green_hp)

        if own_min <= 6 and self.defense == 0 and random.random() < 0.6:
            return "BOLSTER_DEFENSE"

        if self.attack < 8 and own_min > 12 and random.random() < 0.3:
            return "BOLSTER_ATTACK"

        return min({
            "ATTACK_RED": opp_r,
            "ATTACK_BLUE": opp_b,
            "ATTACK_GREEN": opp_g
        }, key=lambda k: {
            "ATTACK_RED": opp_r,
            "ATTACK_BLUE": opp_b,
            "ATTACK_GREEN": opp_g
        }[k])

    def receive_attack(self, channel: str, raw_damage: int):
        actual = max(0, raw_damage - self.defense)
        if channel == "RED":
            self.red_hp -= actual
        elif channel == "BLUE":
            self.blue_hp -= actual
        elif channel == "GREEN":
            self.green_hp -= actual
        return actual

    def apply_own_move(self, move: str):
        if move == "BOLSTER_DEFENSE":
            self.defense = min(1, self.defense + 1)
        elif move == "BOLSTER_ATTACK":
            self.attack += 1


class PacketDelivered(Exception):
    pass


# ============================================================
# ===================== NETWORK HELPERS =======================
# ============================================================

def random_mac():
    return ':'.join(f'{random.randint(0,255):02X}' for _ in range(6))


def generate_data(sender, receiver, msg_type="HTTP",
                  combat_type=None, combat_payload=None, verbose=True):
    base = {
        "host": receiver.name,
        "path": "/",
        "src_ip": f"192.168.{random.randint(0,9)}.{random.randint(2,254)}",
        "dst_ip": f"10.0.{random.randint(0,9)}.{random.randint(2,254)}",
        "src_port": random.randint(40000,60000),
        "dst_port": 80,
        "src_mac": sender.mac,
        "dst_mac": receiver.mac,
        "msg_type": msg_type,
        "verbose": verbose,
    }

    if msg_type == "COMBAT":
        base["combat_type"] = combat_type
        base["combat_payload"] = combat_payload

    return base


# ============================================================
# ======================== DEVICES ============================
# ============================================================

class Device:
    def __init__(self, name):
        self.name = name
        self.mac = random_mac()
        self.stack = build_stack()
        self.connections = []
        self.home_router = None
        self.fighter = Fighter(name)

    def connect(self, other):
        if other not in self.connections:
            self.connections.append(other)
            other.connections.append(self)

    def send(self, data, destination, verbose=True):
        if verbose:
            print("\n" + "="*60)
            print(f"{self.name} → {destination.name} [{data.get('msg_type')}]")
            print("="*60)
            print("Starting Encapsulation...\n")

        self.stack.process(data)

        if verbose:
            print("\n--- Transmission Starting ---")

        try:
            self.forward(data, destination, set(), verbose)
        except PacketDelivered:
            pass

    def forward(self, data, destination, visited, verbose):
        if self in visited:
            return
        visited.add(self)

        if verbose:
            print(f"[{self.name}] RECEIVED FRAME | {data['packet']['src_ip']} → {data['packet']['dst_ip']}")

        if self == destination:
            if verbose:
                print(f"   {self.name} ACCEPTED PACKET (DESTINATION REACHED)\n")
            raise PacketDelivered

        self.handle_forwarding(data, destination, visited, verbose)

    def handle_forwarding(self, data, destination, visited, verbose):
        for conn in self.connections:
            if conn not in visited:
                if verbose:
                    print(f"  {self.name} → {conn.name}")
                conn.forward(data, destination, visited, verbose)
                return


class Router(Device):
    def handle_forwarding(self, data, destination, visited, verbose):
        if verbose:
            print(f"  {self.name} (ROUTER): Routing using IP")

        for conn in self.connections:
            if conn not in visited:
                if verbose:
                    print(f"  {self.name} → {conn.name}")
                conn.forward(data, destination, visited, verbose)
                return


class Switch(Device):
    def handle_forwarding(self, data, destination, visited, verbose):
        if verbose:
            print(f"  {self.name} (SWITCH): Forwarding using MAC table")

        for conn in self.connections:
            if conn not in visited:
                conn.forward(data, destination, visited, verbose)
                return


class Hub(Device):
    def handle_forwarding(self, data, destination, visited, verbose):
        if verbose:
            print(f"  {self.name} (HUB): Broadcasting")

        for conn in self.connections:
            if conn not in visited:
                conn.forward(data, destination, visited, verbose)


# ============================================================
# ====================== COMBAT LOGIC =========================
# ============================================================

def do_combat(attacker, defender):
    af, df = attacker.fighter, defender.fighter

    print("\n" + "─"*60)
    print(f"⚔ COMBAT: {attacker.name} vs {defender.name}")
    print("─"*60)

    turn, other = attacker, defender
    round_num = 0

    while True:
        round_num += 1
        tf, of = turn.fighter, other.fighter

        move = tf.choose_move({
            "red_hp": of.red_hp,
            "blue_hp": of.blue_hp,
            "green_hp": of.green_hp
        })

        if move.startswith("ATTACK"):
            channel = move.split("_")[1]
            dmg = random.randint(1, tf.attack)
            of.receive_attack(channel, dmg)

        tf.apply_own_move(move)

        if of.is_dead():
            tf.wins += 1
            of.alive = False
            print(f"🏆 {turn.name} WINS")
            return

        turn, other = other, turn


# ============================================================
# ===================== TOURNAMENT ============================
# ============================================================

def run_tournament(devices):
    alive = devices[:]

    while len(alive) > 1:
        random.shuffle(alive)
        next_round = []

        for i in range(0, len(alive), 2):
            if i+1 < len(alive):
                a, b = alive[i], alive[i+1]
                do_combat(a, b)
                next_round.append(a if a.fighter.alive else b)
            else:
                next_round.append(alive[i])

        alive = [d for d in next_round if d.fighter.alive]

    return alive[0]


# ============================================================
# ================= VICTORY BROADCAST ========================
# ============================================================

def broadcast_victory(champion, devices):
    print("\n🏁 CHAMPION:", champion.name)

    msg = f"VICTORY | {champion.fighter.serialize()}"

    for d in devices:
        if d != champion:
            champion.send(
                generate_data(champion, d, "COMBAT", "VICTORY", msg),
                d
            )


# ============================================================
# ========================= MAIN ==============================
# ============================================================

def simulate():
    print("\nPROJECT 4 START\n")

    devices = [Device(f"PC{i}") for i in range(60, 90)]

    print("\nPHASE 1: NETWORK TEST\n")
    for _ in range(10):
        a, b = random.sample(devices, 2)
        a.send(generate_data(a, b), b)

    print("\nPHASE 2: TOURNAMENT\n")
    champion = run_tournament(devices)

    print("\nPHASE 3: VICTORY BROADCAST\n")
    broadcast_victory(champion, devices)

    print("\nFINAL STANDINGS")
    for d in sorted(devices, key=lambda x: x.fighter.wins, reverse=True):
        print(d.fighter.summary())


# ============================================================
# ====================== ENTRY POINT ==========================
# ============================================================

if __name__ == "__main__":
    simulate()