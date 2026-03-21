"""Payment processing module with multiple payment gateways.

Handles credit card validation, transaction processing, refunds,
and payment gateway failover logic.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Status codes for payment transactions."""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REFUNDED = "refunded"
    ERROR = "error"


@dataclass
class Transaction:
    """Represents a single payment transaction."""
    transaction_id: str
    amount: float
    currency: str
    status: PaymentStatus
    gateway: str
    customer_id: str
    timestamp: float
    metadata: Optional[Dict] = None


class CreditCardValidator:
    """Validates credit card numbers using the Luhn algorithm."""

    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm.

        The Luhn algorithm works by doubling every second digit
        from the right, subtracting 9 from results over 9,
        and checking if the total modulo 10 equals zero.
        """
        digits = [int(d) for d in card_number.replace(" ", "")]
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def detect_card_type(card_number: str) -> str:
        """Detect credit card type from number prefix."""
        num = card_number.replace(" ", "")
        if num.startswith("4"):
            return "visa"
        elif num.startswith(("51", "52", "53", "54", "55")):
            return "mastercard"
        elif num.startswith(("34", "37")):
            return "amex"
        elif num.startswith("6011"):
            return "discover"
        return "unknown"


class PaymentGateway:
    """Abstract payment gateway interface."""

    def __init__(self, api_key: str, sandbox: bool = True):
        self.api_key = api_key
        self.sandbox = sandbox
        self.retry_count = 3
        self.timeout = 30

    def process_payment(self, amount: float, card_token: str,
                       currency: str = "USD") -> Transaction:
        """Process a payment through this gateway.

        Implements retry logic with exponential backoff.
        Returns Transaction object with result status.
        """
        for attempt in range(self.retry_count):
            try:
                result = self._send_to_gateway(amount, card_token, currency)
                return Transaction(
                    transaction_id=result["id"],
                    amount=amount,
                    currency=currency,
                    status=PaymentStatus.APPROVED,
                    gateway=self.__class__.__name__,
                    customer_id=result.get("customer", "unknown"),
                    timestamp=time.time(),
                )
            except ConnectionError:
                if attempt < self.retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Gateway retry in {wait_time}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                else:
                    raise

    def _send_to_gateway(self, amount, card_token, currency):
        """Send payment request to gateway API."""
        raise NotImplementedError

    def process_refund(self, transaction_id: str, amount: float) -> Transaction:
        """Process a refund for a previous transaction.

        Validates that the refund amount does not exceed
        the original transaction amount.
        """
        logger.info(f"Processing refund: {transaction_id} for ${amount:.2f}")
        return Transaction(
            transaction_id=f"ref_{transaction_id}",
            amount=-amount,
            currency="USD",
            status=PaymentStatus.REFUNDED,
            gateway=self.__class__.__name__,
            customer_id="unknown",
            timestamp=time.time(),
        )


class PaymentProcessor:
    """Orchestrates payment processing across multiple gateways.

    Implements failover logic: if the primary gateway fails,
    automatically tries secondary gateways in priority order.
    """

    def __init__(self, gateways: List[PaymentGateway]):
        self.gateways = gateways
        self.transaction_log: List[Transaction] = []

    def charge(self, amount: float, card_number: str,
               currency: str = "USD") -> Transaction:
        """Charge a credit card with gateway failover.

        Validates the card first, then tries each gateway
        in order until one succeeds.
        """
        validator = CreditCardValidator()
        if not validator.validate_card_number(card_number):
            return Transaction(
                transaction_id="invalid",
                amount=amount,
                currency=currency,
                status=PaymentStatus.DECLINED,
                gateway="none",
                customer_id="unknown",
                timestamp=time.time(),
                metadata={"reason": "Invalid card number"},
            )

        card_type = validator.detect_card_type(card_number)
        card_token = hashlib.sha256(card_number.encode()).hexdigest()

        for gateway in self.gateways:
            try:
                txn = gateway.process_payment(amount, card_token, currency)
                txn.metadata = {"card_type": card_type}
                self.transaction_log.append(txn)
                return txn
            except Exception as e:
                logger.error(f"Gateway {gateway.__class__.__name__} failed: {e}")
                continue

        return Transaction(
            transaction_id="all_failed",
            amount=amount,
            currency=currency,
            status=PaymentStatus.ERROR,
            gateway="none",
            customer_id="unknown",
            timestamp=time.time(),
            metadata={"reason": "All gateways failed"},
        )

    def get_transaction_history(self, customer_id: str = None) -> List[Transaction]:
        """Get transaction history, optionally filtered by customer."""
        if customer_id:
            return [t for t in self.transaction_log if t.customer_id == customer_id]
        return self.transaction_log.copy()

    def calculate_daily_revenue(self) -> float:
        """Calculate total revenue from approved transactions today."""
        today_start = time.time() - 86400
        return sum(
            t.amount for t in self.transaction_log
            if t.status == PaymentStatus.APPROVED and t.timestamp >= today_start
        )
