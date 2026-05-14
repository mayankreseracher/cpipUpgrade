# Bare-Metal Deployment Guide (No Docker)

This guide provides instructions for deploying the CPIP (Cloud Package Virtualization) system on bare-metal hardware, such as a Raspberry Pi or a standard PC, without using Docker. This is ideal for lightweight setups, edge computing, or environments where installing Docker is not feasible.

## 1. Prerequisites

Before you begin, ensure your server (Raspberry Pi or PC) meets the following requirements:
- A Linux-based Operating System (e.g., Ubuntu, Debian, Raspberry Pi OS).
- Python 3.10 or newer.
- `git` for version control.
- `build-essential` for compiling Python packages.
- Redis (optional, but recommended if you plan to run background task queues in the future).

## 2. Server Setup (Raspberry Pi / PC)

The server acts as the central hub for the CPIP network, handling API requests and web socket connections from clients.

### Step 2.1: Install System Dependencies

Update your system packages and install the necessary dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git build-essential redis-server
```

*(Note: Redis will automatically start as a systemd service on Debian/Ubuntu-based systems.)*

### Step 2.2: Clone the Repository & Setup Python Environment

Clone the CPIP repository to your server and set up a virtual environment to avoid polluting your system's Python packages:

```bash
# Clone the repository
git clone https://github.com/yashab-cyber/cpip.git
cd cpip

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Step 2.3: Install CPIP Server

With the virtual environment active, install the CPIP package with the server dependencies:

```bash
pip install -e .[server]
```

### Step 2.4: Configure the Server Environment

Set the necessary environment variables. You can export them directly or create a `.env` file in the root of the project:

```bash
export CPIP_HOST=0.0.0.0
export CPIP_PORT=8000
export CPIP_DEBUG=true
export DATABASE_URL=sqlite+aiosqlite:///./cpip.db
```

### Step 2.5: Start the Server

Start the API server using `uvicorn`. Binding to `0.0.0.0` ensures the server listens on all network interfaces, allowing the client to connect remotely.

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4
```

Your server is now running. Note the IP address of your Raspberry Pi/PC on your local network (you can find this using `ip a` or `hostname -I`).

---

## 3. Builder Setup (Optional)

If you intend to host the CPIP **Builder Farm Worker** on your bare-metal setup (to compile wheels for Android), you can do so natively without Docker.

### Step 3.1: Install Builder Dependencies

On your server, install the builder requirements in the same virtual environment:

```bash
pip install -e .[builder]
```

### Step 3.2: Configure for Native Building

By default, the builder attempts to use Docker. Since you are on bare-metal, instruct the builder to bypass Docker and run native compilation:

```bash
export CPIP_USE_DOCKER=false
```

### Step 3.3: Managing the Android NDK (For C/C++ Extensions)

When `CPIP_USE_DOCKER` is `false`, the builder uses your system's native `pip wheel` capabilities:
- **Pure Python Packages**: These will build flawlessly right out of the box.
- **Packages with C/C++ Extensions**: Termux wheels require compilation against the Android NDK. Since Docker is disabled, you must manually install the Android NDK on your Raspberry Pi/PC if you need to build packages like `numpy` or `cryptography`. 
  - *Workaround*: If you don't want to install the NDK natively, restrict your native bare-metal builder to pure Python packages only.

### Step 3.4: Start the Worker

Start the build queue worker to listen for build jobs:

```bash
python3 -m builder.worker
```

---

## 4. Client Setup (Android / Termux)

The client runs within the Termux environment on an Android device.

### Step 4.1: Install Dependencies

Open Termux and install Python and Git:

```bash
pkg update
pkg install python git
```

### Step 4.2: Clone & Install Client

Clone the CPIP repository and install the client dependencies:

```bash
git clone https://github.com/yashab-cyber/cpip.git
cd cpip
pip install -e .[client]
```

---

## 5. Connecting Server and Client

To establish communication between your client and your newly configured bare-metal server, follow these steps.

### Step 5.1: Network and Firewall Configuration

Ensure your server allows incoming connections on port `8000`. If you are using `ufw` (Uncomplicated Firewall) on your server, you can allow the port with:

```bash
sudo ufw allow 8000/tcp
```

Ensure both the Android device and the server are on the same local network, or that the server is exposed to the internet via port forwarding/VPN.

### Step 5.2: Configure the Client API URL

On your Android device (Termux), point the CPIP client to your server's IP address. Replace `<SERVER_IP>` with the actual IP address of your Raspberry Pi or PC.

```bash
cpip config --api-url http://<SERVER_IP>:8000
```

### Step 5.3: Initialize and Verify Connection

Initialize the client configuration, login (if required), and verify the connection to the backend server:

```bash
# Initialize local configuration
cpip config --init

# Login (if authentication is enforced)
cpip login

# Run diagnostics to test connectivity to the server
cpip doctor
```

If `cpip doctor` reports that the network connectivity to the cloud backend is successful, your bare-metal setup is fully functional!
