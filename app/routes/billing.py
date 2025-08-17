"""
Billing and subscription management API routes
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.database import get_db_session
from app.services.quota_service import quota_service

router = APIRouter(prefix="/billing", tags=["billing"])

class PlanResponse(BaseModel):
    """Pricing plan information"""
    id: str
    name: str
    price: float
    currency: str = "USD"
    billing_cycle: str  # "monthly", "yearly"
    features: Dict[str, Any]

class UpgradeRequest(BaseModel):
    """Request to upgrade subscription"""
    plan_id: str = Field(..., description="Target plan ID")
    payment_method: str = Field("stripe", description="Payment method")
    billing_cycle: str = Field("monthly", description="Billing cycle")

class PaymentIntentResponse(BaseModel):
    """Payment intent for frontend processing"""
    payment_intent_id: str
    client_secret: str
    amount: float
    currency: str

# Pricing plans configuration
PRICING_PLANS = {
    "free": {
        "id": "free",
        "name": "Free Plan",
        "price": 0.0,
        "billing_cycle": "none",
        "features": {
            "daily_messages": 20,
            "character_access": "basic",
            "priority_support": False,
            "api_access": False
        }
    },
    "pro": {
        "id": "pro", 
        "name": "Pro Plan",
        "price": 9.99,
        "billing_cycle": "monthly",
        "features": {
            "daily_messages": 500,
            "character_access": "premium",
            "priority_support": True,
            "api_access": True
        }
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise Plan", 
        "price": 29.99,
        "billing_cycle": "monthly",
        "features": {
            "daily_messages": -1,  # unlimited
            "character_access": "all",
            "priority_support": True,
            "api_access": True,
            "custom_characters": True
        }
    }
}

@router.get("/plans")
async def get_pricing_plans() -> Dict[str, Any]:
    """
    Get all available pricing plans.
    
    Returns:
        List of available subscription plans with pricing and features
    """
    return {
        "plans": list(PRICING_PLANS.values()),
        "currency": "USD",
        "payment_methods": ["stripe", "paypal"],
        "billing_cycles": ["monthly", "yearly"]
    }

@router.get("/current-plan")
async def get_current_plan(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's current subscription plan and usage.
    """
    try:
        user_tier = current_user.subscription_tier or "free"
        plan_info = PRICING_PLANS.get(user_tier, PRICING_PLANS["free"])
        
        # Get quota information
        quota_info = await quota_service.get_quota_info(current_user.id, user_tier)
        
        return {
            "current_plan": plan_info,
            "usage": quota_info,
            "billing_status": "active" if user_tier != "free" else "none",
            "next_billing_date": None  # Would come from payment processor
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current plan: {str(e)}"
        )

@router.post("/create-payment-intent")
async def create_payment_intent(
    upgrade_request: UpgradeRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create payment intent for plan upgrade.
    
    In production, this would integrate with Stripe/PayPal.
    For now, returns mock payment intent for testing.
    """
    try:
        target_plan = PRICING_PLANS.get(upgrade_request.plan_id)
        if not target_plan:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan ID: {upgrade_request.plan_id}"
            )
        
        current_tier = current_user.subscription_tier or "free"
        if current_tier == upgrade_request.plan_id:
            raise HTTPException(
                status_code=400,
                detail=f"User already on {upgrade_request.plan_id} plan"
            )
        
        # Calculate amount (in production, handle prorations, taxes, etc.)
        amount = target_plan["price"]
        
        # Mock payment intent (in production, create real Stripe payment intent)
        mock_payment_intent = {
            "payment_intent_id": f"pi_mock_{current_user.id}_{upgrade_request.plan_id}",
            "client_secret": f"pi_mock_{current_user.id}_secret",
            "amount": amount,
            "currency": "USD",
            "status": "requires_payment_method",
            "metadata": {
                "user_id": current_user.id,
                "plan_id": upgrade_request.plan_id,
                "current_tier": current_tier
            }
        }
        
        return {
            "payment_intent": mock_payment_intent,
            "plan": target_plan,
            "total_amount": amount,
            "payment_methods": ["card", "paypal"],
            "test_mode": True  # Remove in production
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create payment intent: {str(e)}"
        )

@router.post("/confirm-upgrade")
async def confirm_upgrade(
    payment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Confirm successful payment and upgrade user tier.
    
    In production, this would be called by webhook from payment processor.
    For testing, allows manual confirmation.
    """
    try:
        # Extract payment info
        payment_intent_id = payment_data.get("payment_intent_id")
        plan_id = payment_data.get("plan_id")
        
        if not payment_intent_id or not plan_id:
            raise HTTPException(
                status_code=400,
                detail="Missing payment_intent_id or plan_id"
            )
        
        # Validate plan
        target_plan = PRICING_PLANS.get(plan_id)
        if not target_plan:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan ID: {plan_id}"
            )
        
        # In production: verify payment with Stripe/PayPal here
        # For testing: assume payment successful
        
        # Update user tier in database
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            old_tier = user.subscription_tier
            user.subscription_tier = plan_id
            
            # Reset quota on upgrade
            if plan_id == "pro" and old_tier == "free":
                await quota_service.reset_daily_quota(user.id)
            
            await db.commit()
            await db.refresh(user)
        
        # Get updated quota info
        quota_info = await quota_service.get_quota_info(user.id, plan_id)
        
        return {
            "success": True,
            "message": f"Successfully upgraded to {target_plan['name']}",
            "user": {
                "id": user.id,
                "email": user.email,
                "subscription_tier": user.subscription_tier
            },
            "plan": target_plan,
            "quota": quota_info,
            "payment": {
                "payment_intent_id": payment_intent_id,
                "amount": target_plan["price"],
                "status": "succeeded"
            }
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm upgrade: {str(e)}"
        )

@router.get("/usage-history")
async def get_usage_history(
    days: int = 30,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's usage history for billing purposes.
    
    In production, this would query usage analytics.
    """
    try:
        # Mock usage history (in production, query from analytics DB)
        current_quota = await quota_service.get_quota_info(
            current_user.id, 
            current_user.subscription_tier or "free"
        )
        
        # Mock historical data
        mock_history = [
            {
                "date": "2024-01-15",
                "messages_sent": current_quota["used"],
                "tier": current_quota["tier"]
            }
        ]
        
        return {
            "usage_history": mock_history,
            "current_period": current_quota,
            "billing_period": "monthly",
            "days_requested": days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage history: {str(e)}"
        )

@router.post("/cancel-subscription") 
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel user's subscription (downgrade to free).
    
    In production, this would cancel via payment processor.
    """
    try:
        if current_user.subscription_tier == "free":
            raise HTTPException(
                status_code=400,
                detail="User is already on free plan"
            )
        
        # Update user to free tier
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            old_tier = user.subscription_tier
            user.subscription_tier = "free"
            
            await db.commit()
            await db.refresh(user)
        
        # Get updated quota (free tier limits)
        quota_info = await quota_service.get_quota_info(user.id, "free")
        
        return {
            "success": True,
            "message": f"Subscription cancelled. Downgraded from {old_tier} to free.",
            "user": {
                "id": user.id,
                "email": user.email,
                "subscription_tier": user.subscription_tier
            },
            "new_plan": PRICING_PLANS["free"],
            "quota": quota_info,
            "effective_date": "immediate"  # In production, might be end of billing cycle
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel subscription: {str(e)}"
        )