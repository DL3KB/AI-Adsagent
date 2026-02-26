"""
Google Ads API Service
Fetches campaign, ad group, and keyword data from Google Ads.
Includes SQLite caching (15 min TTL) to reduce API calls.
"""

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import date, timedelta
from typing import Optional
import json
import logging

from app.config import get_settings
from app.models.schemas import (
    CampaignMetrics,
    AdGroupMetrics,
    KeywordMetrics,
    CampaignOverview,
    DateRange,
    SearchTermMetrics,
    SearchTermReport,
    DeviceMetrics,
    LocationMetrics,
    DeviceLocationReport,
    DailyMetrics,
    TrendReport,
    HourlyMetrics,
    HourlyReport,
    AdMetrics,
    AdPerformanceReport,
    NgramMetrics,
    NgramReport,
    LandingPageMetrics,
    LandingPageReport,
)
from collections import defaultdict
from app.services.cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


def _micros_to_currency(micros: int) -> float:
    """Convert micros to currency (e.g., EUR/USD)."""
    return micros / 1_000_000


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
    # MCC: login_customer_id ist Pflicht bei Verwaltungskonten
    if settings.google_ads_login_customer_id:
        credentials["login_customer_id"] = settings.google_ads_login_customer_id
    return GoogleAdsClient.load_from_dict(credentials)


def _default_date_range() -> DateRange:
    """Return the last 30 days as default date range."""
    end = date.today()
    start = end - timedelta(days=30)
    return DateRange(start_date=start, end_date=end)


def get_campaigns(
    date_range: Optional[DateRange] = None,
    campaign_ids: Optional[list[str]] = None,
) -> CampaignOverview:
    """Fetch campaign-level metrics from Google Ads (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    # Check cache
    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        ids=sorted(campaign_ids) if campaign_ids else None,
    )
    cached = cache_get("campaigns", **cache_params)
    if cached:
        return CampaignOverview.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.ctr,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.advertising_channel_type = 'SEARCH'
    """

    if campaign_ids:
        ids_str = ", ".join(campaign_ids)
        query += f" AND campaign.id IN ({ids_str})"

    query += " ORDER BY metrics.cost_micros DESC"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        campaigns = []
        total_cost_micros = 0
        total_clicks = 0
        total_impressions = 0
        total_conversions = 0.0

        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)
            conv_rate = (
                (row.metrics.conversions / row.metrics.clicks * 100)
                if row.metrics.clicks > 0
                else 0.0
            )
            cost_per_conv = (
                cost / row.metrics.conversions
                if row.metrics.conversions > 0
                else 0.0
            )

            campaign = CampaignMetrics(
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                status=row.campaign.status.name,
                impressions=row.metrics.impressions,
                clicks=row.metrics.clicks,
                cost_micros=row.metrics.cost_micros,
                conversions=row.metrics.conversions,
                conversion_value=row.metrics.conversions_value,
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc_micros=row.metrics.average_cpc,
                cost=round(cost, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            )
            campaigns.append(campaign)

            total_cost_micros += row.metrics.cost_micros
            total_clicks += row.metrics.clicks
            total_impressions += row.metrics.impressions
            total_conversions += row.metrics.conversions

        total_cost = _micros_to_currency(total_cost_micros)
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        avg_cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0

        result = CampaignOverview(
            campaigns=campaigns,
            total_cost=round(total_cost, 2),
            total_clicks=total_clicks,
            total_impressions=total_impressions,
            total_conversions=round(total_conversions, 2),
            avg_ctr=round(avg_ctr, 2),
            avg_cpc=round(avg_cpc, 2),
            date_range=date_range,
        )

        # Store in cache
        cache_set("campaigns", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = []
        for error in ex.failure.errors:
            error_messages.append(error.message)
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


def get_ad_groups(
    campaign_id: str,
    date_range: Optional[DateRange] = None,
) -> list[AdGroupMetrics]:
    """Fetch ad group metrics for a specific campaign (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    # Check cache
    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
    )
    cached = cache_get("ad_groups", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [AdGroupMetrics.model_validate(a) for a in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.id = {campaign_id}
        ORDER BY metrics.cost_micros DESC
    """

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        ad_groups = []
        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)

            ad_group = AdGroupMetrics(
                ad_group_id=str(row.ad_group.id),
                ad_group_name=row.ad_group.name,
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                status=row.ad_group.status.name,
                impressions=row.metrics.impressions,
                clicks=row.metrics.clicks,
                cost_micros=row.metrics.cost_micros,
                conversions=row.metrics.conversions,
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc_micros=row.metrics.average_cpc,
                cost=round(cost, 2),
                avg_cpc=round(avg_cpc, 2),
            )
            ad_groups.append(ad_group)

        # Store in cache
        cache_set("ad_groups", json.dumps([a.model_dump() for a in ad_groups], default=str), **cache_params)
        return ad_groups

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


def get_keywords(
    campaign_id: Optional[str] = None,
    ad_group_id: Optional[str] = None,
    date_range: Optional[DateRange] = None,
) -> list[KeywordMetrics]:
    """Fetch keyword-level metrics with quality scores (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    # Check cache
    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
        adgroup=ad_group_id,
    )
    cached = cache_get("keywords", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [KeywordMetrics.model_validate(k) for k in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.post_click_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.status,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"
    if ad_group_id:
        query += f" AND ad_group.id = {ad_group_id}"

    query += " ORDER BY metrics.impressions DESC LIMIT 100"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        keywords = []
        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)
            qs = row.ad_group_criterion.quality_info.quality_score
            quality_score = qs if qs > 0 else None

            # Quality Score sub-components (enum → readable string)
            qi = row.ad_group_criterion.quality_info
            expected_ctr = qi.search_predicted_ctr.name if qi.search_predicted_ctr and qi.search_predicted_ctr.name != "UNSPECIFIED" else None
            ad_relevance = qi.creative_quality_score.name if qi.creative_quality_score and qi.creative_quality_score.name != "UNSPECIFIED" else None
            landing_page_exp = qi.post_click_quality_score.name if qi.post_click_quality_score and qi.post_click_quality_score.name != "UNSPECIFIED" else None

            keyword = KeywordMetrics(
                keyword_id=str(row.ad_group_criterion.criterion_id),
                keyword_text=row.ad_group_criterion.keyword.text,
                match_type=row.ad_group_criterion.keyword.match_type.name,
                ad_group_id=str(row.ad_group.id),
                ad_group_name=row.ad_group.name,
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                status=row.ad_group_criterion.status.name,
                quality_score=quality_score,
                expected_ctr=expected_ctr,
                ad_relevance=ad_relevance,
                landing_page_experience=landing_page_exp,
                impressions=row.metrics.impressions,
                clicks=row.metrics.clicks,
                cost_micros=row.metrics.cost_micros,
                conversions=row.metrics.conversions,
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc_micros=row.metrics.average_cpc,
                cost=round(cost, 2),
                avg_cpc=round(avg_cpc, 2),
            )
            keywords.append(keyword)

        # Store in cache
        cache_set("keywords", json.dumps([k.model_dump() for k in keywords], default=str), **cache_params)
        return keywords

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


def get_negative_keywords(
    campaign_id: Optional[str] = None,
) -> list:
    """Fetch negative keywords at campaign level (cached 15 min)."""
    from app.models.schemas import NegativeKeyword

    cache_params = dict(campaign=campaign_id)
    cached = cache_get("negative_keywords", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [NegativeKeyword.model_validate(k) for k in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    negatives: list[NegativeKeyword] = []

    # ---- Campaign-level negative keywords ----
    query = """
        SELECT
            campaign_criterion.keyword.text,
            campaign_criterion.keyword.match_type,
            campaign_criterion.negative,
            campaign.id,
            campaign.name
        FROM campaign_criterion
        WHERE campaign_criterion.type = 'KEYWORD'
          AND campaign_criterion.negative = TRUE
    """
    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )
        for row in response:
            negatives.append(NegativeKeyword(
                keyword_text=row.campaign_criterion.keyword.text,
                match_type=row.campaign_criterion.keyword.match_type.name,
                level="CAMPAIGN",
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
            ))
    except GoogleAdsException as ex:
        logger.warning(f"Failed to fetch campaign negatives: {ex}")

    # ---- Ad group-level negative keywords ----
    ag_query = """
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.negative,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name
        FROM ad_group_criterion
        WHERE ad_group_criterion.type = 'KEYWORD'
          AND ad_group_criterion.negative = TRUE
    """
    if campaign_id:
        ag_query += f" AND campaign.id = {campaign_id}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=ag_query
        )
        for row in response:
            negatives.append(NegativeKeyword(
                keyword_text=row.ad_group_criterion.keyword.text,
                match_type=row.ad_group_criterion.keyword.match_type.name,
                level="AD_GROUP",
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                ad_group_id=str(row.ad_group.id),
                ad_group_name=row.ad_group.name,
            ))
    except GoogleAdsException as ex:
        logger.warning(f"Failed to fetch ad group negatives: {ex}")

    cache_set("negative_keywords", json.dumps([n.model_dump() for n in negatives], default=str), **cache_params)
    return negatives


def get_change_history(
    campaign_id: Optional[str] = None,
    date_range: Optional[DateRange] = None,
    limit: int = 50,
) -> list:
    """Fetch account change history (change_event) for the given period (cached 15 min)."""
    from app.models.schemas import ChangeEvent

    if date_range is None:
        date_range = _default_date_range()

    # change_event only supports up to 30 days back
    earliest = date.today() - timedelta(days=29)
    start = max(date_range.start_date, earliest)
    end = min(date_range.end_date, date.today())

    cache_params = dict(start=str(start), end=str(end), campaign=campaign_id)
    cached = cache_get("change_history", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [ChangeEvent.model_validate(e) for e in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            change_event.change_date_time,
            change_event.change_resource_type,
            change_event.changed_fields,
            change_event.resource_change_operation,
            change_event.user_email,
            campaign.name,
            campaign.id
        FROM change_event
        WHERE change_event.change_date_time >= '{start_str}'
          AND change_event.change_date_time <= '{end_str}'
    """
    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"
    query += f" ORDER BY change_event.change_date_time DESC LIMIT {limit}"

    events: list[ChangeEvent] = []
    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )
        for row in response:
            ce = row.change_event
            fields = list(ce.changed_fields.paths) if ce.changed_fields else []
            events.append(ChangeEvent(
                change_date_time=ce.change_date_time,
                resource_type=ce.change_resource_type.name,
                operation=ce.resource_change_operation.name,
                changed_fields=fields,
                user_email=ce.user_email,
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
            ))
    except GoogleAdsException as ex:
        logger.warning(f"Failed to fetch change history: {ex}")
    except Exception as ex:
        logger.warning(f"Change history error: {ex}")

    cache_set("change_history", json.dumps([e.model_dump() for e in events], default=str), **cache_params)
    return events


def get_search_terms(
    campaign_id: Optional[str] = None,
    date_range: Optional[DateRange] = None,
    limit: int = 200,
) -> SearchTermReport:
    """Fetch search term report showing actual queries that triggered ads (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    # Check cache
    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
        limit=limit,
    )
    cached = cache_get("search_terms", **cache_params)
    if cached:
        return SearchTermReport.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            search_term_view.search_term,
            segments.keyword.info.text,
            segments.keyword.info.match_type,
            campaign.id,
            campaign.name,
            ad_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM search_term_view
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    query += f" ORDER BY metrics.cost_micros DESC LIMIT {limit}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        search_terms = []
        total_cost = 0.0
        total_clicks = 0
        total_impressions = 0
        total_conversions = 0.0
        irrelevant_spend = 0.0

        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)
            clicks = row.metrics.clicks
            conversions = row.metrics.conversions
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = (cost / conversions) if conversions > 0 else 0.0

            st = SearchTermMetrics(
                search_term=row.search_term_view.search_term,
                keyword_text=row.segments.keyword.info.text,
                match_type=row.segments.keyword.info.match_type.name,
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                ad_group_name=row.ad_group.name,
                impressions=row.metrics.impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=conversions,
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            )
            search_terms.append(st)

            total_cost += cost
            total_clicks += clicks
            total_impressions += row.metrics.impressions
            total_conversions += conversions
            if clicks > 0 and conversions == 0:
                irrelevant_spend += cost

        result = SearchTermReport(
            search_terms=search_terms,
            total_search_terms=len(search_terms),
            total_cost=round(total_cost, 2),
            total_clicks=total_clicks,
            total_impressions=total_impressions,
            total_conversions=round(total_conversions, 2),
            irrelevant_spend=round(irrelevant_spend, 2),
            date_range=date_range,
        )

        # Store in cache
        cache_set("search_terms", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


# ============================================================
# DEVICE SEGMENTATION
# ============================================================

def get_device_performance(
    date_range: Optional[DateRange] = None,
    campaign_ids: Optional[list[str]] = None,
) -> list[DeviceMetrics]:
    """Fetch performance metrics segmented by device type (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        ids=sorted(campaign_ids) if campaign_ids else None,
    )
    cached = cache_get("device_perf", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [DeviceMetrics.model_validate(d) for d in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            segments.device,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.advertising_channel_type = 'SEARCH'
    """

    if campaign_ids:
        ids_str = ", ".join(campaign_ids)
        query += f" AND campaign.id IN ({ids_str})"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        # Aggregate by device
        device_data: dict[str, dict] = {}
        total_impressions = 0
        total_cost = 0.0

        for row in response:
            device_name = row.segments.device.name  # MOBILE, DESKTOP, TABLET, OTHER
            if device_name not in device_data:
                device_data[device_name] = {
                    "impressions": 0, "clicks": 0,
                    "cost_micros": 0, "conversions": 0.0,
                }
            d = device_data[device_name]
            d["impressions"] += row.metrics.impressions
            d["clicks"] += row.metrics.clicks
            d["cost_micros"] += row.metrics.cost_micros
            d["conversions"] += row.metrics.conversions
            total_impressions += row.metrics.impressions
            total_cost += row.metrics.cost_micros

        devices = []
        for device_name, d in sorted(device_data.items(), key=lambda x: x[1]["cost_micros"], reverse=True):
            cost = _micros_to_currency(d["cost_micros"])
            clicks = d["clicks"]
            impressions = d["impressions"]
            conversions = d["conversions"]
            avg_cpc = cost / clicks if clicks > 0 else 0.0
            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = cost / conversions if conversions > 0 else 0.0

            devices.append(DeviceMetrics(
                device=device_name,
                impressions=impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(ctr, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
                impression_share=round((impressions / total_impressions * 100) if total_impressions > 0 else 0, 1),
                cost_share=round((_micros_to_currency(d["cost_micros"]) / _micros_to_currency(total_cost) * 100) if total_cost > 0 else 0, 1),
            ))

        cache_set("device_perf", json.dumps([d.model_dump() for d in devices]), **cache_params)
        return devices

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


# ============================================================
# LOCATION / GEO SEGMENTATION
# ============================================================

def get_location_performance(
    date_range: Optional[DateRange] = None,
    campaign_ids: Optional[list[str]] = None,
    limit: int = 50,
) -> list[LocationMetrics]:
    """Fetch performance metrics segmented by geographic location (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        ids=sorted(campaign_ids) if campaign_ids else None,
        limit=limit,
    )
    cached = cache_get("location_perf", **cache_params)
    if cached:
        raw = json.loads(cached)
        return [LocationMetrics.model_validate(loc) for loc in raw]

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            geographic_view.country_criterion_id,
            geographic_view.location_type,
            campaign.id,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM geographic_view
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
    """

    if campaign_ids:
        ids_str = ", ".join(campaign_ids)
        query += f" AND campaign.id IN ({ids_str})"

    query += " ORDER BY metrics.cost_micros DESC"
    query += f" LIMIT {limit}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        # Collect rows and geo IDs for name lookup
        geo_ids: set[int] = set()
        raw_rows = []
        for row in response:
            raw_rows.append(row)
            geo_id = row.geographic_view.country_criterion_id
            if geo_id:
                geo_ids.add(geo_id)

        # Fetch geo target names
        geo_names: dict[int, tuple[str, str]] = {}  # criterion_id -> (name, type)
        if geo_ids:
            ids_list = ", ".join(str(gid) for gid in geo_ids)
            try:
                geo_query = f"""
                    SELECT
                        geo_target_constant.name,
                        geo_target_constant.target_type,
                        geo_target_constant.id
                    FROM geo_target_constant
                    WHERE geo_target_constant.id IN ({ids_list})
                """
                geo_resp = ga_service.search(
                    customer_id=settings.google_ads_customer_id, query=geo_query
                )
                for gr in geo_resp:
                    geo_names[gr.geo_target_constant.id] = (
                        gr.geo_target_constant.name,
                        gr.geo_target_constant.target_type,
                    )
            except Exception:
                pass

        locations = []
        for row in raw_rows:
            geo_id = row.geographic_view.country_criterion_id
            name, loc_type = geo_names.get(geo_id, (str(geo_id), "Unknown"))

            cost = _micros_to_currency(row.metrics.cost_micros)
            clicks = row.metrics.clicks
            impressions = row.metrics.impressions
            conversions = row.metrics.conversions
            avg_cpc = cost / clicks if clicks > 0 else 0.0
            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = cost / conversions if conversions > 0 else 0.0

            locations.append(LocationMetrics(
                location_name=name,
                location_type=loc_type,
                location_id=str(geo_id),
                impressions=impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(ctr, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            ))

        cache_set("location_perf", json.dumps([loc.model_dump() for loc in locations]), **cache_params)
        return locations

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


def get_device_location_report(
    date_range: Optional[DateRange] = None,
    campaign_ids: Optional[list[str]] = None,
    location_limit: int = 50,
) -> DeviceLocationReport:
    """Combined device + location report."""
    if date_range is None:
        date_range = _default_date_range()
    devices = get_device_performance(date_range, campaign_ids)
    locations = get_location_performance(date_range, campaign_ids, location_limit)
    return DeviceLocationReport(
        devices=devices,
        locations=locations,
        date_range=date_range,
    )


# ============================================================
# DAILY TRENDS
# ============================================================

def get_daily_trends(
    date_range: Optional[DateRange] = None,
    campaign_id: Optional[str] = None,
) -> TrendReport:
    """Fetch day-by-day performance metrics (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
    )
    cached = cache_get("daily_trends", **cache_params)
    if cached:
        return TrendReport.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            segments.date,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.advertising_channel_type = 'SEARCH'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    query += " ORDER BY segments.date ASC"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        # Aggregate by date (multiple campaigns per day)
        day_data: dict[str, dict] = {}
        for row in response:
            d = row.segments.date  # YYYY-MM-DD string
            if d not in day_data:
                day_data[d] = {"impressions": 0, "clicks": 0, "cost_micros": 0, "conversions": 0.0}
            day_data[d]["impressions"] += row.metrics.impressions
            day_data[d]["clicks"] += row.metrics.clicks
            day_data[d]["cost_micros"] += row.metrics.cost_micros
            day_data[d]["conversions"] += row.metrics.conversions

        daily = []
        for d in sorted(day_data.keys()):
            dd = day_data[d]
            cost = _micros_to_currency(dd["cost_micros"])
            clicks = dd["clicks"]
            impressions = dd["impressions"]
            conversions = dd["conversions"]
            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
            avg_cpc = (cost / clicks) if clicks > 0 else 0.0
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = (cost / conversions) if conversions > 0 else 0.0

            daily.append(DailyMetrics(
                date=date.fromisoformat(d),
                impressions=impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(ctr, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            ))

        result = TrendReport(daily=daily, date_range=date_range)
        cache_set("daily_trends", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


# ============================================================
# HOUR-OF-DAY PERFORMANCE
# ============================================================

def get_hourly_performance(
    date_range: Optional[DateRange] = None,
    campaign_id: Optional[str] = None,
) -> HourlyReport:
    """Fetch performance by hour of day (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
    )
    cached = cache_get("hourly_perf", **cache_params)
    if cached:
        return HourlyReport.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            segments.hour,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.advertising_channel_type = 'SEARCH'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        hour_data: dict[int, dict] = {}
        for row in response:
            h = row.segments.hour
            if h not in hour_data:
                hour_data[h] = {"impressions": 0, "clicks": 0, "cost_micros": 0, "conversions": 0.0}
            hour_data[h]["impressions"] += row.metrics.impressions
            hour_data[h]["clicks"] += row.metrics.clicks
            hour_data[h]["cost_micros"] += row.metrics.cost_micros
            hour_data[h]["conversions"] += row.metrics.conversions

        hours = []
        for h in range(24):
            hd = hour_data.get(h, {"impressions": 0, "clicks": 0, "cost_micros": 0, "conversions": 0.0})
            cost = _micros_to_currency(hd["cost_micros"])
            clicks = hd["clicks"]
            impressions = hd["impressions"]
            conversions = hd["conversions"]
            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
            avg_cpc = (cost / clicks) if clicks > 0 else 0.0
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0

            hours.append(HourlyMetrics(
                hour=h,
                impressions=impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(ctr, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
            ))

        result = HourlyReport(hours=hours, date_range=date_range)
        cache_set("hourly_perf", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


# ============================================================
# AD COPY PERFORMANCE
# ============================================================

def get_ad_performance(
    date_range: Optional[DateRange] = None,
    campaign_id: Optional[str] = None,
    limit: int = 100,
) -> AdPerformanceReport:
    """Fetch ad-level performance metrics including headlines & descriptions (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
        limit=limit,
    )
    cached = cache_get("ad_perf", **cache_params)
    if cached:
        return AdPerformanceReport.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad.type,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            ad_group_ad.ad.final_urls,
            ad_group_ad.status,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
            AND campaign.advertising_channel_type = 'SEARCH'
            AND ad_group_ad.status != 'REMOVED'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    query += f" ORDER BY metrics.cost_micros DESC LIMIT {limit}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        ads = []
        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)
            clicks = row.metrics.clicks
            conversions = row.metrics.conversions
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = (cost / conversions) if conversions > 0 else 0.0

            # Extract headlines and descriptions from responsive search ads
            headlines = []
            descriptions = []
            try:
                rsa = row.ad_group_ad.ad.responsive_search_ad
                if rsa.headlines:
                    headlines = [h.text for h in rsa.headlines]
                if rsa.descriptions:
                    descriptions = [d.text for d in rsa.descriptions]
            except Exception:
                pass

            final_urls = list(row.ad_group_ad.ad.final_urls) if row.ad_group_ad.ad.final_urls else []
            final_url = final_urls[0] if final_urls else ""

            ads.append(AdMetrics(
                ad_id=str(row.ad_group_ad.ad.id),
                ad_group_id=str(row.ad_group.id),
                ad_group_name=row.ad_group.name,
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                status=row.ad_group_ad.status.name,
                ad_type=row.ad_group_ad.ad.type_.name if hasattr(row.ad_group_ad.ad, 'type_') else str(row.ad_group_ad.ad.type),
                headlines=headlines,
                descriptions=descriptions,
                final_url=final_url,
                impressions=row.metrics.impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            ))

        result = AdPerformanceReport(
            ads=ads,
            total_ads=len(ads),
            date_range=date_range,
        )
        cache_set("ad_perf", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")


# ============================================================
# N-GRAM ANALYSIS (computed from search term data)
# ============================================================

def _extract_ngrams(text: str, n: int) -> list[str]:
    """Extract n-grams from a search term."""
    words = text.lower().strip().split()
    if len(words) < n:
        return []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def get_ngram_analysis(
    campaign_id: Optional[str] = None,
    date_range: Optional[DateRange] = None,
    min_n: int = 1,
    max_n: int = 3,
    min_frequency: int = 2,
    limit: int = 100,
) -> NgramReport:
    """Analyze search terms by breaking them into n-grams with aggregated metrics."""
    if date_range is None:
        date_range = _default_date_range()

    # Check cache
    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
        min_n=min_n,
        max_n=max_n,
        min_freq=min_frequency,
    )
    cached = cache_get("ngrams", **cache_params)
    if cached:
        return NgramReport.model_validate_json(cached)

    # Fetch search terms (reuse existing function)
    search_report = get_search_terms(
        campaign_id=campaign_id,
        date_range=date_range,
        limit=500,  # get more search terms for better n-gram analysis
    )

    # Aggregate n-grams
    ngram_data: dict[str, dict] = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "cost": 0.0,
        "conversions": 0.0, "search_terms": set(), "n": 0,
    })

    for st in search_report.search_terms:
        for n in range(min_n, max_n + 1):
            for ngram in _extract_ngrams(st.search_term, n):
                entry = ngram_data[ngram]
                entry["n"] = n
                entry["impressions"] += st.impressions
                entry["clicks"] += st.clicks
                entry["cost"] += st.cost
                entry["conversions"] += st.conversions
                entry["search_terms"].add(st.search_term)

    # Build results, filter by min_frequency
    ngrams = []
    for ngram_text, data in ngram_data.items():
        freq = len(data["search_terms"])
        if freq < min_frequency:
            continue

        clicks = data["clicks"]
        impressions = data["impressions"]
        cost = data["cost"]
        conversions = data["conversions"]
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        avg_cpc = (cost / clicks) if clicks > 0 else 0.0
        conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
        cost_per_conv = (cost / conversions) if conversions > 0 else 0.0

        ngrams.append(NgramMetrics(
            ngram=ngram_text,
            n=data["n"],
            frequency=freq,
            impressions=impressions,
            clicks=clicks,
            cost=round(cost, 2),
            conversions=round(conversions, 2),
            ctr=round(ctr, 2),
            avg_cpc=round(avg_cpc, 2),
            conversion_rate=round(conv_rate, 2),
            cost_per_conversion=round(cost_per_conv, 2),
            search_terms=sorted(list(data["search_terms"]))[:5],  # top 5 examples
        ))

    # Sort by cost descending and limit
    ngrams.sort(key=lambda x: x.cost, reverse=True)
    ngrams = ngrams[:limit]

    result = NgramReport(
        ngrams=ngrams,
        total_ngrams=len(ngrams),
        date_range=date_range,
    )
    cache_set("ngrams", result.model_dump_json(), **cache_params)
    return result


# ============================================================
# LANDING PAGE PERFORMANCE
# ============================================================

def get_landing_page_performance(
    campaign_id: Optional[str] = None,
    date_range: Optional[DateRange] = None,
    limit: int = 50,
) -> LandingPageReport:
    """Fetch landing page performance metrics (cached 15 min)."""
    if date_range is None:
        date_range = _default_date_range()

    cache_params = dict(
        start=str(date_range.start_date),
        end=str(date_range.end_date),
        campaign=campaign_id,
        limit=limit,
    )
    cached = cache_get("landing_pages", **cache_params)
    if cached:
        return LandingPageReport.model_validate_json(cached)

    settings = get_settings()
    client = _get_client()
    ga_service = client.get_service("GoogleAdsService")

    start_str = date_range.start_date.strftime("%Y-%m-%d")
    end_str = date_range.end_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            landing_page_view.unexpanded_final_url,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM landing_page_view
        WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
    """

    if campaign_id:
        query += f" AND campaign.id = {campaign_id}"

    query += f" ORDER BY metrics.cost_micros DESC LIMIT {limit}"

    try:
        response = ga_service.search(
            customer_id=settings.google_ads_customer_id, query=query
        )

        pages = []
        for row in response:
            cost = _micros_to_currency(row.metrics.cost_micros)
            avg_cpc = _micros_to_currency(row.metrics.average_cpc)
            clicks = row.metrics.clicks
            conversions = row.metrics.conversions
            conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0
            cost_per_conv = (cost / conversions) if conversions > 0 else 0.0

            pages.append(LandingPageMetrics(
                url=row.landing_page_view.unexpanded_final_url,
                impressions=row.metrics.impressions,
                clicks=clicks,
                cost=round(cost, 2),
                conversions=round(conversions, 2),
                ctr=round(row.metrics.ctr * 100, 2),
                avg_cpc=round(avg_cpc, 2),
                conversion_rate=round(conv_rate, 2),
                cost_per_conversion=round(cost_per_conv, 2),
            ))

        result = LandingPageReport(
            pages=pages,
            total_pages=len(pages),
            date_range=date_range,
        )
        cache_set("landing_pages", result.model_dump_json(), **cache_params)
        return result

    except GoogleAdsException as ex:
        error_messages = [error.message for error in ex.failure.errors]
        raise Exception(f"Google Ads API Error: {'; '.join(error_messages)}")