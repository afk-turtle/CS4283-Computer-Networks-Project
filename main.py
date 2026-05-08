import random
import uuid
import time



# OSI LAYERS 
class Layer:
    def __init__(self, next_layer=None):
        self.next_layer = next_layer

    def process(self, data):
        raise NotImplementedError


class ApplicationLayer(Layer):
    def process(self, data):
        v = data.get("verbose", True)
        if data.get("msg_type") == "COMBAT":
            data["app_data"] = (
                f"COMBAT/{data['combat_type']} | "
                f"From: {data['host']} | "
                f"Payload: {data['combat_payload']}"
            )
            if v: print(f"Application Layer: Combat Message Created [{data['combat_type']}]")
        else:
            data["app_data"] = f"GET {data['path']} HTTP/1.1 | Host: {data['host']}"
            if v: print("Application Layer: HTTP Request Created")
        if self.next_layer:
            self.next_layer.process(data)


class PresentationLayer(Layer):
    def process(self, data):
        data["encoded"] = data["app_data"].encode("utf-8")
        if data.get("verbose", True): print("Presentation Layer: Data Encoded")
        if self.next_layer:
            self.next_layer.process(data)


class SessionLayer(Layer):
    def process(self, data):
        data["session_id"] = str(uuid.uuid4())
        if data.get("verbose", True): print(f"Session Layer: Session ID = {data['session_id']}")
        if self.next_layer:
            self.next_layer.process(data)


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



# COMBAT SYSTEM

MOVES = ["ATTACK_RED", "ATTACK_BLUE", "ATTACK_GREEN", "BOLSTER_DEFENSE", "BOLSTER_ATTACK"]

class Fighter:
    """Represents a combatant living on an end-node Device."""

    def __init__(self, owner_name):
        self.owner      = owner_name
        self.red_hp     = 20
        self.blue_hp    = 20
        self.green_hp   = 20
        self.attack     = 6
        self.defense    = 0
        self.alive      = True
        self.wins       = 0

    # state
    def is_dead(self):
        return self.red_hp <= 0 or self.blue_hp <= 0 or self.green_hp <= 0

    def serialize(self):
        return (
            f"R:{self.red_hp},B:{self.blue_hp},G:{self.green_hp},"
            f"ATK:{self.attack},DEF:{self.defense}"
        )

    def summary(self):
        status = "ALIVE" if self.alive else "DEAD"
        return (
            f"{self.owner} [{status}] | "
            f"HP R:{self.red_hp}/B:{self.blue_hp}/G:{self.green_hp} | "
            f"ATK:{self.attack} DEF:{self.defense} | Wins:{self.wins}"
        )

    # AI move
    def choose_move(self, opponent_state: dict) -> str:
        """
        Simple AI heuristic:
        - If defense is 0 and own lowest HP channel is being targeted → bolster defense
        - If attack is low and all HP channels are healthy → bolster attack
        - Otherwise, attack the opponent's lowest HP channel
        """
        opp_r = opponent_state.get("red_hp", 20)
        opp_b = opponent_state.get("blue_hp", 20)
        opp_g = opponent_state.get("green_hp", 20)

        own_min = min(self.red_hp, self.blue_hp, self.green_hp)

        # Defensive priority: low own HP and undefended
        if own_min <= 6 and self.defense == 0 and random.random() < 0.6:
            return "BOLSTER_DEFENSE"

        # Offensive investment: build up attack if all channels healthy
        if self.attack < 8 and own_min > 12 and random.random() < 0.3:
            return "BOLSTER_ATTACK"

        # Target weakest opponent channel
        channel_map = {
            "ATTACK_RED":   opp_r,
            "ATTACK_BLUE":  opp_b,
            "ATTACK_GREEN": opp_g,
        }
        return min(channel_map, key=channel_map.get)

    # take damage
    def receive_attack(self, channel: str, raw_damage: int) -> int:
        """
        Defending player calculates and applies damage (per Project 1 rules).
        Returns actual damage dealt.
        """
        actual = max(0, raw_damage - self.defense)
        if channel == "RED":
            self.red_hp -= actual
        elif channel == "BLUE":
            self.blue_hp -= actual
        elif channel == "GREEN":
            self.green_hp -= actual
        return actual

    # apply move
    def apply_own_move(self, move: str):
        if move == "BOLSTER_DEFENSE":
            self.defense = min(1, self.defense + 1)
        elif move == "BOLSTER_ATTACK":
            self.attack += 1



# NETWORK PACKET SIGNALS
class PacketDelivered(Exception):
    pass



# HELPERS

def random_mac():
    return ':'.join(f'{random.randint(0, 255):02X}' for _ in range(6))


def generate_data(sender, receiver, msg_type="HTTP",
                  combat_type=None, combat_payload=None, verbose=True):
    """Build the OSI data dict. Supports HTTP and COMBAT message types."""
    base = {
        "host": receiver.name,
        "path": "/",
        "src_ip":  f"192.168.{random.randint(0,9)}.{random.randint(2, 254)}",
        "dst_ip":  f"10.0.{random.randint(0,9)}.{random.randint(2, 254)}",
        "src_port": random.randint(40000, 60000),
        "dst_port": 80,
        "src_mac": sender.mac,
        "dst_mac": receiver.mac,
        "msg_type": msg_type,
        "verbose": verbose,
    }
    if msg_type == "COMBAT":
        base["combat_type"]    = combat_type
        base["combat_payload"] = combat_payload
    return base



# DEVICES

class Device:
    def __init__(self, name):
        self.name        = name
        self.mac         = random_mac()
        self.stack       = build_stack()
        self.connections = []
        self.home_router = None
        self.fighter     = Fighter(name)

    def connect(self, other):
        if other not in self.connections:
            self.connections.append(other)
            other.connections.append(self)

    def send(self, data, destination, verbose=True):
        if verbose:
            print(f"\n\n{'='*60}")
            print(f"  {self.name} → {destination.name}  [{data.get('msg_type','?')}/"
                  f"{data.get('combat_type','')}]")
            print(f"{'='*60}")
            print("Starting Encapsulation...\n")
            self.stack.process(data)
            print("\n--- Transmission Starting ---")
        else:
            self.stack.process(data)
        try:
            self.forward(data, destination, visited=set(), verbose=verbose)
        except PacketDelivered:
            pass

    def forward(self, data, destination, visited, verbose=True):
        if self in visited:
            return
        visited.add(self)

        if verbose:
            print(f"[{self.name}] RECEIVED FRAME  |  "
                  f"IP: {data['packet']['src_ip']} → {data['packet']['dst_ip']}")

        if self == destination:
            if verbose:
                print(f"   {self.name} ACCEPTED PACKET (DESTINATION REACHED)\n")
            raise PacketDelivered

        if not self.connections:
            if verbose:
                print("  No connections. Packet dropped.")
            return

        self.handle_forwarding(data, destination, visited, verbose)

    def handle_forwarding(self, data, destination, visited, verbose=True):
        for conn in self.connections:
            if isinstance(conn, (Switch, Hub)) and conn not in visited:
                if verbose:
                    print(f"  {self.name} forwarding to {conn.name}")
                conn.forward(data, destination, visited, verbose)
                return
        next_hop = random.choice(self.connections)
        if verbose:
            print(f"  {self.name} forwarding to {next_hop.name}")
        next_hop.forward(data, destination, visited, verbose)


class Router(Device):
    def __init__(self, name):
        super().__init__(name)
        self.fighter = None  # Routers don't fight

    def handle_forwarding(self, data, destination, visited, verbose=True):
        if verbose:
            print(f"  {self.name} (ROUTER): Routing using IP")

        for conn in self.connections:
            if isinstance(conn, (Switch, Hub)) and conn not in visited:
                for device in conn.connections:
                    if device == destination:
                        if verbose:
                            print(f"  {self.name} → {conn.name} (destination on this segment)")
                        conn.forward(data, destination, visited, verbose)
                        return

        dst_router = destination.home_router
        if dst_router and dst_router not in visited:
            if dst_router in self.connections:
                if verbose:
                    print(f"  {self.name} → {dst_router.name} (direct route)")
                dst_router.forward(data, destination, visited, verbose)
                return
            for conn in self.connections:
                if isinstance(conn, Router) and conn not in visited:
                    if dst_router in conn.connections:
                        if verbose:
                            print(f"  {self.name} → {conn.name} (via neighbor)")
                        conn.forward(data, destination, visited, verbose)
                        return

        router_neighbors = [c for c in self.connections if isinstance(c, Router) and c not in visited]
        if router_neighbors:
            next_hop = random.choice(router_neighbors)
            if verbose:
                print(f"  {self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited, verbose)
            return

        unvisited = [c for c in self.connections if c not in visited]
        if unvisited:
            next_hop = random.choice(unvisited)
            if verbose:
                print(f"  {self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited, verbose)


class Switch(Device):
    def __init__(self, name):
        super().__init__(name)
        self.fighter = None  # Switches don't fight

    def handle_forwarding(self, data, destination, visited, verbose=True):
        if verbose:
            print(f"  {self.name} (SWITCH): Forwarding using MAC table")

        if destination in self.connections and destination not in visited:
            if verbose:
                print(f"  {self.name} → {destination.name} (MAC match)")
            destination.forward(data, destination, visited, verbose)
            return

        for conn in self.connections:
            if isinstance(conn, Router) and conn not in visited:
                if verbose:
                    print(f"  {self.name} → {conn.name}")
                conn.forward(data, destination, visited, verbose)
                return

        unvisited = [c for c in self.connections if c not in visited]
        if unvisited:
            next_hop = random.choice(unvisited)
            if verbose:
                print(f"  {self.name} → {next_hop.name}")
            next_hop.forward(data, destination, visited, verbose)


class Hub(Device):
    def __init__(self, name):
        super().__init__(name)
        self.fighter = None  # Hubs don't fight

    def handle_forwarding(self, data, destination, visited, verbose=True):
        if verbose:
            print(f"  {self.name} (HUB): Broadcasting to all ports")

        if destination in self.connections and destination not in visited:
            if verbose:
                print(f"  {self.name} → {destination.name} (destination on this segment)")
            destination.forward(data, destination, visited, verbose)
            return

        for device in self.connections:
            if device not in visited:
                if verbose:
                    print(f"  {self.name} → {device.name}")
                device.forward(data, destination, visited, verbose)



# NETWORK BUILDER

def build_network():
    num_routers = random.randint(6, 10)
    routers = [Router(f"Router{i}") for i in range(num_routers)]

    router_peripheral_counts = [random.randint(2, 5) for _ in range(num_routers)]
    total_peripherals = sum(router_peripheral_counts)

    num_switches = random.randint(total_peripherals // 3, (2 * total_peripherals) // 3)
    num_hubs     = total_peripherals - num_switches

    switches = [Switch(f"Switch{i}") for i in range(num_switches)]
    hubs     = [Hub(f"Hub{i}")     for i in range(num_hubs)]
    peripherals_pool = switches + hubs
    random.shuffle(peripherals_pool)

    total_devices = total_peripherals * 3
    devices = [Device(f"PC{i}") for i in range(59, 59 + total_devices)]

    pi = 0
    di = 0

    for i, router in enumerate(routers):
        router.connect(routers[(i + 1) % num_routers])
        count = router_peripheral_counts[i]
        for _ in range(count):
            peripheral = peripherals_pool[pi]
            pi += 1
            router.connect(peripheral)
            for _ in range(3):
                devices[di].home_router = router
                peripheral.connect(devices[di])
                di += 1

    for i in range(num_routers // 2):
        routers[i].connect(routers[i + num_routers // 2])

    print("\n")
    print("=" * 60)
    print("              NETWORK TOPOLOGY GENERATED")
    print("=" * 60)
    print(f"  Routers  : {num_routers}")
    print(f"  Switches : {num_switches}")
    print(f"  Hubs     : {num_hubs}")
    print(f"  End Nodes: {total_devices}")
    print(f"  Total    : {num_routers + num_switches + num_hubs + total_devices}")
    print("=" * 60)

    return devices, routers



# COMBAT PROTOCOL
def do_combat(attacker: Device, defender: Device):
    """
    Full 1v1 combat loop between two end-node fighters, using the network to
    transmit every move and result as a COMBAT packet through the OSI stack.

    Protocol messages (combat_type field):
        CHALLENGE  - Attacker initiates, payload = attacker fighter state
        ACCEPT     - Defender accepts, payload = defender fighter state
        MOVE       - Current turn player declares intent, payload = move string
        RESULT     - Defending player reports damage result, payload = state
        CONCEDE    - Loser surrenders, payload = final state
        AGREE      - Winner confirms concession, payload = final state
    """

    af = attacker.fighter  # attacker's Fighter object
    df = defender.fighter  # defender's Fighter object

    if not af.alive or not df.alive:
        return  # One of them already eliminated

    separator = f"\n{'─'*60}\n"

    print(separator)
    print(f"  ⚔  COMBAT INITIATED: {attacker.name} vs {defender.name}")
    print(separator)

    # HANDSHAKE, Attacker sends CHALLENGE
    attacker.send(
        generate_data(attacker, defender, "COMBAT", "CHALLENGE", af.serialize(), verbose=True),
        defender, verbose=True
    )
    print(f"  [{attacker.name}] CHALLENGE sent: {af.serialize()}")

    # Defender sends ACCEPT
    defender.send(
        generate_data(defender, attacker, "COMBAT", "ACCEPT", df.serialize(), verbose=True),
        attacker, verbose=True
    )
    print(f"  [{defender.name}] ACCEPT sent: {df.serialize()}")

    # Coin flip for first turn
    turn = random.choice([attacker, defender])
    other = defender if turn == attacker else attacker
    print(f"\n  Coin flip → {turn.name} goes first!\n")

    # COMBAT LOOP 
    round_num = 0
    while True:
        round_num += 1
        turn_fighter  = turn.fighter
        other_fighter = other.fighter

        print(f"\n  --- Round {round_num}: {turn.name}'s turn ---")
        print(f"    {turn_fighter.summary()}")
        print(f"    {other_fighter.summary()}")

        # Build opponent state dict for AI
        opp_state = {
            "red_hp":   other_fighter.red_hp,
            "blue_hp":  other_fighter.blue_hp,
            "green_hp": other_fighter.green_hp,
        }

        # AI chooses move
        move = turn_fighter.choose_move(opp_state)
        print(f"\n  [{turn.name}] AI Decision → {move}")

        # Transmit MOVE packet through the network
        turn.send(
            generate_data(turn, other, "COMBAT", "MOVE", move, verbose=True),
            other, verbose=True
        )

        # MOVE RESOLUTION
        if move == "BOLSTER_DEFENSE":
            turn_fighter.apply_own_move(move)
            result_payload = f"BOLSTER_DEFENSE | {turn_fighter.serialize()}"
            print(f"  [{turn.name}] Bolstered defense → DEF={turn_fighter.defense}")

        elif move == "BOLSTER_ATTACK":
            turn_fighter.apply_own_move(move)
            result_payload = f"BOLSTER_ATTACK | {turn_fighter.serialize()}"
            print(f"  [{turn.name}] Bolstered attack → ATK={turn_fighter.attack}")

        else:
            # Attack, defender calculates damage
            channel = move.split("_")[1]  # RED, BLUE, or GREEN
            raw_damage = random.randint(1, turn_fighter.attack)
            actual_damage = other_fighter.receive_attack(channel, raw_damage)
            result_payload = (
                f"ATTACK_{channel} raw={raw_damage} actual={actual_damage} | "
                f"{other_fighter.serialize()}"
            )
            print(f"  [{other.name}] Received ATTACK_{channel}: "
                  f"raw={raw_damage}, DEF={other_fighter.defense}, "
                  f"actual={actual_damage}")

        # Transmit RESULT back through the network
        other.send(
            generate_data(other, turn, "COMBAT", "RESULT", result_payload, verbose=True),
            turn, verbose=True
        )
        print(f"  [{other.name}] RESULT sent: {result_payload}")

        # CHECK FOR DEFEAT 
        if other_fighter.is_dead():
            print(f"\n   {other.name}'s fighter has been defeated!")

            # Loser sends CONCEDE
            other.send(
                generate_data(other, turn, "COMBAT", "CONCEDE", other_fighter.serialize(), verbose=True),
                turn, verbose=True
            )
            print(f"  [{other.name}] CONCEDE sent: {other_fighter.serialize()}")

            # Winner sends AGREE
            turn.send(
                generate_data(turn, other, "COMBAT", "AGREE", turn_fighter.serialize(), verbose=True),
                other, verbose=True
            )
            print(f"  [{turn.name}] AGREE (concession accepted): {turn_fighter.serialize()}")

            # Update status
            other_fighter.alive = False
            turn_fighter.wins += 1

            print(f"\n  🏆 {turn.name} WINS this bout!")
            print(f"     Final — {turn_fighter.summary()}")
            print(f"     Final — {other_fighter.summary()}")
            return

        # SWAP TURNS 
        turn, other = other, turn



# TOURNAMENT (every node fights until one champion remains)

def run_tournament(devices: list):
    """
    Single-elimination style: randomly pair alive fighters.
    Repeat until one fighter is left standing.
    """
    print("\n\n")
    print("#" * 60)
    print("                     TOURNAMENT BEGIN  ")
    print("#" * 60)
    print(f"  {len(devices)} fighters enter. One leaves.\n")

    alive = list(devices)
    round_num = 0

    while len(alive) > 1:
        round_num += 1
        print(f"\n\n{'#'*60}")
        print(f"  TOURNAMENT ROUND {round_num}  |  {len(alive)} fighters remaining")
        print(f"{'#'*60}")

        random.shuffle(alive)
        next_alive = []
        i = 0

        while i < len(alive):
            if i + 1 < len(alive):
                a, b = alive[i], alive[i + 1]
                do_combat(a, b)
                # Winner advances
                if a.fighter.alive:
                    next_alive.append(a)
                else:
                    next_alive.append(b)
                i += 2
            else:
                # Odd one out, gets a bye
                print(f"\n  {alive[i].name} receives a bye this round.")
                next_alive.append(alive[i])
                i += 1

        alive = [d for d in next_alive if d.fighter.alive]

    return alive[0] if alive else None


# VICTORY BROADCAST
def broadcast_victory(champion: Device, all_devices: list, all_routers: list):
    """
    Champion sends a COMBAT/VICTORY message to every other end-node,
    routed through the full OSI stack and network infrastructure.
    """
    print("\n\n")
    print("-" * 60)
    print(f"    CHAMPION: {champion.name}")
    print(f"  {champion.fighter.summary()}")
    print("-" * 60)
    print("\n  Champion broadcasting victory to all nodes...\n")

    payload = f"I AM THE LAST FIGHTER STANDING | {champion.fighter.serialize()}"

    for device in all_devices:
        if device == champion:
            continue
        print(f"\n  → Sending VICTORY broadcast to {device.name}")
        champion.send(
            generate_data(champion, device, "COMBAT", "VICTORY", payload, verbose=True),
            device,
            verbose=True
        )

    print("\n   All nodes notified. Tournament complete.")



# MAIN SIMULATION
def simulate():
    print("\n" + "=" * 60)
    print("      PROJECT 4 — NETWORKED COMBAT SIMULATION")
    print("      (OSI Stack + AI Fighter Tournament)")
    print("=" * 60)

    # Build network
    devices, routers = build_network()

    # Print initial fighter roster
    print("\n  FIGHTER ROSTER")
    print("  " + "─" * 40)
    for d in devices:
        print(f"  {d.fighter.summary()}")

    # Run 10 normal OSI messages first 
    print("\n\n" + "=" * 60)
    print("  PHASE 1: OSI MESSAGE SIMULATION (10 messages)")
    print("=" * 60)
    for i in range(10):
        sender   = random.choice(devices)
        receiver = random.choice(devices)
        while sender == receiver:
            receiver = random.choice(devices)
        data = generate_data(sender, receiver)
        sender.send(data, receiver)

    # Run the combat tournament
    print("\n\n" + "=" * 60)
    print("  PHASE 2: COMBAT TOURNAMENT")
    print("=" * 60)
    champion = run_tournament(devices)

    if champion:
        # Champion broadcasts victory through the network
        broadcast_victory(champion, devices, routers)

        # Final scoreboard
        print("\n\n  FINAL STANDINGS")
        print("  " + "─" * 40)
        sorted_devices = sorted(devices, key=lambda d: d.fighter.wins, reverse=True)
        for d in sorted_devices:
            print(f"  {d.fighter.summary()}")
    else:
        print("\n  No champion determined (all fighters eliminated simultaneously).")


# ENTRY POINT

if __name__ == "__main__":
    simulate()