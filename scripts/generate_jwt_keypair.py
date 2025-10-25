"""Generate RSA key pair for Backend Services JWT authentication."""

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_keypair(output_dir: Path, kid: str = "ai-assistant-key-1") -> tuple[str, str, dict]:
    """
    Generate RSA key pair for JWT signing.

    Args:
        output_dir: Directory to save keys
        kid: Key ID for JWKS

    Returns:
        Tuple of (private_key_path, public_key_path, jwks_dict)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key to PEM format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Generate JWKS (JSON Web Key Set) for Keycloak
    public_numbers = public_key.public_numbers()

    # Convert to base64url encoding (without padding)
    def int_to_base64url(num: int) -> str:
        """Convert integer to base64url string."""
        # Get bytes with big-endian byte order
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
        # Encode to base64url (no padding)
        return base64.urlsafe_b64encode(num_bytes).decode("utf-8").rstrip("=")

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS384",
        "kid": kid,
        "n": int_to_base64url(public_numbers.n),
        "e": int_to_base64url(public_numbers.e),
    }

    jwks = {"keys": [jwk]}

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write private key
    private_key_path = output_dir / "ai_assistant_private.pem"
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_key_path, 0o600)  # Secure permissions

    # Write public key
    public_key_path = output_dir / "ai_assistant_public.pem"
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    # Write JWKS JSON
    jwks_path = output_dir / "ai_assistant_jwks.json"
    with open(jwks_path, "w") as f:
        json.dump(jwks, f, indent=2)

    print(f"✅ Private key saved to: {private_key_path}")
    print(f"✅ Public key saved to: {public_key_path}")
    print(f"✅ JWKS saved to: {jwks_path}")
    print("\n⚠️  Keep the private key secure! Add it to .gitignore")
    print("\n📋 Public key content (for Client registration):")
    print("=" * 70)
    print(public_pem.decode("utf-8"))
    print("=" * 70)

    return str(private_key_path), str(public_key_path), jwks


if __name__ == "__main__":
    # Generate keys in the mcp-server directory
    script_dir = Path(__file__).parent.parent
    keys_dir = script_dir / "keys"

    print("🔐 Generating RSA key pair for AI Assistant Backend Services auth...")
    private_path, public_path, jwks = generate_keypair(keys_dir)

    print("\n� JWKS for Keycloak (copy this to realm export):")
    print("=" * 70)
    print(json.dumps(jwks, indent=2))
    print("=" * 70)

    print("\n📝 Keycloak Configuration:")
    print("1. Open keycloak/realm-export.json")
    print("2. Find the 'ai-assistant-agent' client")
    print("3. Update the 'jwks.string' attribute with:")
    print(f"   {json.dumps(jwks)}")

    print("\n📝 Test Configuration:")
    print(f"1. Private key for tests: {private_path}")
    print("2. Add 'keys/' to .gitignore if not already present")
    print("3. Restart Keycloak to apply changes: docker compose restart keycloak")
