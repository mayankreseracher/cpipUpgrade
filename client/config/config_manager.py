"""
Interactive Configuration Manager for cpip
Inspired by rclone's config command with menu-driven infrastructure selection
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import questionary
from datetime import time


class InfrastructureType(Enum):
    """Supported infrastructure types"""
    BARE_METAL = "bare_metal"
    VIRTUAL_MACHINE = "virtual_machine"
    GPU_CLUSTER = "gpu_cluster"
    HYBRID = "hybrid"


class ProviderType(Enum):
    """Supported cloud providers"""
    AWS = "aws"
    GCP = "google_cloud"
    AZURE = "azure"
    LAMBDA_LABS = "lambda_labs"
    PAPERSPACE = "paperspace"
    LOCAL = "local"


class GPUType(Enum):
    """Supported GPU types"""
    NVIDIA_A100 = "a100"
    NVIDIA_H100 = "h100"
    NVIDIA_V100 = "v100"
    NVIDIA_T4 = "t4"
    NVIDIA_RTX4090 = "rtx4090"
    AMD_MI250X = "mi250x"
    TPU_V4 = "tpu_v4"


@dataclass
class GPUTimerConfig:
    """Configuration for GPU process timing"""
    enabled: bool = False
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None    # HH:MM format
    timezone: str = "UTC"
    allow_override: bool = False  # Allow manual override of timing


@dataclass
class AutoDetectorConfig:
    """Configuration for cost optimization auto-detector"""
    enabled: bool = False
    idle_threshold_minutes: int = 30  # Turn off after 30 mins of inactivity
    cost_threshold_usd: float = 10.0  # Alert if hourly cost exceeds this
    auto_shutdown: bool = False  # Auto shutdown when idle
    power_monitoring: bool = False  # Monitor power consumption
    consolidate_instances: bool = False  # Consolidate workloads to fewer instances


@dataclass
class InfrastructureConfig:
    """Infrastructure configuration for a deployment"""
    name: str
    type: InfrastructureType
    provider: ProviderType
    gpu_types: List[GPUType] = None
    region: str = "us-east-1"
    gpu_timer: GPUTimerConfig = None
    auto_detector: AutoDetectorConfig = None
    compute_budget_monthly: float = 500.0
    enable_caching: bool = True
    max_workers: int = 8
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.gpu_types is None:
            self.gpu_types = []
        if self.gpu_timer is None:
            self.gpu_timer = GPUTimerConfig()
        if self.auto_detector is None:
            self.auto_detector = AutoDetectorConfig()
        if self.metadata is None:
            self.metadata = {}


class ConfigManager:
    """Manages cpip configurations with interactive CLI"""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize config manager"""
        if config_dir is None:
            config_dir = os.path.expanduser("~/.cpip/configs")
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.configs: Dict[str, InfrastructureConfig] = {}
        self.load_all_configs()

    def load_all_configs(self) -> None:
        """Load all saved configurations from disk"""
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    config = self._deserialize_config(config_data)
                    self.configs[config.name] = config
            except Exception as e:
                print(f"Warning: Failed to load {config_file}: {e}")

    def _deserialize_config(self, data: Dict) -> InfrastructureConfig:
        """Deserialize JSON config back to InfrastructureConfig"""
        # Convert enum strings back to enums
        data['type'] = InfrastructureType(data['type'])
        data['provider'] = ProviderType(data['provider'])
        data['gpu_types'] = [GPUType(g) for g in data.get('gpu_types', [])]
        
        # Deserialize nested configs
        if data.get('gpu_timer'):
            data['gpu_timer'] = GPUTimerConfig(**data['gpu_timer'])
        if data.get('auto_detector'):
            data['auto_detector'] = AutoDetectorConfig(**data['auto_detector'])
        
        return InfrastructureConfig(**data)

    def _serialize_config(self, config: InfrastructureConfig) -> Dict:
        """Serialize config to JSON-compatible dict"""
        data = {
            'name': config.name,
            'type': config.type.value,
            'provider': config.provider.value,
            'gpu_types': [g.value for g in config.gpu_types],
            'region': config.region,
            'gpu_timer': asdict(config.gpu_timer),
            'auto_detector': asdict(config.auto_detector),
            'compute_budget_monthly': config.compute_budget_monthly,
            'enable_caching': config.enable_caching,
            'max_workers': config.max_workers,
            'metadata': config.metadata,
        }
        return data

    def save_config(self, config: InfrastructureConfig) -> None:
        """Save configuration to disk"""
        config_file = self.config_dir / f"{config.name}.json"
        with open(config_file, 'w') as f:
            json.dump(self._serialize_config(config), f, indent=2)
        self.configs[config.name] = config
        print(f"✓ Configuration '{config.name}' saved successfully")

    def delete_config(self, name: str) -> None:
        """Delete a configuration"""
        config_file = self.config_dir / f"{name}.json"
        if config_file.exists():
            config_file.unlink()
            if name in self.configs:
                del self.configs[name]
            print(f"✓ Configuration '{name}' deleted")
        else:
            print(f"✗ Configuration '{name}' not found")

    def list_configs(self) -> List[str]:
        """List all saved configurations"""
        return list(self.configs.keys())

    def get_config(self, name: str) -> Optional[InfrastructureConfig]:
        """Get a specific configuration"""
        return self.configs.get(name)

    def interactive_create(self) -> InfrastructureConfig:
        """Create configuration interactively (rclone-style)"""
        
        print("\n" + "="*60)
        print("🔧 cpip Configuration Setup (rclone-style)")
        print("="*60 + "\n")

        # Step 1: Configuration name
        name = questionary.text(
            "Enter a name for this configuration:",
            validate=lambda x: len(x) > 0 and len(x) <= 50
        ).ask()

        if name in self.configs:
            overwrite = questionary.confirm(
                f"Configuration '{name}' already exists. Overwrite?"
            ).ask()
            if not overwrite:
                return None

        # Step 2: Infrastructure type
        print("\n📦 Select Infrastructure Type:")
        infra_type_choice = questionary.select(
            "Infrastructure type:",
            choices=[
                "Bare Metal (Local/On-premises)",
                "Virtual Machine (Cloud VMs)",
                "GPU Cluster (Distributed GPU)",
                "Hybrid (Mix of local + cloud)"
            ]
        ).ask()

        infra_type_map = {
            0: InfrastructureType.BARE_METAL,
            1: InfrastructureType.VIRTUAL_MACHINE,
            2: InfrastructureType.GPU_CLUSTER,
            3: InfrastructureType.HYBRID,
        }
        infra_type = infra_type_map[["Bare Metal (Local/On-premises)", 
                                      "Virtual Machine (Cloud VMs)",
                                      "GPU Cluster (Distributed GPU)",
                                      "Hybrid (Mix of local + cloud)"].index(infra_type_choice)]

        # Step 3: Provider selection (context-aware)
        print("\n☁️ Select Provider:")
        if infra_type == InfrastructureType.BARE_METAL:
            provider = ProviderType.LOCAL
            print("✓ Using local provider for bare metal")
        else:
            provider_choice = questionary.select(
                "Cloud provider:",
                choices=[
                    "AWS (EC2, GPU instances)",
                    "Google Cloud (Compute Engine, TPUs)",
                    "Microsoft Azure (VM, GPU)",
                    "Lambda Labs (GPU cloud)",
                    "Paperspace (Gradient)",
                ]
            ).ask()

            provider_map = {
                "AWS (EC2, GPU instances)": ProviderType.AWS,
                "Google Cloud (Compute Engine, TPUs)": ProviderType.GCP,
                "Microsoft Azure (VM, GPU)": ProviderType.AZURE,
                "Lambda Labs (GPU cloud)": ProviderType.LAMBDA_LABS,
                "Paperspace (Gradient)": ProviderType.PAPERSPACE,
            }
            provider = provider_map[provider_choice]

        # Step 4: GPU selection (only for GPU-capable types)
        gpu_types = []
        if infra_type in [InfrastructureType.GPU_CLUSTER, InfrastructureType.HYBRID, InfrastructureType.VIRTUAL_MACHINE]:
            print("\n🎮 Select GPU Types (multi-select):")
            gpu_choices = questionary.checkbox(
                "GPUs to support:",
                choices=[
                    "NVIDIA A100",
                    "NVIDIA H100",
                    "NVIDIA V100",
                    "NVIDIA T4",
                    "NVIDIA RTX 4090",
                    "AMD MI250X",
                    "TPU v4",
                ]
            ).ask()

            gpu_map = {
                "NVIDIA A100": GPUType.NVIDIA_A100,
                "NVIDIA H100": GPUType.NVIDIA_H100,
                "NVIDIA V100": GPUType.NVIDIA_V100,
                "NVIDIA T4": GPUType.NVIDIA_T4,
                "NVIDIA RTX 4090": GPUType.NVIDIA_RTX4090,
                "AMD MI250X": GPUType.AMD_MI250X,
                "TPU v4": GPUType.TPU_V4,
            }
            gpu_types = [gpu_map[g] for g in gpu_choices]

        # Step 5: Region selection
        print("\n🌍 Select Region:")
        region = questionary.select(
            "Deployment region:",
            choices=[
                "us-east-1 (N. Virginia)",
                "us-west-2 (Oregon)",
                "eu-west-1 (Ireland)",
                "ap-northeast-1 (Tokyo)",
                "ap-south-1 (Mumbai)",
            ]
        ).ask()

        region_map = {
            "us-east-1 (N. Virginia)": "us-east-1",
            "us-west-2 (Oregon)": "us-west-2",
            "eu-west-1 (Ireland)": "eu-west-1",
            "ap-northeast-1 (Tokyo)": "ap-northeast-1",
            "ap-south-1 (Mumbai)": "ap-south-1",
        }
        region = region_map[region]

        # Step 6: GPU Timer configuration
        print("\n⏰ GPU Timer Configuration:")
        enable_timer = questionary.confirm(
            "Enable GPU timer (set start/end times for processes)?"
        ).ask()

        gpu_timer = GPUTimerConfig(enabled=enable_timer)
        if enable_timer:
            gpu_timer.start_time = questionary.text(
                "Start time (HH:MM, e.g., 09:00):",
                validate=lambda x: len(x) == 5 and x[2] == ":"
            ).ask()
            gpu_timer.end_time = questionary.text(
                "End time (HH:MM, e.g., 18:00):",
                validate=lambda x: len(x) == 5 and x[2] == ":"
            ).ask()
            gpu_timer.timezone = questionary.text(
                "Timezone (default: UTC):",
                default="UTC"
            ).ask()
            gpu_timer.allow_override = questionary.confirm(
                "Allow manual override of timer?"
            ).ask()

        # Step 7: Auto-detector configuration
        print("\n🔋 Auto-Detector Configuration (Cost Optimization):")
        enable_detector = questionary.confirm(
            "Enable auto-detector for cost optimization?"
        ).ask()

        auto_detector = AutoDetectorConfig(enabled=enable_detector)
        if enable_detector:
            auto_detector.idle_threshold_minutes = int(questionary.text(
                "Idle threshold (minutes before shutdown) [default: 30]:",
                default="30",
                validate=lambda x: x.isdigit() and int(x) > 0
            ).ask())

            auto_detector.cost_threshold_usd = float(questionary.text(
                "Hourly cost alert threshold (USD) [default: 10.0]:",
                default="10.0",
                validate=lambda x: float(x) > 0
            ).ask())

            auto_detector.auto_shutdown = questionary.confirm(
                "Auto-shutdown when idle?"
            ).ask()

            auto_detector.power_monitoring = questionary.confirm(
                "Enable power consumption monitoring?"
            ).ask()

            auto_detector.consolidate_instances = questionary.confirm(
                "Consolidate workloads to fewer instances for cost savings?"
            ).ask()

        # Step 8: Budget and worker configuration
        print("\n💰 Compute Budget and Resources:")
        compute_budget = float(questionary.text(
            "Monthly compute budget (USD) [default: 500]:",
            default="500",
            validate=lambda x: float(x) > 0
        ).ask())

        max_workers = int(questionary.text(
            "Maximum parallel workers [default: 8]:",
            default="8",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask())

        # Create and save config
        config = InfrastructureConfig(
            name=name,
            type=infra_type,
            provider=provider,
            gpu_types=gpu_types,
            region=region,
            gpu_timer=gpu_timer,
            auto_detector=auto_detector,
            compute_budget_monthly=compute_budget,
            max_workers=max_workers,
        )

        self.save_config(config)
        self.print_config_summary(config)
        return config

    def print_config_summary(self, config: InfrastructureConfig) -> None:
        """Print a formatted summary of configuration"""
        print("\n" + "="*60)
        print("📋 Configuration Summary")
        print("="*60)
        print(f"Name: {config.name}")
        print(f"Infrastructure: {config.type.value.replace('_', ' ').title()}")
        print(f"Provider: {config.provider.value.replace('_', ' ').title()}")
        if config.gpu_types:
            print(f"GPU Types: {', '.join([g.value for g in config.gpu_types])}")
        print(f"Region: {config.region}")
        print(f"Max Workers: {config.max_workers}")
        print(f"Monthly Budget: ${config.compute_budget_monthly}")
        
        if config.gpu_timer.enabled:
            print(f"\n⏰ GPU Timer: {config.gpu_timer.start_time} - {config.gpu_timer.end_time} ({config.gpu_timer.timezone})")
        
        if config.auto_detector.enabled:
            print(f"\n🔋 Auto-Detector Enabled:")
            print(f"  - Idle threshold: {config.auto_detector.idle_threshold_minutes} min")
            print(f"  - Cost alert: ${config.auto_detector.cost_threshold_usd}/hour")
            print(f"  - Auto-shutdown: {'Yes' if config.auto_detector.auto_shutdown else 'No'}")
            print(f"  - Power monitoring: {'Yes' if config.auto_detector.power_monitoring else 'No'}")
        
        print("="*60 + "\n")

    def interactive_modify(self, config_name: str) -> Optional[InfrastructureConfig]:
        """Modify an existing configuration interactively"""
        config = self.get_config(config_name)
        if not config:
            print(f"✗ Configuration '{config_name}' not found")
            return None

        print(f"\n📝 Modifying configuration: {config_name}\n")

        choice = questionary.select(
            "What would you like to modify?",
            choices=[
                "GPU Timer Settings",
                "Auto-Detector Settings",
                "Compute Budget",
                "Max Workers",
                "Region",
                "Cancel",
            ]
        ).ask()

        if choice == "GPU Timer Settings":
            config.gpu_timer.enabled = questionary.confirm(
                "Enable GPU timer?"
            ).ask()
            if config.gpu_timer.enabled:
                config.gpu_timer.start_time = questionary.text(
                    f"Start time [{config.gpu_timer.start_time}]:",
                    default=config.gpu_timer.start_time
                ).ask()
                config.gpu_timer.end_time = questionary.text(
                    f"End time [{config.gpu_timer.end_time}]:",
                    default=config.gpu_timer.end_time
                ).ask()

        elif choice == "Auto-Detector Settings":
            config.auto_detector.enabled = questionary.confirm(
                "Enable auto-detector?"
            ).ask()
            if config.auto_detector.enabled:
                config.auto_detector.idle_threshold_minutes = int(
                    questionary.text(
                        f"Idle threshold (min) [{config.auto_detector.idle_threshold_minutes}]:",
                        default=str(config.auto_detector.idle_threshold_minutes)
                    ).ask()
                )
                config.auto_detector.auto_shutdown = questionary.confirm(
                    "Auto-shutdown when idle?"
                ).ask()

        elif choice == "Compute Budget":
            config.compute_budget_monthly = float(questionary.text(
                f"Monthly budget [{config.compute_budget_monthly}]:",
                default=str(config.compute_budget_monthly)
            ).ask())

        elif choice == "Max Workers":
            config.max_workers = int(questionary.text(
                f"Max workers [{config.max_workers}]:",
                default=str(config.max_workers)
            ).ask())

        elif choice == "Region":
            region = questionary.select(
                "Region:",
                choices=["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
            ).ask()
            config.region = region

        elif choice == "Cancel":
            print("Cancelled.")
            return None

        self.save_config(config)
        return config


if __name__ == "__main__":
    manager = ConfigManager()
    config = manager.interactive_create()
