## Configuration Management System

`cpip` features an advanced, rclone-inspired interactive configuration system that enables users to define and manage sophisticated infrastructure deployments with granular control over GPUs, cost optimization, and scheduling.

### Overview

The configuration manager (`client/config/config_manager.py`) provides a menu-driven CLI experience similar to rclone's `config` command, allowing users to:

1. **Define Infrastructure Types**: Choose between bare metal, virtual machines, GPU clusters, or hybrid deployments
2. **Select Cloud Providers**: AWS, Google Cloud, Azure, Lambda Labs, or Paperspace
3. **Configure GPU Resources**: Support multiple GPU types (NVIDIA A100, H100, V100, T4, RTX4090, AMD MI250X, TPU v4)
4. **Set GPU Timers**: Schedule when GPU processes can start and stop
5. **Enable Cost Optimization**: Automatic detection and shutdown of unused instances
6. **Manage Budgets**: Set monthly compute budgets with real-time tracking

### Key Features

#### 1. Interactive Configuration Wizard

Start the configuration wizard with:
```bash
cpip config create
```

This launches a guided setup that walks you through:
- **Configuration Name**: Identify your deployment
- **Infrastructure Type**: Bare metal, VMs, GPU clusters, or hybrid
- **Cloud Provider Selection**: Context-aware provider recommendations
- **GPU Selection**: Multi-select GPU types for your workload
- **Regional Deployment**: Choose from 5 major cloud regions
- **GPU Timing**: Set work hours and timezone
- **Cost Optimization**: Enable auto-detector features
- **Resource Limits**: Set budgets and worker concurrency

#### 2. Infrastructure Types

##### Bare Metal
```
- Local/On-premises deployment
- Perfect for Raspberry Pi and edge devices
- Uses local provider (no cloud dependencies)
- Ideal for privacy-critical workloads
```

##### Virtual Machine
```
- Cloud VM instances (EC2, Compute Engine, etc.)
- Flexible scaling and region selection
- Optional GPU support
- Pay-per-hour pricing model
```

##### GPU Cluster
```
- Distributed GPU resources
- Multi-node coordination
- Horizontal scaling
- Ideal for large ML workloads
```

##### Hybrid
```
- Mix of local compute + cloud GPU offloading
- Optimize cost by keeping light tasks local
- Heavy computations on cloud GPUs
- Best of both worlds approach
```

#### 3. GPU Timer Configuration

Schedule when GPU processes can execute:

```yaml
gpu_timer:
  enabled: true
  start_time: "09:00"      # Start using GPUs at 9 AM
  end_time: "18:00"        # Stop at 6 PM
  timezone: "America/New_York"
  allow_override: true     # Allow manual override when needed
```

**Use Cases:**
- Run expensive computations during off-peak hours for cost savings
- Enforce company policy on GPU usage windows
- Coordinate with shared resource pools
- Prevent excessive power consumption during specific times

**Example: Scheduling GPU Jobs**
```python
from client.config.gpu_timer import GPUTimerManager

timer = GPUTimerManager()

# Check if current time is within GPU window
if timer.is_gpu_active():
    # Safe to use GPU
    result = torch.cuda.tensor([1, 2, 3])
else:
    # Fallback to CPU or defer job
    result = compute_on_cpu()
```

#### 4. Auto-Detector Configuration (Cost Optimization)

Intelligent resource management to minimize compute costs:

```yaml
auto_detector:
  enabled: true
  idle_threshold_minutes: 30          # Shutdown after 30 min inactivity
  cost_threshold_usd: 10.0            # Alert if hourly rate exceeds $10
  auto_shutdown: true                 # Auto-terminate unused instances
  power_monitoring: true              # Track real-time power usage
  consolidate_instances: true         # Merge workloads to fewer instances
```

**Features:**

| Feature | Benefit | Example |
|---------|---------|---------|
| **Idle Detection** | Automatically shuts down GPUs after inactivity | 30-min GPU unused → Auto-stop |
| **Cost Alerts** | Notifies when spending exceeds threshold | Hourly rate > $10 → Alert |
| **Auto-Shutdown** | Prevents unexpected bills from forgotten instances | Stalled job → Auto-terminate |
| **Power Monitoring** | Real-time power consumption tracking | Monitor Watts used per instance |
| **Consolidation** | Merge multiple small jobs into single instance | 5 mini jobs → 1 consolidated job |

**Cost Savings Example:**
```
Scenario: ML Training Pipeline
- Without auto-detector: 24/7 running GPU = $720/month (AWS p3.2xlarge)
- With auto-detector: 8 hours/day active + 30min idle timeout = $240/month
- Savings: 67% cost reduction
```

**Auto-Detector Logic Flow:**
```
1. Monitor job execution
   ↓
2. Job completes or stalls
   ↓
3. Start idle timer (30 min default)
   ↓
4. No new jobs submitted?
   ↓
5. Check hourly cost vs threshold
   ↓
6. Cost acceptable + Idle timeout reached?
   ↓
7. Auto-shutdown instance
```

#### 5. Configuration Management Commands

**List all configurations:**
```bash
cpip config list
```

**Show specific configuration:**
```bash
cpip config show my-deployment
```

**Modify configuration:**
```bash
cpip config edit my-deployment
```

**Delete configuration:**
```bash
cpip config delete my-deployment
```

**Validate configuration:**
```bash
cpip config validate my-deployment
```

**Set active configuration:**
```bash
cpip config use my-deployment
```

### Configuration File Structure

Configurations are stored in `~/.cpip/configs/` as JSON files for portability:

```json
{
  "name": "my-gpu-cluster",
  "type": "gpu_cluster",
  "provider": "aws",
  "gpu_types": ["a100", "h100"],
  "region": "us-east-1",
  "gpu_timer": {
    "enabled": true,
    "start_time": "09:00",
    "end_time": "18:00",
    "timezone": "UTC",
    "allow_override": false
  },
  "auto_detector": {
    "enabled": true,
    "idle_threshold_minutes": 30,
    "cost_threshold_usd": 10.0,
    "auto_shutdown": true,
    "power_monitoring": true,
    "consolidate_instances": true
  },
  "compute_budget_monthly": 500.0,
  "enable_caching": true,
  "max_workers": 8,
  "metadata": {
    "team": "ml-ops",
    "project": "nlp-training"
  }
}
```

### Advanced Usage

#### Multi-Configuration Management

Manage different configurations for different projects:

```python
from client.config.config_manager import ConfigManager

manager = ConfigManager()

# Get all configurations
configs = manager.list_configs()

# Switch between configs
prod_config = manager.get_config("prod-cluster")
dev_config = manager.get_config("dev-gpu")

# Validate before deployment
if manager.validate(prod_config):
    deploy(prod_config)
```

#### Programmatic Configuration

Create configurations without interactive wizard:

```python
from client.config.config_manager import ConfigManager, InfrastructureConfig
from client.config.config_manager import InfrastructureType, ProviderType, GPUType
from client.config.config_manager import GPUTimerConfig, AutoDetectorConfig

manager = ConfigManager()

config = InfrastructureConfig(
    name="ml-pipeline",
    type=InfrastructureType.GPU_CLUSTER,
    provider=ProviderType.AWS,
    gpu_types=[GPUType.NVIDIA_A100, GPUType.NVIDIA_H100],
    region="us-west-2",
    gpu_timer=GPUTimerConfig(
        enabled=True,
        start_time="08:00",
        end_time="20:00",
        timezone="America/Los_Angeles"
    ),
    auto_detector=AutoDetectorConfig(
        enabled=True,
        idle_threshold_minutes=15,
        cost_threshold_usd=15.0,
        auto_shutdown=True,
        power_monitoring=True
    ),
    compute_budget_monthly=1000.0,
    max_workers=16
)

manager.save_config(config)
```

#### Integration with Deployment

Use configurations in your deployment scripts:

```bash
#!/bin/bash

# Use specific configuration for deployment
export CPIP_CONFIG="prod-cluster"

# Launch with configuration
cpip daemon start --config prod-cluster

# Install packages with timing constraints
cpip install --config prod-cluster torch tensorflow

# Run workload
cpip shell --config prod-cluster < my_script.py
```

### Best Practices

#### 1. Environment Separation
```bash
# Development: Lower costs, flexible timing
cpip config create dev-gpu
# - Type: Virtual Machine
# - Max workers: 4
# - Budget: $100/month
# - No timer restrictions

# Production: Strict scheduling, cost controls
cpip config create prod-gpu
# - Type: GPU Cluster
# - Max workers: 16
# - Budget: $500/month
# - Timer: 09:00-18:00 UTC
```

#### 2. Cost Optimization Strategy
```yaml
# Conservative approach (max savings)
auto_detector:
  idle_threshold_minutes: 10      # Aggressive shutdown
  cost_threshold_usd: 5.0         # Low threshold
  auto_shutdown: true
  consolidate_instances: true

# Balanced approach (recommended)
auto_detector:
  idle_threshold_minutes: 30      # Standard timeout
  cost_threshold_usd: 10.0        # Reasonable threshold
  auto_shutdown: true
  consolidate_instances: true

# Performance-focused (higher costs)
auto_detector:
  idle_threshold_minutes: 60      # Generous timeout
  cost_threshold_usd: 50.0        # High threshold
  auto_shutdown: false            # Keep warm
  consolidate_instances: false    # Dedicated resources
```

#### 3. GPU Timer Alignment
```yaml
# Align with business hours
start_time: "09:00"
end_time: "18:00"
timezone: "America/New_York"

# Align with off-peak pricing (AWS, GCP)
start_time: "22:00"  # Night batch processing
end_time: "08:00"
timezone: "UTC"

# Global team support (24/7)
enabled: false  # No time restrictions
```

#### 4. Budget Monitoring
```bash
# Monitor current spending
cpip status --config prod-cluster

# Project monthly cost
cpip cost-estimate --config prod-cluster --days 30

# Alert when approaching budget
cpip config set prod-cluster cost_threshold_usd=100.0
```

### Troubleshooting

#### Configuration Not Loading
```bash
# Validate configuration syntax
cpip config validate my-config

# Check configuration file location
ls -la ~/.cpip/configs/

# View configuration details
cpip config show my-config --verbose
```

#### GPU Timer Not Working
```bash
# Check if timer is enabled
cpip config show my-config | grep "gpu_timer"

# Verify timezone
timedatectl  # Check system timezone

# Check current time window
cpip timer status
```

#### Cost Issues
```bash
# Review auto-detector settings
cpip config show my-config | grep "auto_detector"

# Check current spending
cpip spending report

# View instance consolidation status
cpip instances list --config my-config
```

### Migration from rclone

If you're familiar with rclone's config system, here's the mapping:

| rclone Concept | cpip Equivalent |
|---|---|
| Remote storage | Infrastructure Type |
| Provider (S3, GCS, etc) | Cloud Provider |
| Configuration name | Config name |
| Options (key, secret) | GPU Timer, Auto-Detector settings |
| Multiple remotes | Multiple configurations |

### Related Documentation

- [System Architecture](./architecture.md) - Understanding the underlying architecture
- [Bare-Metal Deployment](./bare-metal-deployment.md) - Deploy without cloud
- [Setup Guide](./setup.md) - Initial setup and installation
- [Advanced Usage](./usage.md) - Agent integration and advanced features
