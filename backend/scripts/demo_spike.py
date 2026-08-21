"""
PayPilot AI - Demo UPI Spike Injector
Injects a realistic 48-hour UPI timeout surge for live demo presentation without wiping existing DB data.

Usage:
    python -m scripts.demo_spike
"""
import sys
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.transaction import Transaction
from app.models.customer import Customer

settings = get_settings()
engine = create_engine(settings.DATABASE_URL_SYNC)

# Demo Merchant ID (TechBazaar India / demo@paypilot.ai)
MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def inject_demo_spike():
    print("=" * 60)
    print("PAYPILOT AI - INJECTING DEMO UPI FAILURE SPIKE")
    print("=" * 60)

    with Session(engine) as session:
        # Get existing customers for this merchant
        cust_stmt = select(Customer.id).where(Customer.merchant_id == MERCHANT_ID)
        customer_ids = list(session.scalars(cust_stmt).all())

        if not customer_ids:
            print("[WARN] No customers found for demo merchant. Please run python -m scripts.seed first.")
            return

        now = datetime.utcnow()
        transactions_to_add = []

        # 120 Failed UPI Transactions (within last 36 hours)
        total_failed_amount = Decimal("0")
        print("Injecting 120 failed UPI transactions (upi_timeout)...")
        for i in range(120):
            hours_ago = random.uniform(1, 36)
            tx_time = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
            
            # Realistic amounts between 850 and 7200 (avg ~2600)
            amount = Decimal(str(round(random.uniform(850.0, 7200.0), 2)))
            total_failed_amount += amount

            tx = Transaction(
                id=uuid.uuid4(),
                merchant_id=MERCHANT_ID,
                customer_id=random.choice(customer_ids),
                amount=amount,
                currency="INR",
                status="failed",
                payment_method="upi",
                payment_gateway="razorpay",
                failure_code="upi_timeout",
                failure_reason="UPI gateway timed out waiting for PSP response (NPCI latency spike)",
                description=f"E-commerce order checkout #{random.randint(50000, 99999)}",
                created_at=tx_time,
                updated_at=tx_time,
            )
            transactions_to_add.append(tx)

        # 60 Successful UPI Transactions (same period, representing partial success)
        total_captured_amount = Decimal("0")
        print("Injecting 60 successful UPI transactions...")
        for i in range(60):
            hours_ago = random.uniform(1, 36)
            tx_time = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
            amount = Decimal(str(round(random.uniform(600.0, 6500.0), 2)))
            total_captured_amount += amount

            tx = Transaction(
                id=uuid.uuid4(),
                merchant_id=MERCHANT_ID,
                customer_id=random.choice(customer_ids),
                amount=amount,
                currency="INR",
                status="captured",
                payment_method="upi",
                payment_gateway="razorpay",
                failure_code=None,
                failure_reason=None,
                description=f"E-commerce order checkout #{random.randint(50000, 99999)}",
                created_at=tx_time,
                updated_at=tx_time,
            )
            transactions_to_add.append(tx)

        session.add_all(transactions_to_add)
        session.commit()

        print("\n" + "=" * 60)
        print("[SUCCESS] SPIKE INJECTION COMPLETE")
        print("=" * 60)
        print(f"  Total Transactions Added:   {len(transactions_to_add)}")
        print(f"  Failed UPI Transactions:    120")
        print(f"  Failed Volume (At Risk):    INR {total_failed_amount:,.2f}")
        print(f"  Captured UPI Transactions:  60")
        print(f"  Captured Volume:            INR {total_captured_amount:,.2f}")
        print(f"  Spike Window:               Last 36 Hours")
        print(f"  Projected Recovery (70%):   INR {(total_failed_amount * Decimal('0.70')):,.2f}")
        print("=" * 60)
        print("Demo ready! Now run an investigation in Copilot or view the Dashboard.")


if __name__ == "__main__":
    inject_demo_spike()
