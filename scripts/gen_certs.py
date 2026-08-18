"""
Helpful scripts for generating TLS certificates.

USAGE:
    # Generate self-signed certificate for development
    python scripts/gen_certs.py --output-dir ./certs --dev

    # Generate server certificate
    python scripts/gen_certs.py --output-dir ./certs --cert-type server

    # Generate client certificate for mTLS
    python scripts/gen_certs.py --output-dir ./certs --cert-type client
"""

import argparse
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_self_signed_cert(
    output_dir: Path,
    days: int = 365,
    key_size: int = 2048,
) -> tuple[Path, Path]:
    """
    Generate self-signed certificate for development.

    Args:
        output_dir: Directory to save certificate and key
        days: Certificate validity period
        key_size: RSA key size

    Returns:
        Tuple of (cert_path, key_path)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cert_path = output_dir / "server.crt"
    key_path = output_dir / "server.key"

    cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        f"rsa:{key_size}",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-days",
        str(days),
        "-nodes",
        "-subj",
        "/C=US/ST=CA/L=San Francisco/O=cpip/CN=localhost",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Generated self-signed certificate: {cert_path}")
        logger.info(f"Generated private key: {key_path}")
        return cert_path, key_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate certificate: {e}")
        raise


def generate_ca_cert(
    output_dir: Path,
    days: int = 3650,
    key_size: int = 2048,
) -> tuple[Path, Path]:
    """
    Generate CA certificate for mTLS.

    Args:
        output_dir: Directory to save certificate and key
        days: Certificate validity period
        key_size: RSA key size

    Returns:
        Tuple of (ca_cert_path, ca_key_path)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ca_cert_path = output_dir / "ca.crt"
    ca_key_path = output_dir / "ca.key"

    cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        f"rsa:{key_size}",
        "-keyout",
        str(ca_key_path),
        "-out",
        str(ca_cert_path),
        "-days",
        str(days),
        "-nodes",
        "-subj",
        "/C=US/ST=CA/L=San Francisco/O=cpip/CN=cpip-ca",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Generated CA certificate: {ca_cert_path}")
        logger.info(f"Generated CA key: {ca_key_path}")
        return ca_cert_path, ca_key_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate CA certificate: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate TLS certificates for cpip")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="./certs",
        help="Output directory for certificates",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Generate self-signed certificate for development",
    )
    parser.add_argument(
        "--ca",
        action="store_true",
        help="Generate CA certificate for mTLS",
    )

    args = parser.parse_args()

    if args.dev:
        logger.info("Generating development self-signed certificate...")
        generate_self_signed_cert(args.output_dir)

    if args.ca:
        logger.info("Generating CA certificate for mTLS...")
        generate_ca_cert(args.output_dir)

    if not args.dev and not args.ca:
        logger.info("Generating development certificate by default...")
        generate_self_signed_cert(args.output_dir)


if __name__ == "__main__":
    main()
