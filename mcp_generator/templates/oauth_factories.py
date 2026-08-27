"""
Auth provider factories emitted into the generated oauth_provider module.

Static template text with no interpolation, kept out of the assembly
function so that module stays within the size gate.
"""

AUTH_PROVIDER_FACTORIES = '''def create_multi_auth_verifier(
    providers: list[dict] | None = None,
) -> Optional["MultiAuth"]:
    """Create a MultiAuth verifier composing multiple token verification sources.

    This is useful when you need to accept tokens from more than one provider
    (e.g., internal JWTs alongside a third-party OAuth provider).

    Requires FastMCP >= 3.1.

    Args:
        providers: List of provider configs, each with 'jwks_uri', 'issuer', 'audience'.
                   Falls back to the default single JWTVerifier if empty.

    Returns:
        MultiAuth instance or None if not available/configured.
    """
    try:
        from fastmcp.server.auth import MultiAuth
    except ImportError:
        logger.warning("MultiAuth not available (requires fastmcp>=3.1)")
        return None

    verifiers = []

    # Always include the primary verifier
    primary = create_jwt_verifier()
    if primary:
        verifiers.append(primary)

    # Add additional providers from config
    if providers:
        for prov in providers:
            try:
                v = JWTVerifier(
                    jwks_uri=prov.get("jwks_uri", ""),
                    issuer=prov.get("issuer", ""),
                    audience=prov.get("audience", ""),
                    required_scopes=prov.get("required_scopes", []),
                )
                verifiers.append(v)
                logger.info("  MultiAuth: Added provider issuer=%s", prov.get("issuer"))
            except Exception as exc:
                logger.warning("  MultiAuth: Failed to add provider: %s", exc)

    if not verifiers:
        return None

    logger.info("MultiAuth configured with %d token verifiers", len(verifiers))
    return MultiAuth(verifiers)


def create_propelauth_provider(
    config: dict | None = None,
) -> Optional["PropelAuthProvider"]:
    """Create a PropelAuth authentication provider.

    PropelAuth provides enterprise-grade authentication with
    built-in token introspection and user management.

    Requires FastMCP >= 3.1.

    Args:
        config: PropelAuth configuration dict with keys:
            - auth_url: PropelAuth API URL
            - introspection_client_id: Client ID for token introspection
            - introspection_client_secret: Client secret for introspection
            - base_url: Base URL for the MCP server
            - required_scopes: Optional list of required scopes

    Returns:
        PropelAuthProvider instance or None if not available/configured.
    """
    try:
        from fastmcp.server.auth.providers.propelauth import PropelAuthProvider
    except ImportError:
        logger.warning("PropelAuth not available (requires fastmcp>=3.1)")
        return None

    config = config or {}
    auth_url = config.get("auth_url")
    client_id = config.get("introspection_client_id")
    client_secret = config.get("introspection_client_secret")
    base_url = config.get("base_url", API_BASE_URL)
    required_scopes = config.get("required_scopes")

    if not all([auth_url, client_id, client_secret]):
        logger.error("PropelAuth requires auth_url, introspection_client_id, and introspection_client_secret")
        return None

    try:
        provider = PropelAuthProvider(
            auth_url=auth_url,
            introspection_client_id=client_id,
            introspection_client_secret=client_secret,
            base_url=base_url,
            required_scopes=required_scopes,
        )
        logger.info("PropelAuth provider configured: %s", auth_url)
        return provider
    except Exception as exc:
        logger.error("Failed to create PropelAuth provider: %s", exc)
        return None


def create_oauth_proxy(
    config: dict | None = None,
) -> Optional[Any]:
    """Create an OAuthProxy for bridging non-DCR IdPs to MCP-compatible auth.

    OAuthProxy presents a DCR-compliant interface while proxying to enterprise
    IdPs (Auth0, Okta, Azure AD, Google, GitHub) that don't support Dynamic
    Client Registration. This enables production HTTP deployments with real SSO.

    Requires FastMCP >= 3.1 and a pre-registered OAuth app with the upstream IdP.

    Args:
        config: OAuth Proxy configuration dict with keys:
            - upstream_authorization_endpoint: IdP authorization URL
            - upstream_token_endpoint: IdP token URL
            - upstream_client_id: Pre-registered app client ID
            - upstream_client_secret: Pre-registered app client secret
            - upstream_revocation_endpoint: (optional) Token revocation URL
            - base_url: Public URL of this MCP server
            - redirect_path: (optional) Callback path (default: /oauth/callback)
            - valid_scopes: (optional) List of allowed scopes
            - forward_pkce: (optional) Forward PKCE to upstream (default: true)

    Returns:
        OAuthProxy instance or None if not available/configured.
    """
    try:
        from fastmcp.server.auth.oauth_proxy import OAuthProxy
    except ImportError:
        logger.warning("OAuthProxy not available (requires fastmcp>=3.1)")
        return None

    config = config or {}
    auth_endpoint = config.get("upstream_authorization_endpoint")
    token_endpoint = config.get("upstream_token_endpoint")
    client_id = config.get("upstream_client_id")
    client_secret = config.get("upstream_client_secret")
    base_url = config.get("base_url", API_BASE_URL)

    if not all([auth_endpoint, token_endpoint, client_id, client_secret]):
        logger.error(
            "OAuthProxy requires upstream_authorization_endpoint, upstream_token_endpoint, "
            "upstream_client_id, and upstream_client_secret"
        )
        return None

    try:
        # Create a JWTVerifier for token validation (reuse existing config)
        token_verifier = create_jwt_verifier()
        if not token_verifier:
            logger.error("OAuthProxy requires a working JWTVerifier for token validation")
            return None

        proxy_kwargs = {
            "upstream_authorization_endpoint": auth_endpoint,
            "upstream_token_endpoint": token_endpoint,
            "upstream_client_id": client_id,
            "upstream_client_secret": client_secret,
            "token_verifier": token_verifier,
            "base_url": base_url,
        }

        # Optional parameters
        if config.get("upstream_revocation_endpoint"):
            proxy_kwargs["upstream_revocation_endpoint"] = config["upstream_revocation_endpoint"]
        if config.get("redirect_path"):
            proxy_kwargs["redirect_path"] = config["redirect_path"]
        if config.get("valid_scopes"):
            proxy_kwargs["valid_scopes"] = config["valid_scopes"]
        if "forward_pkce" in config:
            proxy_kwargs["forward_pkce"] = config["forward_pkce"]

        proxy = OAuthProxy(**proxy_kwargs)
        logger.info("OAuthProxy configured: auth=%s, token=%s", auth_endpoint, token_endpoint)
        logger.info("  Base URL: %s", base_url)
        logger.info("  Client ID: %s", client_id[:8] + "..." if len(client_id) > 8 else client_id)
        return proxy

    except Exception as exc:
        logger.error("Failed to create OAuthProxy: %s", exc)
        return None


def create_keycloak_provider(
    config: dict | None = None,
) -> Optional[Any]:
    """Create a Keycloak authentication provider.

    Uses FastMCP's built-in KeycloakAuthProvider (a slim RemoteAuthProvider
    subclass) that auto-discovers OIDC endpoints from the Keycloak realm URL
    and validates JWT tokens via the realm's JWKS endpoint.

    Requires FastMCP >= 3.2.4 and Keycloak >= 26.6.0 (native DCR support).

    Args:
        config: Keycloak configuration dict with keys:
            - realm_url: Full URL to the Keycloak realm
              (e.g. "https://keycloak.example.com/realms/myrealm")
            - required_scopes: Optional list of required scopes
            - audience: Optional audience claim (defaults to realm URL)

    Returns:
        KeycloakAuthProvider instance or None if not available/configured.
    """
    try:
        from fastmcp.server.auth.providers.keycloak import KeycloakAuthProvider
    except ImportError:
        logger.warning("KeycloakAuthProvider not available (requires fastmcp>=3.2.4)")
        return None

    config = config or {}
    realm_url = config.get("realm_url")

    if not realm_url:
        logger.error("Keycloak requires realm_url (e.g. 'https://keycloak.example.com/realms/myrealm')")
        return None

    try:
        provider = KeycloakAuthProvider(
            realm_url=realm_url,
            required_scopes=config.get("required_scopes"),
            audience=config.get("audience"),
        )
        logger.info("Keycloak provider configured: %s", realm_url)
        return provider
    except Exception as exc:
        logger.error("Failed to create Keycloak provider: %s", exc)
        return None
'''
