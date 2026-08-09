# cpipUpgrade Go Service

Cloud-Powered Package Virtualization for Android Termux - Go Backend Service

## Overview

This is the Go service component of cpipUpgrade, providing:
- HTTP API on port 5081
- Health checks and metrics
- OpenAPI specification
- Flexible logging (zap/zerolog)
- Prometheus metrics integration
- Optional vulnerability scanning via govulncheck

## Requirements

- Go 1.22 or later

## Building

```bash
go build -o server ./cmd/server
```

## Running

```bash
# With default zap logger
./server

# With zerolog
LOGGER=zerolog ./server

# With autocheck enabled
AUTOCHECK=true ./server
```

## Endpoints

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /openapi.yaml` - OpenAPI specification
- `GET /items` - Items list

## Development

### Run tests
```bash
go test -v ./...
```

### Run linter
```bash
golangci-lint run
```

### Check for vulnerabilities
```bash
govulncheck ./...
```

## Docker

```bash
docker build -t cpip-upgrade:latest .
docker run -p 5081:5081 cpip-upgrade:latest
```

## Environment Variables

- `LOGGER` - Logger backend: `zap` (default) or `zerolog`
- `AUTOCHECK` - Enable automatic vulnerability checking: `true` or `false` (default: false)

### System Diagnostics
Check the health of your Termux environment, cache sizes, and cloud connection:
```bash
cpip doctor
cpip runtime
```

---

## 📚 Documentation

For deep dives into the architecture, setup guides, and advanced usage, check out the `docs/` folder:

- [System Architecture](docs/architecture.md)
- [Complete Setup Guide](docs/setup.md)
- [Bare-Metal Deployment](docs/bare-metal-deployment.md)
- [Advanced Usage & Agents](docs/usage.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

# CPIP: Cloud-Powered Package Virtualization

**Hybrid microservice architecture** for accelerated Python workloads on resource-constrained edge devices (Android Termux). Combines **Go HTTP service** for cloud offloading with **Python runtime** components for transparent module proxying and execution orchestration.

---

## Architecture

CPIP decouples training from inference via a two-tier system:

- **Go Service** (`cmd/`, `api/`, `pkg/`): RESTful API gateway (port 5081) managing offload decisions, health checks, metrics aggregation, and vulnerability scanning
- **Python Runtime** (`client/`, `agent/`, `runtime/`): Transparent module proxying, local caching, execution orchestration, and result serialization

**Data Flow:**
1. Python client imports module (e.g., `torch`)
2. Runtime intercepts import, checks local cache and cloud availability
3. Go service routes to GPU cluster or returns cached binary
4. Results stream back to Termux via optimized serialization

---

## High-Impact Use Cases

Below are separated, self-contained use cases demonstrating CPIP's capabilities. Each use case is independent.

<details>
<summary><h3>1. Real-Time Machine Learning on Mobile</h3></summary>

Scenario: Mobile security app requiring sub-50ms threat detection on video frames

```python
import cv2
import torch
from torchvision import models

# Loads ResNet50 from cloud GPU—entire 100MB model never stored locally
model = models.resnet50(pretrained=True).cuda()

# Inference offloaded; only 1-2MB classification results returned
frame = cv2.imread('/sdcard/camera_frame.jpg')
predictions = model(preprocess(frame))
```

CPIP Benefit: Execute complex ML inference without storing large models locally; minimal result payloads.

</details>

<details>
<summary><h3>2. Financial Modeling with Constrained Devices</h3></summary>

Scenario: Risk portfolio analysis requiring massive matrix operations; Termux CPU insufficient

```python
import numpy as np
from scipy.optimize import linprog  # Sparse solver—offloaded
import pandas as pd

portfolio = pd.read_csv('/sdcard/positions.csv')  # 10k instruments
correlation_matrix = portfolio.corr()  # 10k×10k—too large for Termux RAM

# Offload sparse linear programming to cloud CPU cluster
optimal_weights = linprog(objective, constraints=correlation_matrix)
```

CPIP Benefit: Run large numeric workloads on cloud resources while using Termux as the thin client.

</details>

<details>
<summary><h3>3. Edge AI Inference Pipeline</h3></summary>

Scenario: Computer vision on autonomous edge device (robot/drone) with latency constraints

```python
from ultralytics import YOLO

model = YOLO('yolov8s.pt')  # Quantized 30MB model cached locally after first fetch

# Real-time detection loop—inference cached, only new frames processed
results = model.predict(source=0, conf=0.5)  # <30ms per frame
```

CPIP Benefit: Push model updates server-side without redeploying edge binaries; enables fleet A/B testing.

</details>

<details>
<summary><h3>4. Data Science Exploration Without Setup Friction</h3></summary>

Scenario: Researcher running exploratory data analysis on Termux without installing heavy dependencies

```python
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

# All computationally intensive libraries proxied to cloud

data = pd.read_csv('/sdcard/experiment.csv')
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=50)),  # Offloaded
    ('classifier', RandomForestClassifier(n_estimators=500))  # Cloud
])
```

CPIP Benefit: Explore ML without gigabytes of local storage; pay only for compute consumed.

</details>

<details>
<summary><h3>5. Batch Processing with Hybrid Execution</h3></summary>

Scenario: Processing 1M records locally with CPU-intensive operations

```python
# Local filtering and preprocessing (fast on ARM)
data = read_local_data()
filtered = data[data['value'] > threshold]

# Batch the expensive computations, send to cloud
import cpip_batch
results = cpip_batch.map(expensive_ml_transform, filtered, batch_size=1000)
# Streams results back incrementally; local aggregation
aggregated = reduce(lambda x, y: x + y, results)
```

CPIP Benefit: Maximize local compute while offloading bottlenecks; batching reduces network round-trips.

</details>

<details>
<summary><h3>6. Security: Vulnerability Scanning in CI/CD</h3></summary>

Scenario: Termux-based CI runner checking Go dependencies for CVEs

```bash
# Integrated with Go service health checks
# GET /health -> includes govulncheck results
# GET /metrics -> tracks vulnerability trends
cpip security --check-interval 24h --report email
```

CPIP Benefit: Continuous compliance monitoring without external SaaS dependency.

</details>

---

## Technical Stack

Prerequisites

| Component | Version | Purpose |
|---|---:|---|
| Go | 1.22+ | Service backend, HTTP API |
| Python | 3.8+ | Client/runtime libraries |
| Docker | Latest | Containerization & multi-stage builds |

## Building & Running (concise)

Go Service

```bash
go build -o server ./cmd/server
```

Python Runtime (imported as library)

```python
from cpip.client import CloudProxy
proxy = CloudProxy(service_url='http://localhost:5081')
```

Development Mode

```bash
# Terminal 1: Go service with default zap logger
./server

# Terminal 2: Python client (automatic discovery)
python3 -c "import torch; print(torch.__file__)"  # Proxied to cloud
```

Production Mode

```bash
LOGGER=zerolog ./server
AUTOCHECK=true ./server
LOG_LEVEL=debug ./server
```

## API Specification (core endpoints)

- GET /health — Service liveness + system metrics
- GET /metrics — Prometheus format
- GET /openapi.yaml — Schema for code generation
- GET /items — Available offloadable packages
- POST /offload — Execute function on cloud

## Monitoring & Observability

Prometheus metrics exposed at /metrics (examples: cpip_offload_latency_ms, cpip_cache_hits_total, cpip_vulnerabilities_detected)

## Troubleshooting

- High latency: check network/connectivity and increase batch size
- Cache misses: inspect /metrics cache_hit_rate and tune L1 cache size
- Out of memory: adjust offload strategy to move workloads cloud-side

## Project Structure

```
├── cmd/server/          # Go service entry point
├── api/                 # OpenAPI definitions, handlers
├── pkg/
│   ├── builder/         # Module compilation
│   ├── executor/        # Task execution orchestration
│   ├── runtime/         # Execution environment
│   ├── security/        # CVE scanning, auth
│   └── virtualizer/     # Module proxying logic
├── client/              # Python client library
├── agent/               # Execution agents
├── runtime/             # Python runtime hooks
├── tests/               # Unit + integration tests
├── docs/
│   ├── architecture.md  # System design deep-dive
│   ├── setup.md         # Deployment guide
│   ├── tuning.md        # Performance optimization
│   └── security.md      # CVE/auth model
├── go.mod/go.sum        # Go dependencies
├── pyproject.toml       # Python packaging
├── Dockerfile           # Multi-stage build
└── docker-compose.yml   # Local dev environment
```

License

MIT — see LICENSE for full terms.

Contact

For technical questions, issues, or collaboration:
- GitHub Issues: Report bugs with reproducible examples
- Discussions: Architecture decisions, design proposals
