"""
API Routes for campaign data, AI analysis, proposals, search terms,
period comparison, audit log, and CSV export.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from datetime import date, datetime, timedelta
from typing import Optional
import csv
import io

from app.models.schemas import (
    CampaignOverview,
    AdGroupMetrics,
    KeywordMetrics,
    AnalysisRequest,
    AnalysisResponse,
    DateRange,
    Proposal,
    ApplyProposalsRequest,
    ApplyProposalsResponse,
    ApplyProposalResult,
    ProposalAction,
    SearchTermReport,
    ComparisonOverview,
    MetricChange,
    AuditLogEntry,
    DeviceLocationReport,
    TrendReport,
    HourlyReport,
    AdPerformanceReport,
    NgramReport,
    LandingPageReport,
)
from app.services import google_ads_service, gemini_service, google_ads_mutations
from app.services.cache_service import log_action, get_audit_log, get_audit_log_count, cache_clear

router = APIRouter(prefix="/api", tags=["campaigns"])


@router.get("/token-usage")
def get_token_usage():
    """Get current session Gemini API token usage stats."""
    return gemini_service.get_token_usage()


@router.get("/campaigns", response_model=CampaignOverview)
def get_campaigns(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Fetch all search campaigns with metrics."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_campaigns(date_range=date_range)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}/ad-groups", response_model=list[AdGroupMetrics])
def get_ad_groups(
    campaign_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Fetch ad groups for a specific campaign."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_ad_groups(
            campaign_id=campaign_id, date_range=date_range
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords", response_model=list[KeywordMetrics])
def get_keywords(
    campaign_id: Optional[str] = Query(None),
    ad_group_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Fetch keyword metrics with quality scores."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_keywords(
            campaign_id=campaign_id,
            ad_group_id=ad_group_id,
            date_range=date_range,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SEARCH TERMS
# ============================================================

@router.get("/search-terms", response_model=SearchTermReport)
def get_search_terms(
    campaign_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(200, ge=10, le=1000),
):
    """Fetch search term report — actual queries that triggered ads."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_search_terms(
            campaign_id=campaign_id,
            date_range=date_range,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DEVICE / LOCATION SEGMENTATION
# ============================================================

@router.get("/segmentation", response_model=DeviceLocationReport)
def get_segmentation(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    campaign_id: Optional[str] = Query(None),
    location_limit: int = Query(50, ge=5, le=200),
):
    """Performance segmented by device type and geographic location."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        campaign_ids = [campaign_id] if campaign_id else None

        return google_ads_service.get_device_location_report(
            date_range=date_range,
            campaign_ids=campaign_ids,
            location_limit=location_limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DAILY TRENDS
# ============================================================

@router.get("/trends", response_model=TrendReport)
def get_trends(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    campaign_id: Optional[str] = Query(None),
):
    """Day-by-day performance trends."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)
        return google_ads_service.get_daily_trends(
            date_range=date_range, campaign_id=campaign_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# HOURLY PERFORMANCE
# ============================================================

@router.get("/hourly", response_model=HourlyReport)
def get_hourly(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    campaign_id: Optional[str] = Query(None),
):
    """Performance distribution by hour of day."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)
        return google_ads_service.get_hourly_performance(
            date_range=date_range, campaign_id=campaign_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AD COPY PERFORMANCE
# ============================================================

@router.get("/ads", response_model=AdPerformanceReport)
def get_ads(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    campaign_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=10, le=500),
):
    """Ad-level performance including headlines and descriptions."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)
        return google_ads_service.get_ad_performance(
            date_range=date_range, campaign_id=campaign_id, limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# N-GRAM ANALYSIS
# ============================================================

@router.get("/ngrams", response_model=NgramReport)
def get_ngrams(
    campaign_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    min_n: int = Query(1, ge=1, le=3),
    max_n: int = Query(3, ge=1, le=4),
    min_frequency: int = Query(2, ge=1, le=50),
    limit: int = Query(100, ge=10, le=500),
):
    """N-gram analysis of search terms — find common word patterns."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_ngram_analysis(
            campaign_id=campaign_id,
            date_range=date_range,
            min_n=min_n,
            max_n=max_n,
            min_frequency=min_frequency,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# LANDING PAGE PERFORMANCE
# ============================================================

@router.get("/landing-pages", response_model=LandingPageReport)
def get_landing_pages(
    campaign_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=5, le=200),
):
    """Landing page performance — see which URLs convert best."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        return google_ads_service.get_landing_page_performance(
            campaign_id=campaign_id,
            date_range=date_range,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PERIOD COMPARISON
# ============================================================

def _calc_change(current: float, previous: float, lower_is_better: bool = False) -> MetricChange:
    """Calculate change and direction between two metric values."""
    change = current - previous
    change_pct = ((change / previous) * 100) if previous != 0 else 0.0
    if lower_is_better:
        improved = change < 0
    else:
        improved = change > 0
    return MetricChange(
        current=round(current, 2),
        previous=round(previous, 2),
        change=round(change, 2),
        change_pct=round(change_pct, 2),
        improved=improved,
    )


@router.get("/comparison", response_model=ComparisonOverview)
def get_comparison(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Compare current period vs. same-length previous period."""
    try:
        if not start_date or not end_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

        days = (end_date - start_date).days
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days)

        current_range = DateRange(start_date=start_date, end_date=end_date)
        previous_range = DateRange(start_date=prev_start, end_date=prev_end)

        current = google_ads_service.get_campaigns(date_range=current_range)
        previous = google_ads_service.get_campaigns(date_range=previous_range)

        # Calculate per-metric comparison
        cur_conv_rate = (
            (current.total_conversions / current.total_clicks * 100)
            if current.total_clicks > 0 else 0.0
        )
        prev_conv_rate = (
            (previous.total_conversions / previous.total_clicks * 100)
            if previous.total_clicks > 0 else 0.0
        )
        cur_cpa = (
            current.total_cost / current.total_conversions
            if current.total_conversions > 0 else 0.0
        )
        prev_cpa = (
            previous.total_cost / previous.total_conversions
            if previous.total_conversions > 0 else 0.0
        )

        return ComparisonOverview(
            current_period=current_range,
            previous_period=previous_range,
            cost=_calc_change(current.total_cost, previous.total_cost, lower_is_better=True),
            clicks=_calc_change(current.total_clicks, previous.total_clicks),
            impressions=_calc_change(current.total_impressions, previous.total_impressions),
            conversions=_calc_change(current.total_conversions, previous.total_conversions),
            ctr=_calc_change(current.avg_ctr, previous.avg_ctr),
            avg_cpc=_calc_change(current.avg_cpc, previous.avg_cpc, lower_is_better=True),
            conversion_rate=_calc_change(cur_conv_rate, prev_conv_rate),
            cost_per_conversion=_calc_change(cur_cpa, prev_cpa, lower_is_better=True),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AUDIT LOG
# ============================================================

@router.get("/audit-log", response_model=list[AuditLogEntry])
def get_audit_log_entries(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get audit log entries (newest first)."""
    return get_audit_log(limit=limit, offset=offset)


@router.get("/audit-log/count")
def get_audit_log_total():
    """Get total audit log entry count."""
    return {"count": get_audit_log_count()}


# ============================================================
# EXPORT
# ============================================================

@router.get("/export/campaigns/csv")
def export_campaigns_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Export campaign data as CSV."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        overview = google_ads_service.get_campaigns(date_range=date_range)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Kampagne", "Status", "Impressionen", "Klicks", "CTR (%)",
            "Kosten (EUR)", "Ø CPC (EUR)", "Conversions", "Conv. Rate (%)",
            "Kosten/Conv. (EUR)",
        ])
        for c in overview.campaigns:
            writer.writerow([
                c.campaign_name, c.status, c.impressions, c.clicks,
                c.ctr, c.cost, c.avg_cpc, c.conversions,
                c.conversion_rate, c.cost_per_conversion,
            ])
        # Totals row
        writer.writerow([
            "GESAMT", "", overview.total_impressions, overview.total_clicks,
            overview.avg_ctr, overview.total_cost, overview.avg_cpc,
            overview.total_conversions, "", "",
        ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=kampagnen_{start_date}_{end_date}.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/search-terms/csv")
def export_search_terms_csv(
    campaign_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Export search terms report as CSV."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        report = google_ads_service.get_search_terms(
            campaign_id=campaign_id, date_range=date_range
        )

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Suchbegriff", "Keyword", "Match Type", "Kampagne", "Ad Group",
            "Impressionen", "Klicks", "CTR (%)", "Kosten (EUR)",
            "Ø CPC (EUR)", "Conversions", "Conv. Rate (%)", "Kosten/Conv. (EUR)",
        ])
        for st in report.search_terms:
            writer.writerow([
                st.search_term, st.keyword_text, st.match_type,
                st.campaign_name, st.ad_group_name, st.impressions,
                st.clicks, st.ctr, st.cost, st.avg_cpc,
                st.conversions, st.conversion_rate, st.cost_per_conversion,
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=suchanfragen_{start_date}_{end_date}.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/analysis/csv")
def export_analysis_csv():
    """Export latest analysis recommendations + proposals as CSV."""
    # Use last analysis from proposal store
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Typ", "Priorität", "Aktion/Kategorie", "Titel",
        "Beschreibung/Begründung", "Impact", "Status",
        "Kampagne", "Keyword", "Aktueller Wert", "Neuer Wert",
    ])
    for p in _proposal_store.values():
        writer.writerow([
            "Proposal", p.priority, p.action.value, p.title,
            p.reason, p.expected_impact, p.status.value if hasattr(p.status, 'value') else p.status,
            p.campaign_name or "", p.keyword_text or "",
            p.current_value or "", p.new_value or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analyse_vorschlaege.csv"},
    )


# ============================================================
# CACHE MANAGEMENT
# ============================================================

@router.post("/cache/clear")
def clear_cache():
    """Clear all cached data to force fresh API calls."""
    cache_clear()
    return {"status": "ok", "message": "Cache geleert"}


@router.get("/models")
def get_models():
    """Return available Gemini models."""
    return gemini_service.get_available_models()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_campaigns(request: AnalysisRequest):
    """Run AI analysis on campaign data."""
    try:
        # Fetch campaign data
        date_range = request.date_range
        overview = google_ads_service.get_campaigns(
            date_range=date_range,
            campaign_ids=request.campaign_ids,
        )

        if not overview.campaigns:
            raise HTTPException(
                status_code=404,
                detail="Keine Kampagnendaten für den gewählten Zeitraum gefunden.",
            )

        # Fetch keywords for deeper analysis (filtered to selected campaigns)
        campaign_id = request.campaign_ids[0] if request.campaign_ids and len(request.campaign_ids) == 1 else None
        keywords = google_ads_service.get_keywords(date_range=date_range, campaign_id=campaign_id)

        # Fetch ad groups for each campaign
        ad_groups = []
        for campaign in overview.campaigns:
            ag = google_ads_service.get_ad_groups(
                campaign_id=campaign.campaign_id, date_range=date_range
            )
            ad_groups.extend(ag)

        # Fetch trend and hourly data for deeper context
        trend_report = google_ads_service.get_daily_trends(date_range=date_range, campaign_id=campaign_id)
        hourly_report = google_ads_service.get_hourly_performance(date_range=date_range, campaign_id=campaign_id)
        ad_report = google_ads_service.get_ad_performance(date_range=date_range, campaign_id=campaign_id, limit=30)

        # Fetch negative keywords to show what's already been excluded
        negative_keywords = google_ads_service.get_negative_keywords(campaign_id=campaign_id)

        # Fetch account change history for context on recent optimizations
        change_history = google_ads_service.get_change_history(campaign_id=campaign_id, date_range=date_range)

        # Run AI analysis with enriched data
        analysis = gemini_service.analyze_campaigns(
            overview=overview,
            keywords=keywords,
            ad_groups=ad_groups,
            focus_areas=request.focus_areas,
            trend_data=trend_report,
            hourly_data=hourly_report,
            ad_data=ad_report,
            model_name=request.model,
            negative_keywords=negative_keywords,
            change_history=change_history,
        )

        # Store proposals for later execution
        if analysis.proposals:
            store_proposals(analysis.proposals)

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
def chat_about_campaigns(
    question: str = Query(..., description="Your question about the campaign data"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    model: Optional[str] = Query(None, description="Gemini model to use"),
    campaign_id: Optional[str] = Query(None, description="Filter to specific campaign"),
):
    """Ask a question about your campaign data."""
    try:
        date_range = None
        if start_date and end_date:
            date_range = DateRange(start_date=start_date, end_date=end_date)

        campaign_ids = [campaign_id] if campaign_id else None
        overview = google_ads_service.get_campaigns(date_range=date_range, campaign_ids=campaign_ids)
        keywords = google_ads_service.get_keywords(date_range=date_range, campaign_id=campaign_id)
        negative_keywords = google_ads_service.get_negative_keywords(campaign_id=campaign_id)
        change_history = google_ads_service.get_change_history(campaign_id=campaign_id, date_range=date_range)

        response = gemini_service.chat_about_campaigns(
            overview=overview,
            user_question=question,
            keywords=keywords,
            model_name=model,
            negative_keywords=negative_keywords,
            change_history=change_history,
        )

        return {"answer": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "AdsAgent API"}


# ============================================================
# PROPOSALS — Apply changes to Google Ads
# ============================================================

# In-memory store for proposals from latest analysis
_proposal_store: dict[str, Proposal] = {}


def store_proposals(proposals: list[Proposal]):
    """Store proposals from analysis for later execution."""
    global _proposal_store
    _proposal_store = {p.id: p for p in proposals}


@router.get("/proposals", response_model=list[Proposal])
def get_proposals():
    """Get all pending proposals from the latest analysis."""
    return list(_proposal_store.values())


@router.post("/proposals/apply", response_model=ApplyProposalsResponse)
def apply_proposals(request: ApplyProposalsRequest):
    """Apply selected proposals to Google Ads."""
    results = []
    total_applied = 0
    total_failed = 0

    for proposal_id in request.proposal_ids:
        proposal = _proposal_store.get(proposal_id)
        if not proposal:
            results.append(ApplyProposalResult(
                proposal_id=proposal_id,
                success=False,
                message=f"Proposal '{proposal_id}' nicht gefunden.",
                action=ProposalAction.PAUSE_KEYWORD,  # placeholder
            ))
            total_failed += 1
            continue

        result = google_ads_mutations.apply_proposal(proposal)
        results.append(result)

        # Log to audit trail
        log_action(
            action=proposal.action.value,
            success=result.success,
            proposal_id=proposal.id,
            campaign_id=proposal.campaign_id,
            campaign_name=proposal.campaign_name,
            ad_group_id=proposal.ad_group_id,
            keyword_id=proposal.keyword_id,
            keyword_text=proposal.keyword_text,
            old_value=proposal.current_value,
            new_value=proposal.new_value,
            error_message=result.message if not result.success else None,
        )

        if result.success:
            total_applied += 1
            proposal.status = "applied"
            proposal.applied_at = datetime.now()
            # Clear cache after mutation
            cache_clear()
        else:
            total_failed += 1
            proposal.status = "failed"
            proposal.error_message = result.message

    return ApplyProposalsResponse(
        results=results,
        total_applied=total_applied,
        total_failed=total_failed,
    )


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str):
    """Reject (dismiss) a proposal."""
    proposal = _proposal_store.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' nicht gefunden.")
    proposal.status = "rejected"
    return {"status": "rejected", "proposal_id": proposal_id}
