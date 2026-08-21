"""
PayPilot AI - Seed Data Generator
Generates realistic demo data with intentional patterns for hackathon demo.
Run: python -m scripts.seed
"""
import sys
import os
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import Base
from app.models import (
    User, Merchant, Customer, Transaction, Refund, PaymentMethod,
    PaymentFailure, Payout, CashFlowEvent, AIAction, AuditLog
)
from app.services.auth import AuthService

settings = get_settings()
engine = create_engine(settings.DATABASE_URL_SYNC)

# Deterministic UUIDs for the demo
MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEMO_MERCHANT_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")

ADMIN_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ANALYST_USER_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
MERCHANT_2_USER_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")

PAYMENT_METHODS = ["upi", "card", "netbanking", "wallet", "emi"]
FAILURE_CODES = [
    "upi_timeout", "bank_unavailable", "insufficient_funds", 
    "card_declined", "card_expired", "authentication_failed", 
    "network_error", "session_expired", "limit_exceeded"
]
FAILURE_REASONS = {
    "upi_timeout": "UPI gateway timed out waiting for response",
    "bank_unavailable": "Issuer bank is currently unavailable",
    "insufficient_funds": "Insufficient funds in the account",
    "card_declined": "Card was declined by the issuing bank",
    "card_expired": "The card has expired",
    "authentication_failed": "3D Secure authentication failed",
    "network_error": "Network connection dropped during transaction",
    "session_expired": "Payment session expired before completion",
    "limit_exceeded": "Transaction amount exceeds daily limit",
}

INDIAN_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", 
    "Shaurya", "Atharva", "Ananya", "Myra", "Saanvi", "Aadya", "Kiara", "Diya", "Pihu", "Prisha", 
    "Navya", "Kavya", "Rahul", "Priya", "Amit", "Sneha", "Karan", "Pooja", "Vikram", "Riya", 
    "Rohit", "Neha", "Sanjay", "Kriti", "Ravi", "Divya"
]
INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Singh", "Patel", "Kumar", "Shah", "Mehta", "Reddy", 
    "Joshi", "Kapoor", "Yadav", "Chauhan", "Bhatia", "Iyer", "Nair", "Desai", "Menon", "Bose", 
    "Das", "Roy", "Sen", "Sinha", "Mishra", "Pandey"
]
CATEGORIES = ["Electronics", "Fashion", "Food", "Services", "Digital", "Health"]


def seed_merchants(session: Session):
    merchants = [
        Merchant(
            id=MERCHANT_ID,
            name="Arjun Mehta",
            business_name="TechBazaar India",
            email="demo@paypilot.ai",
            phone="+919876543210",
            business_type="ecommerce",
            currency="INR",
            current_balance=Decimal("92000.00"),
        ),
        Merchant(
            id=DEMO_MERCHANT_2,
            name="Priya Sharma",
            business_name="FashionHub Online",
            email="priya@fashionhub.in",
            phone="+919876543211",
            business_type="ecommerce",
            currency="INR",
            current_balance=Decimal("156000.00"),
        ),
    ]
    session.add_all(merchants)
    session.flush()
    print(f"  Created {len(merchants)} merchants")
    return merchants


def seed_users(session: Session):
    users = [
        User(
            id=ADMIN_USER_ID,
            email="demo@paypilot.ai",
            hashed_password=AuthService.hash_password("demo123"),
            full_name="Arjun Mehta",
            role="merchant_admin",
            merchant_id=MERCHANT_ID,
            is_active=True,
        ),
        User(
            id=ANALYST_USER_ID,
            email="analyst@paypilot.ai",
            hashed_password=AuthService.hash_password("analyst123"),
            full_name="Neha Kapoor",
            role="analyst",
            merchant_id=MERCHANT_ID,
            is_active=True,
        ),
        User(
            id=MERCHANT_2_USER_ID,
            email="priya@fashionhub.in",
            hashed_password=AuthService.hash_password("priya123"),
            full_name="Priya Sharma",
            role="merchant_admin",
            merchant_id=DEMO_MERCHANT_2,
            is_active=True,
        ),
    ]
    session.add_all(users)
    session.flush()
    print(f"  Created {len(users)} users")
    return users


def seed_customers(session: Session, merchant_id: uuid.UUID, count: int = 500):
    customers = []
    for i in range(count):
        first_name = random.choice(INDIAN_FIRST_NAMES)
        last_name = random.choice(INDIAN_LAST_NAMES)
        customers.append(Customer(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            name=f"{first_name} {last_name}",
            email=f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@example.com",
            phone=f"+91{random.randint(7000000000, 9999999999)}",
            total_orders=random.randint(1, 50),
            total_spent=random.randint(500, 100000),
        ))
    session.add_all(customers)
    session.flush()
    print(f"  Created {count} customers")
    return customers


def seed_transactions(session: Session, merchant_id: uuid.UUID, customers: list):
    now = datetime.utcnow()
    transactions = []

    for day_offset in range(90, -1, -1):
        day = now - timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5

        if is_weekend:
            base_count = random.randint(120, 180)
        else:
            base_count = random.randint(180, 250)

        # Introduce patterns for the demo
        if day_offset <= 3:
            # Recent spike in failures
            failure_multiplier = 2.5
            if day_offset == 0:
                base_count = int(base_count * 0.7) # partial day
        elif day_offset <= 7:
            failure_multiplier = 1.8
        else:
            failure_multiplier = 1.0

        for txn_num in range(base_count):
            customer = random.choice(customers)
            amount = Decimal(str(round(random.uniform(150, 25000), 2)))
            method = random.choices(
                PAYMENT_METHODS,
                weights=[35, 25, 20, 15, 5],
            )[0]

            base_success_rate = 0.92 if day_offset <= 3 else 0.96
            
            # Create a specific UPI failure spike for the demo narrative
            failure_code_weights = [1] * len(FAILURE_CODES)
            if day_offset <= 3 and method == "upi":
                base_success_rate -= 0.15 # Big drop in UPI success
                failure_code_weights[FAILURE_CODES.index("upi_timeout")] = 10 # Mostly timeouts
                failure_code_weights[FAILURE_CODES.index("bank_unavailable")] = 5

            is_success = random.random() < (base_success_rate / failure_multiplier)

            if is_success:
                status = "captured"
                failure_code = None
                failure_reason = None
            else:
                status = "failed"
                failure_code = random.choices(FAILURE_CODES, weights=failure_code_weights)[0]
                failure_reason = FAILURE_REASONS.get(failure_code, "Payment failed")

            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            created_at = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            txn = Transaction(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                customer_id=customer.id,
                amount=amount,
                currency="INR",
                status=status,
                payment_method=method,
                payment_gateway="razorpay",
                failure_code=failure_code,
                failure_reason=failure_reason,
                description=f"Order from {customer.name}",
                created_at=created_at,
                updated_at=created_at,
            )
            transactions.append(txn)

    session.add_all(transactions)
    session.flush()
    print(f"  Created {len(transactions)} transactions")

    failed = [t for t in transactions if t.status == "failed"]
    print(f"  Failed transactions: {len(failed)} ({len(failed)/len(transactions)*100:.1f}%)")
    return transactions


def seed_payment_failures(session: Session, merchant_id: uuid.UUID, transactions: list):
    failures = []
    failed_txns = [t for t in transactions if t.status == "failed"]
    for txn in failed_txns:
        is_retryable = "true" if txn.failure_code in ["network_error", "upi_timeout", "insufficient_funds"] else "false"
        failures.append(PaymentFailure(
            id=uuid.uuid4(),
            transaction_id=txn.id,
            merchant_id=merchant_id,
            error_code=txn.failure_code or "payment_failed",
            error_message=txn.failure_reason,
            payment_method=txn.payment_method,
            amount=txn.amount,
            is_retryable=is_retryable,
            recovered="false",
            created_at=txn.created_at,
        ))
    session.add_all(failures)
    session.flush()
    print(f"  Created {len(failures)} payment failures")


def seed_refunds(session: Session, merchant_id: uuid.UUID, transactions: list):
    refunds = []
    captured = [t for t in transactions if t.status == "captured"]
    refund_count = int(len(captured) * 0.03)

    now = datetime.utcnow()
    for i in range(refund_count):
        txn = random.choice(captured)
        refund_pct = Decimal(str(round(random.uniform(0.1, 1.0), 2)))
        refund_amount = txn.amount * refund_pct

        if txn.created_at <= now - timedelta(days=3):
            created_at = txn.created_at + timedelta(days=random.randint(1, 3))
        else:
            created_at = txn.created_at + timedelta(hours=random.randint(1, 24))

        refunds.append(Refund(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            transaction_id=txn.id,
            amount=refund_amount.quantize(Decimal("0.01")),
            status="processed",
            reason=random.choice([
                "Customer requested refund",
                "Product not as described",
                "Duplicate charge",
                "Order cancelled",
                "Quality issue",
            ]),
            created_at=created_at,
        ))
    session.add_all(refunds)
    session.flush()
    print(f"  Created {len(refunds)} refunds")


def seed_payouts(session: Session, merchant_id: uuid.UUID):
    payouts = []
    now = datetime.utcnow()
    for day_offset in range(90, -1, -1):
        if day_offset % 3 == 0:
            day = now - timedelta(days=day_offset)
            amount = Decimal(str(round(random.uniform(25000, 150000), 2)))
            payouts.append(Payout(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                amount=amount,
                status="processed",
                payout_method="bank_transfer",
                reference=f"PO-{day.strftime('%Y%m%d')}-{random.randint(1000,9999)}",
                created_at=day.replace(hour=10, minute=0, second=0),
            ))
    session.add_all(payouts)
    session.flush()
    print(f"  Created {len(payouts)} payouts")


def seed_cash_flow_events(session: Session, merchant_id: uuid.UUID):
    events = []
    now = datetime.utcnow()
    for day_offset in range(30, -1, -1):
        day = now - timedelta(days=day_offset)
        inflow = Decimal(str(round(random.uniform(40000, 120000), 2)))
        events.append(CashFlowEvent(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            type="inflow",
            amount=inflow,
            description=f"Daily payment collections",
            source="payments",
            created_at=day.replace(hour=23, minute=0, second=0),
        ))
        if day_offset % 3 == 0:
            outflow = Decimal(str(round(random.uniform(20000, 80000), 2)))
            events.append(CashFlowEvent(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                type="outflow",
                amount=outflow,
                description="Payout to bank account",
                source="payout",
                created_at=day.replace(hour=10, minute=0, second=0),
            ))
    session.add_all(events)
    session.flush()
    print(f"  Created {len(events)} cash flow events")


def seed_payment_methods(session: Session, merchant_id: uuid.UUID):
    methods = [
        PaymentMethod(id=uuid.uuid4(), merchant_id=merchant_id, name="UPI", type="upi", success_rate=Decimal("94.50"), total_transactions=Decimal("45000")),
        PaymentMethod(id=uuid.uuid4(), merchant_id=merchant_id, name="Credit/Debit Card", type="card", success_rate=Decimal("97.20"), total_transactions=Decimal("30000")),
        PaymentMethod(id=uuid.uuid4(), merchant_id=merchant_id, name="Net Banking", type="netbanking", success_rate=Decimal("96.80"), total_transactions=Decimal("22000")),
        PaymentMethod(id=uuid.uuid4(), merchant_id=merchant_id, name="Wallets", type="wallet", success_rate=Decimal("98.10"), total_transactions=Decimal("18000")),
        PaymentMethod(id=uuid.uuid4(), merchant_id=merchant_id, name="EMI", type="emi", success_rate=Decimal("91.50"), total_transactions=Decimal("5000")),
    ]
    session.add_all(methods)
    session.flush()
    print(f"  Created {len(methods)} payment methods")


def seed_ai_actions_and_audits(session: Session, merchant_id: uuid.UUID, user_id: uuid.UUID):
    now = datetime.utcnow()
    
    # Pre-seed a pending action for the demo
    pending_action = AIAction(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        user_id=user_id,
        action_type="bulk_payment_retry",
        action_class="reversible",
        description="Initiate Smart Retry for 127 failed UPI transactions due to recent timeout spike.",
        reason="Detected elevated UPI timeout rate in the last 72 hours. 127 transactions are eligible for Smart Retry via alternative payment gateways.",
        input_data={"target_failure_code": "upi_timeout", "time_window_hours": 72, "eligible_count": 127},
        estimated_impact=Decimal("345000.00"),
        risk_level="low",
        approval_status="pending",
        execution_status="not_started",
        created_at=now - timedelta(minutes=15)
    )
    
    executed_action = AIAction(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        user_id=user_id,
        action_type="configure_routing",
        action_class="reversible",
        description="Reroute HDFC Netbanking traffic to backup gateway.",
        reason="HDFC Netbanking showed 3 consecutive hours of elevated failure rates.",
        input_data={"bank": "HDFC", "method": "netbanking", "primary": "razorpay", "backup": "ccavenue"},
        output_data={"status": "success", "executed_at": (now - timedelta(days=2)).isoformat()},
        estimated_impact=Decimal("125000.00"),
        risk_level="medium",
        approval_status="approved",
        approved_by=user_id,
        approved_at=now - timedelta(days=2, hours=1),
        execution_status="completed",
        executed_at=now - timedelta(days=2),
        created_at=now - timedelta(days=2, hours=2)
    )
    
    session.add_all([pending_action, executed_action])
    
    # Audit Logs
    audits = [
        AuditLog(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            user_id=None,
            action="system_scan",
            resource_type="anomaly_detector",
            details={"findings": "Detected UPI timeout anomaly", "severity": "warning"},
            created_at=now - timedelta(hours=3)
        ),
        AuditLog(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            user_id=None,
            action="ai_investigation_started",
            resource_type="investigation",
            details={"trigger": "anomaly_detected", "focus": "upi_timeout"},
            created_at=now - timedelta(hours=2)
        ),
        AuditLog(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            user_id=None,
            action="action_proposed",
            resource_type="ai_action",
            resource_id=str(pending_action.id),
            details={"type": "bulk_payment_retry", "impact": "345000.00 INR"},
            created_at=pending_action.created_at
        )
    ]
    session.add_all(audits)
    
    session.flush()
    print("  Created AI actions and audit logs")

def main():
    print("=" * 60)
    print("PayPilot AI - Seed Data Generator")
    print("=" * 60)

    # Make generation deterministic
    random.seed(42)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Database tables recreated")

    with Session(engine) as session:
        print("\nSeeding merchants...")
        seed_merchants(session)

        print("\nSeeding users...")
        seed_users(session)

        print("\nSeeding customers...")
        customers = seed_customers(session, MERCHANT_ID, count=500)

        print("\nSeeding payment methods...")
        seed_payment_methods(session, MERCHANT_ID)

        print("\nSeeding transactions (this may take a moment)...")
        transactions = seed_transactions(session, MERCHANT_ID, customers)

        print("\nSeeding payment failures...")
        seed_payment_failures(session, MERCHANT_ID, transactions)

        print("\nSeeding refunds...")
        seed_refunds(session, MERCHANT_ID, transactions)

        print("\nSeeding payouts...")
        seed_payouts(session, MERCHANT_ID)

        print("\nSeeding cash flow events...")
        seed_cash_flow_events(session, MERCHANT_ID)
        
        print("\nSeeding AI actions and audits...")
        seed_ai_actions_and_audits(session, MERCHANT_ID, ADMIN_USER_ID)

        session.commit()

    print("\n" + "=" * 60)
    print("Seed complete!")
    print(f"\nDemo credentials:")
    print(f"  Email: demo@paypilot.ai")
    print(f"  Password: demo123")
    print(f"\nAnalyst account:")
    print(f"  Email: analyst@paypilot.ai")
    print(f"  Password: analyst123")
    print("=" * 60)


if __name__ == "__main__":
    main()
