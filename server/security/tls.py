"""
TLS and mutual TLS (mTLS) configuration.

Handles certificate loading, HTTPS setup, and client certificate validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import ssl

logger = logging.getLogger(__name__)


class TLSConfig:
    """TLS/mTLS configuration for secure communication."""

    def __init__(
        self,
        enabled: bool = False,
        cert_file: str | Path | None = None,
        key_file: str | Path | None = None,
        ca_file: str | Path | None = None,
        mtls_enabled: bool = False,
        verify_mode: str = "CERT_NONE",
        minimum_version: str = "TLSv1_2",
    ):
        """
        Initialize TLS configuration.

        Args:
            enabled: Enable TLS/HTTPS
            cert_file: Path to server certificate
            key_file: Path to server private key
            ca_file: Path to CA certificate (for mTLS client verification)
            mtls_enabled: Enable mutual TLS (client certificate validation)
            verify_mode: SSL verification mode (CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED)
            minimum_version: Minimum TLS version (TLSv1_2, TLSv1_3)
        """
        self.enabled = enabled
        self.cert_file = Path(cert_file) if cert_file else None
        self.key_file = Path(key_file) if key_file else None
        self.ca_file = Path(ca_file) if ca_file else None
        self.mtls_enabled = mtls_enabled
        self.verify_mode = verify_mode
        self.minimum_version = minimum_version

    def validate(self) -> bool:
        """
        Validate TLS configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.enabled:
            logger.debug("TLS is disabled")
            return True

        if not self.cert_file or not self.key_file:
            logger.error("TLS enabled but cert_file or key_file not specified")
            return False

        if not self.cert_file.exists():
            logger.error(f"Certificate file not found: {self.cert_file}")
            return False

        if not self.key_file.exists():
            logger.error(f"Key file not found: {self.key_file}")
            return False

        if self.mtls_enabled:
            if not self.ca_file:
                logger.error("mTLS enabled but ca_file not specified")
                return False

            if not self.ca_file.exists():
                logger.error(f"CA certificate file not found: {self.ca_file}")
                return False

            logger.info(f"mTLS enabled with CA: {self.ca_file}")

        logger.info(f"TLS configuration validated: cert={self.cert_file}")
        return True

    def create_ssl_context(self) -> ssl.SSLContext | None:
        """
        Create SSL context for server.

        Returns:
            Configured ssl.SSLContext or None if TLS disabled
        """
        if not self.enabled:
            return None

        if not self.validate():
            raise ValueError("Invalid TLS configuration")

        # Create context with secure defaults
        try:
            # Use PROTOCOL_TLS_SERVER for server-side connections
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

            # Load certificate and key
            context.load_cert_chain(
                certfile=str(self.cert_file),
                keyfile=str(self.key_file),
            )

            # Set minimum TLS version
            min_version = getattr(ssl, f"TLSVersion.{self.minimum_version}")
            context.minimum_version = min_version
            logger.info(f"Set minimum TLS version: {self.minimum_version}")

            # Configure mTLS if enabled
            if self.mtls_enabled:
                verify_mode_value = getattr(ssl, self.verify_mode)
                context.verify_mode = verify_mode_value
                context.load_verify_locations(cafile=str(self.ca_file))
                logger.info(
                    f"mTLS enabled: verify_mode={self.verify_mode}, "
                    f"ca_file={self.ca_file}"
                )

            # Disable older/weaker ciphers
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!eNULL:!EXPORT:!DSS:!DES:!RC4:!MD5:!PSK"
            )
            context.options |= ssl.OP_NO_COMPRESSION

            logger.info("SSL context created successfully")
            return context

        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise


class ClientTLSConfig:
    """TLS configuration for client connections."""

    def __init__(
        self,
        verify_cert: bool = True,
        cert_file: str | Path | None = None,
        key_file: str | Path | None = None,
        ca_file: str | Path | None = None,
        minimum_version: str = "TLSv1_2",
    ):
        """
        Initialize client TLS configuration.

        Args:
            verify_cert: Verify server certificate
            cert_file: Path to client certificate (for mTLS)
            key_file: Path to client private key (for mTLS)
            ca_file: Path to CA certificate bundle
            minimum_version: Minimum TLS version to accept
        """
        self.verify_cert = verify_cert
        self.cert_file = Path(cert_file) if cert_file else None
        self.key_file = Path(key_file) if key_file else None
        self.ca_file = Path(ca_file) if ca_file else None
        self.minimum_version = minimum_version

    def get_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context for client.

        Returns:
            Configured ssl.SSLContext
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        if self.verify_cert:
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            if self.ca_file and self.ca_file.exists():
                context.load_verify_locations(cafile=str(self.ca_file))
                logger.info(f"Loaded CA certificate: {self.ca_file}")
            else:
                context.load_default_certs()
                logger.debug("Loaded system default certificates")
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            logger.warning("Certificate verification DISABLED")

        # Load client certificate if provided (for mTLS)
        if self.cert_file and self.key_file:
            if self.cert_file.exists() and self.key_file.exists():
                context.load_cert_chain(
                    certfile=str(self.cert_file),
                    keyfile=str(self.key_file),
                )
                logger.info(f"Loaded client certificate: {self.cert_file}")
            else:
                logger.warning("Client certificate or key file not found")

        # Set minimum TLS version
        min_version = getattr(ssl, f"TLSVersion.{self.minimum_version}")
        context.minimum_version = min_version

        return context
