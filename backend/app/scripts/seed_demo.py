"""
Seed a demo account with six months of realistic transactions.

    uv run poe seed-demo

An empty dashboard shows nothing but empty states, which makes the app
impossible to demo and hard to develop the charts against. This creates
one account with enough history for every panel to have something real
to render: month-over-month trends, a category breakdown that isn't one
bar, and a genuine spending spike for the insights list to find.

Re-running it wipes and rebuilds the demo user's transactions only. No
other account is touched.
"""

import random
from datetime import date, timedelta

from backend.app.core.security import hash_password
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models.category import DEFAULT_CATEGORIES, Category
from backend.app.models.transaction import (
    CategorySource,
    Transaction,
    TransactionSource,
    TransactionType,
)
from backend.app.models.user import User
from backend.app.services.categorization.rule_based import categorize

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Demo User"

MONTHS_OF_HISTORY = 6

# Merchants the rule-based categorizer already recognises, so the seeded
# data also demonstrates auto-categorization rather than needing the
# categories hardcoded here. (min, max) is the per-transaction range.
MERCHANTS: list[tuple[str, int, float, float]] = [
    # (description, roughly how many times a month, min amount, max amount)
    ("SWIGGY ORDER", 6, 180, 650),
    ("ZOMATO ORDER", 4, 200, 700),
    ("BIG BAZAAR GROCERY", 3, 800, 2500),
    ("STARBUCKS COFFEE", 3, 250, 480),
    ("UBER TRIP", 8, 90, 420),
    ("OLA CAB RIDE", 3, 110, 380),
    ("INDIAN OIL PETROL", 2, 1500, 3000),
    ("IRCTC TRAIN BOOKING", 1, 450, 1800),
    ("AMAZON MKTPLACE", 4, 400, 4500),
    ("FLIPKART ORDER", 2, 600, 5000),
    ("MYNTRA FASHION", 1, 900, 3200),
    ("NETFLIX SUBSCRIPTION", 1, 499, 649),
    ("SPOTIFY PREMIUM", 1, 119, 199),
    ("BOOKMYSHOW TICKETS", 1, 400, 1200),
    ("APOLLO PHARMACY", 2, 200, 1400),
    ("CULT FITNESS GYM", 1, 1500, 2200),
    ("AIRTEL BROADBAND", 1, 799, 1199),
    ("ELECTRICITY BILL PAYMENT", 1, 900, 2800),
    ("MOBILE RECHARGE", 1, 239, 799),
]

MONTHLY_RENT = ("HOUSE RENT PAYMENT", 18000.0)
MONTHLY_SALARY = ("MONTHLY SALARY CREDIT", 85000.0)

# The story the insights panel tells: dining and shopping blow out in the
# current month, so detect_spikes has a real spike to find.
#
# detect_spikes compares whole-month totals against the previous three
# months, and the current month is only partly elapsed — so the spike
# categories are given a FULL month's worth of transactions at this
# multiplier, compressed into the days so far. That's both what makes the
# alert fire and what the alert honestly describes: you're already well
# past your usual monthly spend and the month isn't over.
SPIKE_MULTIPLIER = 2.6
SPIKE_MERCHANTS = {"SWIGGY ORDER", "ZOMATO ORDER", "AMAZON MKTPLACE"}


def _month_starts(count: int) -> list[date]:
    """The first day of each of the last `count` months, oldest first."""

    today = date.today()
    starts = []

    year, month = today.year, today.month

    for _ in range(count):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return list(reversed(starts))


def _days_in_month(start: date) -> int:
    if start.month == 12:
        return 31
    return (date(start.year, start.month + 1, 1) - start).days


def _build_transactions(user_id: int, categories: dict[str, int]) -> list[Transaction]:
    # Fixed seed: the demo looks the same every time it's rebuilt, which
    # makes it usable as a reference when working on the charts.
    rng = random.Random(20260911)

    months = _month_starts(MONTHS_OF_HISTORY)
    latest_month = months[-1]

    today = date.today()
    transactions: list[Transaction] = []

    def add(
        when: date,
        description: str,
        amount: float,
        kind: TransactionType,
    ) -> None:
        # Never seed into the future; the current month is partial.
        if when > today:
            return

        category_name = categorize(description)

        transactions.append(
            Transaction(
                user_id=user_id,
                date=when,
                description=description,
                raw_description=description,
                amount=round(amount, 2),
                type=kind,
                category_id=categories.get(category_name),
                category_source=CategorySource.RULE_BASED,
                source=TransactionSource.CSV,
            )
        )

    for month_start in months:
        days_in_month = _days_in_month(month_start)
        is_current_month = month_start == latest_month

        # Only spread transactions across days that have actually
        # happened. Seeding into the future would put the trend chart
        # ahead of today.
        last_day = min(days_in_month, (today - month_start).days + 1)

        if last_day < 1:
            continue

        elapsed = last_day / days_in_month

        add(month_start, MONTHLY_SALARY[0], MONTHLY_SALARY[1], TransactionType.EARN)
        add(
            month_start + timedelta(days=2),
            MONTHLY_RENT[0],
            MONTHLY_RENT[1],
            TransactionType.SPEND,
        )

        for description, per_month, low, high in MERCHANTS:
            if is_current_month and description in SPIKE_MERCHANTS:
                # A full month's spend at the spike rate, already.
                count = int(round(per_month * SPIKE_MULTIPLIER))
            elif is_current_month:
                # Everything else is on its normal pace for the days so far.
                count = max(1, int(round(per_month * elapsed)))
            else:
                count = per_month

            # Vary the count a little so the trend line isn't flat.
            count = max(1, count + rng.randint(-1, 1))

            for _ in range(count):
                day_offset = rng.randint(0, last_day - 1)
                add(
                    month_start + timedelta(days=day_offset),
                    description,
                    rng.uniform(low, high),
                    TransactionType.SPEND,
                )

    transactions.sort(key=lambda t: t.date)
    return transactions


def seed_demo() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Categories must exist before transactions can reference them.
        # Normally the app's startup hook does this; a script run against
        # a fresh database can't rely on the app having booted.
        existing_categories = {c.name: c for c in db.query(Category).all()}
        for name, description in DEFAULT_CATEGORIES.items():
            if name not in existing_categories:
                db.add(Category(name=name, description=description, is_default=True))
        db.commit()

        categories = {c.name: c.id for c in db.query(Category).all()}

        user = db.query(User).filter(User.email == DEMO_EMAIL).first()

        if user is None:
            user = User(
                email=DEMO_EMAIL,
                full_name=DEMO_NAME,
                hashed_password=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created demo user {DEMO_EMAIL}")
        else:
            removed = (
                db.query(Transaction)
                .filter(Transaction.user_id == user.id)
                .delete(synchronize_session=False)
            )
            db.commit()
            print(f"Reset demo user {DEMO_EMAIL} ({removed} old transactions removed)")

        transactions = _build_transactions(user.id, categories)

        db.add_all(transactions)
        db.commit()

        spent = sum(t.amount for t in transactions if t.type == TransactionType.SPEND)
        earned = sum(t.amount for t in transactions if t.type == TransactionType.EARN)

        print(f"Seeded {len(transactions)} transactions across {MONTHS_OF_HISTORY} months")
        print(f"  earned {earned:,.2f} / spent {spent:,.2f}")
        print()
        print("Sign in with:")
        print(f"  email:    {DEMO_EMAIL}")
        print(f"  password: {DEMO_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
