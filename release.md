# Release v0.1.1

This release addresses critical security vulnerabilities, prevents API route shadowing, fixes multiple resource leaks, and updates contact/sponsorship information.

## What's Changed
* **RCE Security Mitigation**: Restrained remote code execution in FastAPI by validating method paths against a strict allowlist.
* **WebSocket Authentication**: Enabled token validation for WebSocket connections to prevent unauthenticated connections.
* **FastAPI Route Reordering**: Resolved route shadowing where `/catalog` was improperly shadowed by `/{name}`.
* **aarch64 & SQLite Support**: Added the missing `aiosqlite` dependency to ensure SQLite async engines initialize properly.
* **Path Traversal Protection**: Implemented target directory verification on all tar file extractions in virtualized layers.
* **CLI Improvements**: Fixed memory/file descriptor leaks in daemon start logic and improved partial failure reporting for CLI installations.
* **Socials & Sponsorship**: Added official Instagram, X, LinkedIn, Threads profiles, and donation contact emails in the README.
