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
)
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
            campaign_criterion.location.geo_target_constant,
            geographic_view.country_criterion_id,
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

        # We also need geo target constant names — fetch them separately
        geo_ids: set[str] = set()
        raw_rows = []
        for row in response:
            raw_rows.append(row)
            geo_resource = row.campaign_criterion.location.geo_target_constant
            if geo_resource:
                geo_ids.add(geo_resource)

        # Fetch geo target names
        geo_names: dict[str, tuple[str, str]] = {}  # resource -> (name, type)
        if geo_ids:
            for geo_resource in geo_ids:
                try:
                    geo_query = f"""
                        SELECT
                            geo_target_constant.name,
                            geo_target_constant.target_type,
                            geo_target_constant.resource_name
                        FROM geo_target_constant
                        WHERE geo_target_constant.resource_name = '{geo_resource}'
                    """
                    geo_resp = ga_service.search(
                        customer_id=settings.google_ads_customer_id, query=geo_query
                    )
                    for gr in geo_resp:
                        geo_names[geo_resource] = (
                            gr.geo_target_constant.name,
                            gr.geo_target_constant.target_type,
                        )
                except Exception:
                    geo_names[geo_resource] = (geo_resource.split("/")[-1], "Unknown")

        locations = []
        for row in raw_rows:
            geo_resource = row.campaign_criterion.location.geo_target_constant
            name, loc_type = geo_names.get(geo_resource, (geo_resource.split("/")[-1] if geo_resource else "Unknown", ""))

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
                location_id=geo_resource.split("/")[-1] if geo_resource else "",
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
