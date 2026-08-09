# cpip costs

The cpip costs subsystem provides simple cost estimation and post-run accounting.

- Costs are estimated from profile pricing fields in the config file.
- Post-run reports are stored in ~/.cpip/costs/ and can be inspected with `cpip costs report --run-id <id>`.

Pricing fields supported (suggested):
- pricing.gpu_price_per_hour
- pricing.vram_gb_price_per_hour
- pricing.vcpu_price_per_hour
- pricing.storage_gb_price_per_hour

