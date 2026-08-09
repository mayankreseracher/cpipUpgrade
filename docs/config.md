# cpip config reference

This document describes the cpip config system. It is inspired by rclone and supports named provider profiles.

Config file location: ~/.cpip/config.yaml (preferred) or ~/.cpip/config.json (fallback)

Example profile fields:
- name: profile name
- type: provider type (runpod, modal, aws, gcp, local, baremetal, etc.)
- auth fields: api_key, iam_role, credentials
- region, instance, device
- pricing: fields used by `cpip costs` for estimation
- max_workers, fallback profiles, quotas

See README.md for an extended example.
