from app.modules.affiliate.models.affiliate_application import (
    AffiliateApplication,
)
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_referral_click import (
    AffiliateReferralClick,
)
from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)
from app.modules.affiliate.models.affiliate_commision_policy import (
    AffiliateCommissionPolicy,
)
from app.modules.affiliate.models.affiliate_withdrawal import (
    AffiliateWithdrawal,
)

# Affiliate Manual KYC models
from app.modules.affiliate.models.affiliate_kyc_submission import (
    AffiliateKYCSubmission,
)
from app.modules.affiliate.models.affiliate_kyc_document import (
    AffiliateKYCDocument,
)
from app.modules.affiliate.models.affiliate_kyc_review_history import (
    AffiliateKYCReviewHistory,
)

__all__ = [
    "AffiliateApplication",
    "Affiliate",
    "AffiliateAttribution",
    "AffiliateReferralClick",
    "AffiliateCommissionLedger",
    "AffiliateWithdrawal",
    "AffiliateCommissionPolicy",
    "AffiliateKYCSubmission",
    "AffiliateKYCDocument",
    "AffiliateKYCReviewHistory",
]