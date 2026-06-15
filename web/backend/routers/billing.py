from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import User
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/billing", tags=["billing"])

TIER_PRICES = {
    "pro": settings.stripe_price_pro,
    "agency": settings.stripe_price_agency,
}


@router.post("/checkout")
async def create_checkout(
    tier: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail="Invalid tier")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        customer_id = customer.id
        result = await db.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one()
        db_user.stripe_customer_id = customer_id
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": TIER_PRICES[tier], "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.frontend_url}/dashboard/billing?success=1",
        cancel_url=f"{settings.frontend_url}/dashboard/billing",
        metadata={"user_id": user.id, "tier": tier},
    )
    return {"url": session.url}


@router.get("/portal")
async def billing_portal(
    user: User = Depends(get_current_user),
):
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/dashboard/billing",
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook")

    if event["type"] == "checkout.session.completed":
        meta = event["data"]["object"].get("metadata", {})
        user_id = meta.get("user_id")
        tier = meta.get("tier")
        sub_id = event["data"]["object"].get("subscription")
        if user_id and tier:
            result = await db.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one_or_none()
            if db_user:
                db_user.subscription_tier = tier
                db_user.stripe_subscription_id = sub_id
                await db.commit()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.subscription_tier = "free"
            db_user.stripe_subscription_id = None
            await db.commit()

    return {"ok": True}
