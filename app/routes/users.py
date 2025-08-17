"""
User management API routes
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.database import get_db_session
from app.services.quota_service import quota_service

router = APIRouter(prefix="/users", tags=["users"])

class TierUpdateRequest(BaseModel):
    """Request model for tier updates"""
    tier: str = Field(..., pattern="^(free|pro)$", description="Subscription tier: 'free' or 'pro'")

class UserUsageResponse(BaseModel):
    """Response model for user usage information"""
    user_id: int
    tier: str
    daily_quota: Dict[str, Any]
    
class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    id: int
    email: str
    subscription_tier: str
    preferred_language: str
    daily_quota: Dict[str, Any]

@router.put("/tier")
async def update_user_tier(
    tier_request: TierUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user subscription tier (for testing purposes).
    
    This endpoint allows manual tier upgrades without payment processing.
    In production, this would be protected with admin permissions.
    """
    try:
        async with get_db_session() as db:
            # Get user from database
            result = await db.execute(select(User).where(User.id == current_user.id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            old_tier = user.subscription_tier
            user.subscription_tier = tier_request.tier
            
            # Reset daily quota when upgrading to pro tier
            if old_tier == "free" and tier_request.tier == "pro":
                await quota_service.reset_daily_quota(user.id)
            
            # Commit changes
            await db.commit()
            await db.refresh(user)
            
            # Get updated quota information
            quota_info = await quota_service.get_quota_info(user.id, user.subscription_tier)
            
            return {
                "success": True,
                "message": f"Tier updated from '{old_tier}' to '{tier_request.tier}'",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "subscription_tier": user.subscription_tier,
                    "preferred_language": user.preferred_language
                },
                "quota": quota_info
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tier: {str(e)}"
        )

@router.get("/usage")
async def get_user_usage(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user usage and quota information.
    """
    try:
        # Get quota information
        quota_info = await quota_service.get_quota_info(
            current_user.id, 
            current_user.subscription_tier or "free"
        )
        
        # Get available tier limits
        tier_limits = quota_service.get_tier_limits()
        
        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "tier": current_user.subscription_tier or "free",
            "quota": quota_info,
            "available_tiers": {
                tier: {"daily_limit": limit} 
                for tier, limit in tier_limits.items()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage information: {str(e)}"
        )

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive user profile with quota information.
    """
    try:
        # Get quota information
        quota_info = await quota_service.get_quota_info(
            current_user.id, 
            current_user.subscription_tier or "free"
        )
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "subscription_tier": current_user.subscription_tier or "free",
            "preferred_language": current_user.preferred_language,
            "quota": quota_info,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get profile: {str(e)}"
        )