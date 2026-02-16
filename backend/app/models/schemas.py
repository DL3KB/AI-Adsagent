from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, Literal
from enum import Enum


class CampaignMetrics(BaseModel):
    campaign_id: str
    campaign_name: str
    status: str
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    conversion_value: float = 0.0
    ctr: float = 0.0
    avg_cpc_micros: int = 0
    cost: float = 0.0
    avg_cpc: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0


class AdGroupMetrics(BaseModel):
    ad_group_id: str
    ad_group_name: str
    campaign_id: str
    campaign_name: str
    status: str
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc_micros: int = 0
    cost: float = 0.0
    avg_cpc: float = 0.0


class KeywordMetrics(BaseModel):
    keyword_id: str
    keyword_text: str
    match_type: str
    ad_group_id: str = ""
    ad_group_name: str
    campaign_id: str = ""
    campaign_name: str
    status: str
    quality_score: Optional[int] = None
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc_micros: int = 0
    cost: float = 0.0
    avg_cpc: float = 0.0


class SearchTermMetrics(BaseModel):
    """A single search term that triggered an ad."""
    search_term: str
    keyword_text: str
    match_type: str
    campaign_name: str
    campaign_id: str
    ad_group_name: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0


class SearchTermReport(BaseModel):
    """Full search term report."""
    search_terms: list[SearchTermMetrics]
    total_search_terms: int = 0
    total_cost: float = 0.0
    total_clicks: int = 0
    total_impressions: int = 0
    total_conversions: float = 0.0
    irrelevant_spend: float = 0.0  # Cost on terms with 0 conversions
    date_range: "DateRange"


class DateRange(BaseModel):
    start_date: date
    end_date: date


class CampaignOverview(BaseModel):
    campaigns: list[CampaignMetrics]
    total_cost: float
    total_clicks: int
    total_impressions: int
    total_conversions: float
    avg_ctr: float
    avg_cpc: float
    date_range: DateRange


class AnalysisRequest(BaseModel):
    campaign_ids: Optional[list[str]] = None
    date_range: Optional[DateRange] = None
    focus_areas: Optional[list[str]] = None  # z.B. ["ctr", "quality_score", "budget"]


class AnalysisResponse(BaseModel):
    summary: str
    recommendations: list[dict]
    insights: list[dict]
    raw_data_summary: dict
    proposals: list["Proposal"] = []


# ============================================================
# DEVICE / LOCATION SEGMENTATION
# ============================================================

class DeviceMetrics(BaseModel):
    """Performance metrics for a single device type."""
    device: str  # MOBILE, DESKTOP, TABLET, OTHER
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0
    impression_share: float = 0.0  # % of total impressions
    cost_share: float = 0.0  # % of total cost


class LocationMetrics(BaseModel):
    """Performance metrics for a single geographic location."""
    location_name: str
    location_type: str = ""  # Country, Region, City
    location_id: str = ""
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0


class DeviceLocationReport(BaseModel):
    """Combined device and location segmentation report."""
    devices: list[DeviceMetrics]
    locations: list[LocationMetrics]
    date_range: "DateRange"


# ============================================================
# PERIOD COMPARISON
# ============================================================

class MetricChange(BaseModel):
    """Change in a single metric between two periods."""
    current: float
    previous: float
    change: float  # absolute
    change_pct: float  # percentage
    improved: bool  # True if change is positive (depends on metric)


class ComparisonOverview(BaseModel):
    """KPI comparison between current and previous period."""
    current_period: DateRange
    previous_period: DateRange
    cost: MetricChange
    clicks: MetricChange
    impressions: MetricChange
    conversions: MetricChange
    ctr: MetricChange
    avg_cpc: MetricChange
    conversion_rate: MetricChange
    cost_per_conversion: MetricChange


# ============================================================
# AUDIT LOG
# ============================================================

class AuditLogEntry(BaseModel):
    """A logged change action."""
    id: int = 0
    timestamp: datetime
    action: str
    proposal_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    ad_group_id: Optional[str] = None
    keyword_id: Optional[str] = None
    keyword_text: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


# ============================================================
# PROPOSALS — Executable change proposals
# ============================================================

class ProposalAction(str, Enum):
    """All supported automated actions."""
    PAUSE_KEYWORD = "pause_keyword"
    ENABLE_KEYWORD = "enable_keyword"
    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_CAMPAIGN = "enable_campaign"
    PAUSE_AD_GROUP = "pause_ad_group"
    ENABLE_AD_GROUP = "enable_ad_group"
    ADD_NEGATIVE_KEYWORD = "add_negative_keyword"
    CHANGE_KEYWORD_BID = "change_keyword_bid"
    CHANGE_CAMPAIGN_BUDGET = "change_campaign_budget"
    CHANGE_KEYWORD_MATCH_TYPE = "change_keyword_match_type"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class Proposal(BaseModel):
    """A single executable change proposal."""
    id: str  # unique identifier
    action: ProposalAction
    priority: Literal["high", "medium", "low"] = "medium"
    title: str  # Short description
    reason: str  # Why this change is recommended
    expected_impact: str  # What should improve
    status: ProposalStatus = ProposalStatus.PENDING

    # Target identifiers
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    ad_group_id: Optional[str] = None
    ad_group_name: Optional[str] = None
    keyword_id: Optional[str] = None
    keyword_text: Optional[str] = None

    # Change parameters
    current_value: Optional[str] = None  # Current state/value
    new_value: Optional[str] = None  # Proposed new state/value

    # Execution result
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ProposalBatch(BaseModel):
    """A collection of proposals from one analysis."""
    proposals: list[Proposal]
    total_count: int = 0
    estimated_savings: float = 0.0  # EUR
    estimated_impact: str = ""


class ApplyProposalsRequest(BaseModel):
    """Request to apply selected proposals."""
    proposal_ids: list[str]


class ApplyProposalResult(BaseModel):
    """Result of applying a single proposal."""
    proposal_id: str
    success: bool
    message: str
    action: ProposalAction


class ApplyProposalsResponse(BaseModel):
    """Response after applying proposals."""
    results: list[ApplyProposalResult]
    total_applied: int = 0
    total_failed: int = 0


# Resolve forward references
AnalysisResponse.model_rebuild()
SearchTermReport.model_rebuild()
DeviceLocationReport.model_rebuild()
