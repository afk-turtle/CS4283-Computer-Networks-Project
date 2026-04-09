OSI NETWORK SIMULATION PROJECT

Overview:
This project simulates a full 7-layer OSI (Open Systems Interconnection) model along with a network of interconnected devices such as PCs, routers, switches, and hubs. It demonstrates how data is created, encapsulated, transmitted, and forwarded across a network from a sender to a receiver.

Features:

* Full implementation of all 7 OSI layers
* Randomly generated network with 60+ devices
* Simulation of routers, switches, and hubs
* Data encapsulation from HTTP request to raw bits
* Randomized packet transmission between devices
* Unique session IDs using UUID
* Detailed console logs showing each step

How It Works:
The simulation follows the OSI model step-by-step. Data starts at the Application Layer where an HTTP request is created. It is then encoded in the Presentation Layer, assigned a session ID in the Session Layer, packaged into a TCP segment in the Transport Layer, wrapped into an IP packet in the Network Layer, framed with MAC addresses in the Data Link Layer, and finally converted into bits in the Physical Layer.

Once encapsulated, the data is transmitted through a randomly generated network. Devices forward the packet based on their type:

* Routers route using IP logic
* Switches forward using MAC-based behavior
* Hubs broadcast to all connected devices

The process continues until the packet reaches the destination device or is dropped.

How to Run:

1. Make sure Python is installed on your system.
2. Download or clone the project files.
3. Open the project folder in your code editor or terminal.
4. Run the program using the command:
   python main.py
   (Replace "main.py" with the actual filename if different.)

Example Output:
The program prints step-by-step logs showing:

* OSI layer processing
* Encapsulation details
* Device-to-device forwarding
* Final delivery confirmation when the destination is reached

Project Structure:

* main.py : Contains all classes and simulation logic
* README.txt : Project documentation

Learning Objectives:

* Understand how the OSI model works in practice
* Visualize data encapsulation across layers
* Learn the roles of different network devices
* Observe how packets move through a network

Future Improvements:

* Implement real routing tables instead of random forwarding
* Add MAC address learning for switches
* Simulate packet loss and congestion
* Create a visual representation of the network topology
