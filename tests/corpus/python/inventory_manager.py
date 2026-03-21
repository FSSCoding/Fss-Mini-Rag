"""Warehouse inventory management system.

Tracks stock levels, handles reordering, manages warehouse zones,
and generates inventory reports.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """Represents a product in the warehouse."""
    sku: str
    name: str
    category: str
    unit_price: float
    weight_kg: float
    zone: str = "general"
    min_stock: int = 10
    max_stock: int = 1000


@dataclass
class StockEntry:
    """A record of stock level change."""
    sku: str
    quantity_change: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    batch_id: Optional[str] = None


class WarehouseZone:
    """Represents a physical zone in the warehouse.

    Zones have temperature requirements, capacity limits,
    and specific product type restrictions.
    """

    def __init__(self, zone_id: str, name: str, capacity: int,
                 temperature_range: Tuple[float, float] = (15.0, 25.0)):
        self.zone_id = zone_id
        self.name = name
        self.capacity = capacity
        self.temperature_range = temperature_range
        self.current_occupancy = 0
        self.products: Dict[str, int] = {}

    def can_accept(self, quantity: int) -> bool:
        """Check if zone has capacity for additional stock."""
        return self.current_occupancy + quantity <= self.capacity

    def add_stock(self, sku: str, quantity: int) -> bool:
        """Add stock to this zone."""
        if not self.can_accept(quantity):
            logger.warning(f"Zone {self.zone_id} at capacity, cannot accept {quantity} units")
            return False
        self.products[sku] = self.products.get(sku, 0) + quantity
        self.current_occupancy += quantity
        return True

    def remove_stock(self, sku: str, quantity: int) -> bool:
        """Remove stock from this zone."""
        current = self.products.get(sku, 0)
        if current < quantity:
            return False
        self.products[sku] = current - quantity
        self.current_occupancy -= quantity
        return True

    def get_utilization(self) -> float:
        """Get zone utilization as percentage."""
        return (self.current_occupancy / self.capacity) * 100 if self.capacity > 0 else 0.0


class InventoryManager:
    """Central inventory management system.

    Coordinates stock across multiple warehouse zones,
    handles automatic reordering when stock drops below
    minimum levels, and generates comprehensive reports.
    """

    def __init__(self):
        self.products: Dict[str, Product] = {}
        self.zones: Dict[str, WarehouseZone] = {}
        self.stock_levels: Dict[str, int] = defaultdict(int)
        self.stock_history: List[StockEntry] = []
        self.pending_orders: List[Dict] = []

    def register_product(self, product: Product) -> None:
        """Register a new product in the inventory system."""
        self.products[product.sku] = product
        logger.info(f"Registered product: {product.name} (SKU: {product.sku})")

    def receive_shipment(self, sku: str, quantity: int, zone_id: str,
                         batch_id: Optional[str] = None) -> bool:
        """Process incoming shipment into a warehouse zone.

        Validates the product exists, checks zone capacity,
        updates stock levels, and records the transaction.
        """
        if sku not in self.products:
            logger.error(f"Unknown SKU: {sku}")
            return False

        zone = self.zones.get(zone_id)
        if not zone:
            logger.error(f"Unknown zone: {zone_id}")
            return False

        if not zone.add_stock(sku, quantity):
            return False

        self.stock_levels[sku] += quantity
        self.stock_history.append(StockEntry(
            sku=sku, quantity_change=quantity,
            reason="shipment_received", batch_id=batch_id
        ))

        self._check_reorder_status(sku)
        return True

    def fulfill_order(self, sku: str, quantity: int) -> bool:
        """Fulfill a customer order by reducing stock.

        Finds the best zone to pick from based on
        stock availability and zone priority.
        """
        if self.stock_levels.get(sku, 0) < quantity:
            logger.warning(f"Insufficient stock for {sku}: need {quantity}, have {self.stock_levels.get(sku, 0)}")
            return False

        remaining = quantity
        for zone in self.zones.values():
            zone_stock = zone.products.get(sku, 0)
            if zone_stock > 0:
                take = min(zone_stock, remaining)
                zone.remove_stock(sku, take)
                remaining -= take
                if remaining == 0:
                    break

        self.stock_levels[sku] -= quantity
        self.stock_history.append(StockEntry(
            sku=sku, quantity_change=-quantity,
            reason="order_fulfilled"
        ))

        self._check_reorder_status(sku)
        return True

    def _check_reorder_status(self, sku: str) -> None:
        """Check if stock is below minimum and trigger reorder."""
        product = self.products.get(sku)
        if not product:
            return

        current = self.stock_levels.get(sku, 0)
        if current < product.min_stock:
            reorder_qty = product.max_stock - current
            self.pending_orders.append({
                "sku": sku,
                "quantity": reorder_qty,
                "reason": f"Below minimum ({current} < {product.min_stock})",
                "created": datetime.now().isoformat(),
            })
            logger.info(f"Reorder triggered for {sku}: {reorder_qty} units")

    def generate_stock_report(self) -> Dict:
        """Generate comprehensive inventory report.

        Includes stock levels, zone utilization, low stock alerts,
        and pending reorder information.
        """
        low_stock = []
        for sku, level in self.stock_levels.items():
            product = self.products.get(sku)
            if product and level < product.min_stock:
                low_stock.append({
                    "sku": sku,
                    "name": product.name,
                    "current": level,
                    "minimum": product.min_stock,
                })

        zone_utilization = {
            zid: zone.get_utilization()
            for zid, zone in self.zones.items()
        }

        return {
            "total_products": len(self.products),
            "total_stock_units": sum(self.stock_levels.values()),
            "low_stock_alerts": low_stock,
            "zone_utilization": zone_utilization,
            "pending_reorders": len(self.pending_orders),
            "transaction_count": len(self.stock_history),
        }
