# Providers

This folder should contain provider adapter implementations that implement the provider interface.

Provider interface (conceptual):
- Provision(request) -> alloc
- Execute(alloc, harness) -> result
- PriceEstimate(request) -> price
- Release(alloc)

Initial adapters to implement: runpod, modal, aws, gcp, local, baremetal
