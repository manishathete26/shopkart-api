import os

from fastapi import HTTPException
from fastapi_mail import ConnectionConfig


def get_mail_config() -> ConnectionConfig:
    """Build Gmail SMTP configuration from environment variables."""
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    from_email = os.getenv("MAIL_FROM") or username
    server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    port_value = os.getenv("MAIL_PORT", "587")
    use_ssl = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
    use_starttls = os.getenv("MAIL_STARTTLS", "true").lower() == "true"

    if not all((username, password, from_email, server, port_value)):
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured.",
        )

    try:
        mail_port = int(port_value)
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured.",
        ) from error

    use_ssl = os.getenv("MAIL_SSL_TLS", "true").lower() == "true"
    use_starttls = os.getenv("MAIL_STARTTLS", "false").lower() == "true"

    return ConnectionConfig(
        MAIL_USERNAME=username,
        MAIL_PASSWORD=password,
        MAIL_FROM=from_email,
        MAIL_PORT=mail_port,
        MAIL_SERVER=server,
        MAIL_STARTTLS=use_starttls,
        MAIL_SSL_TLS=use_ssl,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
