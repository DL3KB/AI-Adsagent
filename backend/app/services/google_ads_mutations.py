"""
Google Ads Mutations Service
Executes write operations on the Google Ads API.

Supported actions:
- Pause / Enable campaigns, ad groups, keywords
- Change keyword CPC bids
- Change campaign budgets
- Add negative keywords to campaigns
- Change keyword match types
"""

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime
from typing import Optional
import logging

from app.config import get_settings
from app.models.schemas import (
    Proposal,
    ProposalAction,
    ProposalStatus,
    ApplyProposalResult,
)

logger = logging.getLogger(__name__)


def _get_client() -> GoogleAdsClient:
    """Create a Google Ads API client from settings."""
    settings = get_settings()
    credentials = {
        "developer_token": settings.google_ads_developer_token,
        "client_id": settings.google_ads_client_id,
        "client_secret": settings.google_ads_client_secret,
        "refresh_token": settings.google_ads_refresh_token,
        "use_proto_plus": True,
    }
    if settings.google_ads_login_customer_id:
        credentials["login_customer_id"] = settings.google_ads_login_customer_id
    return GoogleAdsClient.load_from_dict(credentials)


def _get_customer_id() -> str:
    return get_settings().google_ads_customer_id


# ============================================================
# CAMPAIGN MUTATIONS
# ============================================================

def _set_campaign_status(campaign_id: str, status: str) -> str:
    """Set campaign status to ENABLED or PAUSED."""
    client = _get_client()
    customer_id = _get_customer_id()
    campaign_service = client.get_service("CampaignService")

    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.update
    campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)

    if status == "PAUSED":
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
    elif status == "ENABLED":
        campaign.status = client.enums.CampaignStatusEnum.ENABLED
    else:
        raise ValueError(f"Unsupported campaign status: {status}")

    # Set the update mask
    client.copy_from(
        campaign_operation.update_mask,
        client.get_type("FieldMask")(paths=["status"]),
    )

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id,
        operations=[campaign_operation],
    )
    return response.results[0].resource_name


def _change_campaign_budget(campaign_id: str, new_budget_micros: int) -> str:
    """
    Change the daily budget for a campaign.
    Note: We need to find the budget resource linked to the campaign first.
    """
    client = _get_client()
    customer_id = _get_customer_id()
    ga_service = client.get_service("GoogleAdsService")

    # Look up the campaign's budget resource
    query = f"""
        SELECT campaign.campaign_budget
        FROM campaign
        WHERE campaign.id = {campaign_id}
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    budget_resource = None
    for row in response:
        budget_resource = row.campaign.campaign_budget
        break

    if not budget_resource:
        raise ValueError(f"Kein Budget für Kampagne {campaign_id} gefunden.")

    # Update the budget
    budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")
    budget = budget_operation.update
    budget.resource_name = budget_resource
    budget.amount_micros = new_budget_micros

    client.copy_from(
        budget_operation.update_mask,
        client.get_type("FieldMask")(paths=["amount_micros"]),
    )

    response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id,
        operations=[budget_operation],
    )
    return response.results[0].resource_name


# ============================================================
# AD GROUP MUTATIONS
# ============================================================

def _set_ad_group_status(ad_group_id: str, campaign_id: str, status: str) -> str:
    """Set ad group status to ENABLED or PAUSED."""
    client = _get_client()
    customer_id = _get_customer_id()
    ad_group_service = client.get_service("AdGroupService")

    operation = client.get_type("AdGroupOperation")
    ad_group = operation.update
    ad_group.resource_name = ad_group_service.ad_group_path(customer_id, ad_group_id)

    if status == "PAUSED":
        ad_group.status = client.enums.AdGroupStatusEnum.PAUSED
    elif status == "ENABLED":
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    else:
        raise ValueError(f"Unsupported ad group status: {status}")

    client.copy_from(
        operation.update_mask,
        client.get_type("FieldMask")(paths=["status"]),
    )

    response = ad_group_service.mutate_ad_groups(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


# ============================================================
# KEYWORD (AD GROUP CRITERION) MUTATIONS
# ============================================================

def _set_keyword_status(ad_group_id: str, keyword_id: str, status: str) -> str:
    """Set keyword status to ENABLED or PAUSED."""
    client = _get_client()
    customer_id = _get_customer_id()
    criterion_service = client.get_service("AdGroupCriterionService")

    operation = client.get_type("AdGroupCriterionOperation")
    criterion = operation.update
    criterion.resource_name = criterion_service.ad_group_criterion_path(
        customer_id, ad_group_id, keyword_id
    )

    if status == "PAUSED":
        criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
    elif status == "ENABLED":
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    else:
        raise ValueError(f"Unsupported keyword status: {status}")

    client.copy_from(
        operation.update_mask,
        client.get_type("FieldMask")(paths=["status"]),
    )

    response = criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _change_keyword_bid(ad_group_id: str, keyword_id: str, new_bid_micros: int) -> str:
    """Change keyword-level CPC bid."""
    client = _get_client()
    customer_id = _get_customer_id()
    criterion_service = client.get_service("AdGroupCriterionService")

    operation = client.get_type("AdGroupCriterionOperation")
    criterion = operation.update
    criterion.resource_name = criterion_service.ad_group_criterion_path(
        customer_id, ad_group_id, keyword_id
    )
    criterion.cpc_bid_micros = new_bid_micros

    client.copy_from(
        operation.update_mask,
        client.get_type("FieldMask")(paths=["cpc_bid_micros"]),
    )

    response = criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _add_negative_keyword(campaign_id: str, keyword_text: str, match_type: str = "EXACT") -> str:
    """Add a campaign-level negative keyword."""
    client = _get_client()
    customer_id = _get_customer_id()
    criterion_service = client.get_service("CampaignCriterionService")

    operation = client.get_type("CampaignCriterionOperation")
    criterion = operation.create
    criterion.campaign = client.get_service("CampaignService").campaign_path(
        customer_id, campaign_id
    )
    criterion.negative = True
    criterion.keyword.text = keyword_text

    match_type_map = {
        "EXACT": client.enums.KeywordMatchTypeEnum.EXACT,
        "PHRASE": client.enums.KeywordMatchTypeEnum.PHRASE,
        "BROAD": client.enums.KeywordMatchTypeEnum.BROAD,
    }
    criterion.keyword.match_type = match_type_map.get(
        match_type.upper(), client.enums.KeywordMatchTypeEnum.EXACT
    )

    response = criterion_service.mutate_campaign_criteria(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _change_keyword_match_type(
    ad_group_id: str,
    keyword_id: str,
    keyword_text: str,
    new_match_type: str,
) -> str:
    """
    Change a keyword's match type.
    Google Ads API doesn't allow modifying match type directly —
    we must remove the old keyword and create a new one.
    """
    client = _get_client()
    customer_id = _get_customer_id()
    criterion_service = client.get_service("AdGroupCriterionService")

    # Step 1: Remove old keyword
    remove_op = client.get_type("AdGroupCriterionOperation")
    remove_op.remove = criterion_service.ad_group_criterion_path(
        customer_id, ad_group_id, keyword_id
    )

    # Step 2: Create new keyword with new match type
    create_op = client.get_type("AdGroupCriterionOperation")
    new_criterion = create_op.create
    new_criterion.ad_group = client.get_service("AdGroupService").ad_group_path(
        customer_id, ad_group_id
    )
    new_criterion.keyword.text = keyword_text

    match_type_map = {
        "EXACT": client.enums.KeywordMatchTypeEnum.EXACT,
        "PHRASE": client.enums.KeywordMatchTypeEnum.PHRASE,
        "BROAD": client.enums.KeywordMatchTypeEnum.BROAD,
    }
    new_criterion.keyword.match_type = match_type_map.get(
        new_match_type.upper(), client.enums.KeywordMatchTypeEnum.EXACT
    )
    new_criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED

    response = criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id,
        operations=[remove_op, create_op],
    )
    return response.results[0].resource_name


# ============================================================
# PROPOSAL EXECUTOR — Main entry point
# ============================================================

def _currency_to_micros(amount: float) -> int:
    """Convert EUR (or USD) to micros."""
    return int(amount * 1_000_000)


def apply_proposal(proposal: Proposal) -> ApplyProposalResult:
    """
    Execute a single proposal against the Google Ads API.
    Returns the result (success/failure).
    """
    try:
        action = proposal.action

        if action == ProposalAction.PAUSE_CAMPAIGN:
            if not proposal.campaign_id:
                raise ValueError("campaign_id fehlt für PAUSE_CAMPAIGN")
            _set_campaign_status(proposal.campaign_id, "PAUSED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Kampagne '{proposal.campaign_name}' pausiert.",
                action=action,
            )

        elif action == ProposalAction.ENABLE_CAMPAIGN:
            if not proposal.campaign_id:
                raise ValueError("campaign_id fehlt für ENABLE_CAMPAIGN")
            _set_campaign_status(proposal.campaign_id, "ENABLED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Kampagne '{proposal.campaign_name}' aktiviert.",
                action=action,
            )

        elif action == ProposalAction.PAUSE_KEYWORD:
            if not proposal.ad_group_id or not proposal.keyword_id:
                raise ValueError("ad_group_id und keyword_id fehlen für PAUSE_KEYWORD")
            _set_keyword_status(proposal.ad_group_id, proposal.keyword_id, "PAUSED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Keyword '{proposal.keyword_text}' pausiert.",
                action=action,
            )

        elif action == ProposalAction.ENABLE_KEYWORD:
            if not proposal.ad_group_id or not proposal.keyword_id:
                raise ValueError("ad_group_id und keyword_id fehlen für ENABLE_KEYWORD")
            _set_keyword_status(proposal.ad_group_id, proposal.keyword_id, "ENABLED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Keyword '{proposal.keyword_text}' aktiviert.",
                action=action,
            )

        elif action == ProposalAction.PAUSE_AD_GROUP:
            if not proposal.ad_group_id or not proposal.campaign_id:
                raise ValueError("ad_group_id und campaign_id fehlen für PAUSE_AD_GROUP")
            _set_ad_group_status(proposal.ad_group_id, proposal.campaign_id, "PAUSED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Ad Group '{proposal.ad_group_name}' pausiert.",
                action=action,
            )

        elif action == ProposalAction.ENABLE_AD_GROUP:
            if not proposal.ad_group_id or not proposal.campaign_id:
                raise ValueError("ad_group_id und campaign_id fehlen für ENABLE_AD_GROUP")
            _set_ad_group_status(proposal.ad_group_id, proposal.campaign_id, "ENABLED")
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Ad Group '{proposal.ad_group_name}' aktiviert.",
                action=action,
            )

        elif action == ProposalAction.CHANGE_KEYWORD_BID:
            if not proposal.ad_group_id or not proposal.keyword_id or not proposal.new_value:
                raise ValueError("ad_group_id, keyword_id und new_value fehlen für CHANGE_KEYWORD_BID")
            new_bid_micros = _currency_to_micros(float(proposal.new_value))
            _change_keyword_bid(proposal.ad_group_id, proposal.keyword_id, new_bid_micros)
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Keyword '{proposal.keyword_text}' Gebot auf {proposal.new_value} EUR geändert.",
                action=action,
            )

        elif action == ProposalAction.CHANGE_CAMPAIGN_BUDGET:
            if not proposal.campaign_id or not proposal.new_value:
                raise ValueError("campaign_id und new_value fehlen für CHANGE_CAMPAIGN_BUDGET")
            new_budget_micros = _currency_to_micros(float(proposal.new_value))
            _change_campaign_budget(proposal.campaign_id, new_budget_micros)
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Kampagne '{proposal.campaign_name}' Tagesbudget auf {proposal.new_value} EUR geändert.",
                action=action,
            )

        elif action == ProposalAction.ADD_NEGATIVE_KEYWORD:
            if not proposal.campaign_id or not proposal.keyword_text:
                raise ValueError("campaign_id und keyword_text fehlen für ADD_NEGATIVE_KEYWORD")
            match_type = proposal.new_value or "EXACT"
            _add_negative_keyword(proposal.campaign_id, proposal.keyword_text, match_type)
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Negatives Keyword '{proposal.keyword_text}' [{match_type}] zur Kampagne hinzugefügt.",
                action=action,
            )

        elif action == ProposalAction.CHANGE_KEYWORD_MATCH_TYPE:
            if not proposal.ad_group_id or not proposal.keyword_id or not proposal.keyword_text or not proposal.new_value:
                raise ValueError("ad_group_id, keyword_id, keyword_text und new_value fehlen")
            _change_keyword_match_type(
                proposal.ad_group_id,
                proposal.keyword_id,
                proposal.keyword_text,
                proposal.new_value,
            )
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=True,
                message=f"Keyword '{proposal.keyword_text}' Match Type auf {proposal.new_value} geändert.",
                action=action,
            )

        else:
            return ApplyProposalResult(
                proposal_id=proposal.id,
                success=False,
                message=f"Unbekannte Aktion: {action}",
                action=action,
            )

    except GoogleAdsException as ex:
        error_msgs = [error.message for error in ex.failure.errors]
        error_detail = "; ".join(error_msgs)
        logger.error(f"Google Ads API Error for proposal {proposal.id}: {error_detail}")
        return ApplyProposalResult(
            proposal_id=proposal.id,
            success=False,
            message=f"Google Ads API Fehler: {error_detail}",
            action=proposal.action,
        )
    except Exception as e:
        logger.error(f"Error applying proposal {proposal.id}: {str(e)}")
        return ApplyProposalResult(
            proposal_id=proposal.id,
            success=False,
            message=f"Fehler: {str(e)}",
            action=proposal.action,
        )
