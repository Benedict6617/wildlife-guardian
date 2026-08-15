"""
SMS gateway abstraction for community alerts.

Production deployments in East Africa typically use Africa's Talking or
Twilio for SMS delivery. This module defines a small provider interface and
ships a `SimulatedGateway` that logs sends and always "delivers" -- so the
whole platform is runnable and demoable with zero external credentials.

To go live: implement `send()` for `AfricasTalkingGateway` /
`TwilioGateway` using the vendor SDK and set SMS_PROVIDER in the
environment. No other application code needs to change.
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger("wildlife_guardian.sms")


class SMSGateway(ABC):
    @abstractmethod
    def send(self, recipients: List[str], message: str) -> dict:
        """Returns {'delivered': int, 'failed': int, 'status': str}."""
        raise NotImplementedError


class SimulatedGateway(SMSGateway):
    """Default gateway for local/dev/demo use. No network calls."""

    def send(self, recipients: List[str], message: str) -> dict:
        logger.info("SIMULATED SMS to %d recipients: %s", len(recipients), message)
        return {"delivered": len(recipients), "failed": 0, "status": "delivered"}


def get_gateway() -> SMSGateway:
    provider = os.getenv("SMS_PROVIDER", "simulated").lower()
    if provider == "simulated":
        return SimulatedGateway()
    # Placeholder branches for real integrations -- implemented at deployment
    # time once vendor credentials are provisioned.
    raise NotImplementedError(
        f"SMS provider '{provider}' is not wired up yet. "
        "Implement an SMSGateway subclass and register it here."
    )
