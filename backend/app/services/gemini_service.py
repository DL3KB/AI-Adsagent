"""
Gemini AI Analysis Service
Analyzes Google Ads campaign data and provides actionable recommendations.

Optimization approach:
1. Pre-compute anomalies and patterns before sending to AI
2. Use structured analysis framework (not open-ended)
3. Force step-by-step reasoning with expert prompt
4. Highlight red flags in data so AI focuses on what matters
"""

import google.generativeai as genai
import json
import logging
from typing import Optional
from statistics import mean, stdev

from app.config import get_settings
from app.models.schemas import (
    CampaignOverview,
    KeywordMetrics,
    AdGroupMetrics,
    AnalysisResponse,
    Proposal,
    ProposalAction,
)

logger = logging.getLogger(__name__)

# ============================================================
# SYSTEM PROMPT — Expert PPC Strategist
# ============================================================
SYSTEM_PROMPT = """Du bist ein Senior Google Ads Strategist mit 15+ Jahren Erfahrung im Performance Marketing.
Du arbeitest methodisch und datengetrieben. Deine Analysen sind präzise, konkret und sofort umsetzbar.

## DEINE ANALYSE-METHODIK

Du gehst bei jeder Analyse systematisch diese 6 Checkpoints durch:

### 1. BUDGET-EFFIZIENZ
- Gibt es Kampagnen/Keywords die viel kosten aber wenig Conversions bringen? (Waste)
- Gibt es Kampagnen mit gutem ROAS die mehr Budget vertragen könnten? (Scaling-Potenzial)
- Wie ist die 80/20-Verteilung? (Welche 20% der Keywords generieren 80% der Conversions?)

### 2. QUALITY SCORE ANALYSE
- Keywords mit QS < 5: Dringend optimieren (Anzeigentext, Landingpage, Relevanz)
- Keywords mit QS 5-7: Verbesserungspotenzial identifizieren
- Keywords mit QS 8-10: Best Practices übertragen
- Fehlende Quality Scores: Warum? Zu wenig Impressionen?

### 3. CTR-BEWERTUNG (mit Benchmarks)
- Search CTR < 2%: Kritisch — Anzeigentexte und Keywords überprüfen
- Search CTR 2-4%: Unterdurchschnittlich — Optimierungspotenzial
- Search CTR 4-7%: Durchschnittlich — gut, aber verbesserbar
- Search CTR 7-10%: Überdurchschnittlich — Best Practices identifizieren
- Search CTR > 10%: Exzellent — möglicherweise zu enge Ausrichtung prüfen

### 4. CONVERSION-ANALYSE
- Conversion Rate < 1%: Landingpage-Problem oder falscher Traffic
- Conversion Rate 1-3%: Durchschnittlich
- Conversion Rate 3-5%: Gut
- Conversion Rate > 5%: Exzellent
- Kosten pro Conversion vs. Kundenlebenswert bewerten
- Keywords mit Klicks aber 0 Conversions identifizieren

### 5. KEYWORD-STRATEGIE
- Match Type Verteilung: Zu viel Broad Match = Streuverlust
- Negative Keywords: Fehlen sie? Welche vorschlagen?
- Keyword-Kannibalisierung: Überlappen sich Keywords zwischen Ad Groups?
- Long-Tail Chancen: Gibt es spezifischere Keywords mit besserem ROAS?

### 6. STRUKTUR & QUICK WINS
- Pausierte Kampagnen/Keywords die reaktiviert werden könnten
- Ad Groups mit nur 1-2 Keywords (zu wenig Daten)
- Kampagnen ohne Conversions (Tracking-Problem?)
- Sofort umsetzbare Verbesserungen (< 30 Min Aufwand)

## RESPONSE FORMAT

Antworte IMMER in diesem exakten JSON-Format:
{
    "summary": "2-3 Sätze Gesamtbewertung. Nenne den wichtigsten Handlungsbedarf und das größte Potenzial mit konkreten Zahlen.",
    "recommendations": [
        {
            "priority": "high|medium|low",
            "category": "budget|bidding|keywords|ads|targeting|quality_score|structure|tracking",
            "title": "Prägnanter Titel (max 10 Wörter)",
            "description": "Detaillierte Begründung MIT konkreten Zahlen aus den Daten. Erkläre WARUM das ein Problem ist und WAS es kostet.",
            "expected_impact": "Quantifizierter erwarteter Impact, z.B. 'CTR-Steigerung um ~2 Prozentpunkte' oder 'Einsparung von ~X EUR/Monat'",
            "action_items": ["Schritt 1 mit konkretem Detail", "Schritt 2 mit konkretem Detail", "Schritt 3"]
        }
    ],
    "insights": [
        {
            "type": "positive|negative|neutral",
            "metric": "CTR|CPC|Quality Score|Conversions|Budget|Structure",
            "title": "Kurzer Insight-Titel",
            "description": "Insight mit konkreten Zahlen und Benchmark-Vergleich"
        }
    ],
    "raw_data_summary": {
        "top_performers": ["Name: Metrik = Wert (warum gut)"],
        "underperformers": ["Name: Metrik = Wert (warum schlecht)"],
        "quick_wins": ["Sofort umsetzbare Maßnahme 1", "Sofort umsetzbare Maßnahme 2"],
        "key_metrics": {
            "avg_ctr": 0.0,
            "avg_cpc": 0.0,
            "total_conversions": 0.0,
            "total_spend": 0.0,
            "wasted_spend": 0.0,
            "best_campaign": "",
            "worst_campaign": ""
        }
    },
    "proposals": [
        {
            "action": "pause_keyword|enable_keyword|pause_campaign|enable_campaign|pause_ad_group|enable_ad_group|add_negative_keyword|change_keyword_bid|change_campaign_budget|change_keyword_match_type",
            "priority": "high|medium|low",
            "title": "Kurze Beschreibung der Änderung (max 10 Wörter)",
            "reason": "Warum diese Änderung? MIT konkreten Zahlen.",
            "expected_impact": "Erwarteter Impact, z.B. 'Einsparung von ~50 EUR/Monat'",
            "campaign_id": "123456789",
            "campaign_name": "Kampagnenname",
            "ad_group_id": "123456789 (nur wenn relevant)",
            "ad_group_name": "Ad Group Name (nur wenn relevant)",
            "keyword_id": "123456789 (nur wenn relevant)",
            "keyword_text": "keyword text (nur wenn relevant)",
            "current_value": "Aktueller Wert/Status",
            "new_value": "Neuer Wert/Status"
        }
    ]
}

## PROPOSALS — AUTOMATISIERBARE ÄNDERUNGSVORSCHLÄGE

Generiere für jede Empfehlung, die automatisch umgesetzt werden kann, einen konkreten Proposal.
Verwende NUR die IDs und Namen aus den bereitgestellten Daten — erfinde KEINE IDs.

Erlaubte Aktionen:
- `pause_keyword`: Keyword pausieren (braucht: ad_group_id, keyword_id, keyword_text)
- `enable_keyword`: Keyword aktivieren (braucht: ad_group_id, keyword_id, keyword_text)
- `pause_campaign`: Kampagne pausieren (braucht: campaign_id, campaign_name)
- `enable_campaign`: Kampagne aktivieren (braucht: campaign_id, campaign_name)
- `pause_ad_group`: Ad Group pausieren (braucht: ad_group_id, ad_group_name, campaign_id)
- `enable_ad_group`: Ad Group aktivieren (braucht: ad_group_id, ad_group_name, campaign_id)
- `add_negative_keyword`: Negatives Keyword hinzufügen (braucht: campaign_id, keyword_text, new_value=EXACT|PHRASE|BROAD)
- `change_keyword_bid`: Keyword-Gebot ändern (braucht: ad_group_id, keyword_id, keyword_text, current_value=aktuelles CPC in EUR, new_value=neues CPC in EUR)
- `change_campaign_budget`: Tagesbudget ändern (braucht: campaign_id, campaign_name, current_value=aktuelles Budget, new_value=neues Tagesbudget in EUR)
- `change_keyword_match_type`: Match Type ändern (braucht: ad_group_id, keyword_id, keyword_text, current_value=BROAD, new_value=EXACT|PHRASE)

WICHTIG:
- Nur Proposals mit ECHTEN IDs aus den Daten erstellen
- Mindestens 3 Proposals wenn Optimierungspotenzial besteht
- current_value und new_value immer als String angeben (z.B. "1.50" für EUR)
- Proposals nach Priorität sortieren (high zuerst)

## REGELN
- Mindestens 5 Empfehlungen, sortiert nach Impact (high zuerst)
- JEDE Empfehlung MUSS konkrete Zahlen aus den Daten enthalten
- Nenne keine generischen Tipps — alles muss sich auf die tatsächlichen Daten beziehen
- Identifiziere mindestens 2 Quick Wins (< 30 Min umsetzbar)
- Bei fehlenden Daten (z.B. kein Quality Score): Erwähne das als Problem
- Berechne verschwendetes Budget: Kosten für Keywords/Kampagnen ohne Conversions
"""

# ============================================================
# CHAT SYSTEM PROMPT
# ============================================================
CHAT_SYSTEM_PROMPT = """Du bist ein erfahrener Google Ads Berater in einem Analysegespräch.

Regeln:
- Antworte IMMER mit konkretem Bezug auf die vorliegenden Daten
- Nenne Zahlen, Prozentsätze und EUR-Beträge
- Vergleiche mit Branchen-Benchmarks wo relevant
- Gib am Ende jeder Antwort 1-2 konkrete nächste Schritte
- Formatiere leserlich mit Aufzählungszeichen
- Antworte auf Deutsch
- Sei direkt und wertend — der Nutzer will klare Empfehlungen, keine Diplomatie
- Wenn du etwas nicht aus den Daten ablesen kannst, sag es klar"""


def _configure_gemini():
    """Configure the Gemini API client."""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)


# ============================================================
# PRE-ANALYSIS: Compute patterns before sending to AI
# ============================================================
def _compute_anomalies(
    overview: CampaignOverview,
    keywords: Optional[list[KeywordMetrics]] = None,
) -> dict:
    """
    Pre-compute statistical anomalies and patterns.
    This gives Gemini concrete red flags to analyze instead of raw data.
    """
    anomalies = {
        "wasted_spend": 0.0,
        "wasted_keywords": [],
        "low_quality_keywords": [],
        "high_cpc_outliers": [],
        "zero_conversion_campaigns": [],
        "top_converters": [],
        "ctr_outliers_low": [],
        "ctr_outliers_high": [],
        "budget_concentration": "",
    }

    # Campaign-level anomalies
    if overview.campaigns:
        costs = [c.cost for c in overview.campaigns if c.cost > 0]
        ctrs = [c.ctr for c in overview.campaigns if c.impressions > 100]

        # Zero-conversion campaigns with spend
        for c in overview.campaigns:
            if c.cost > 0 and c.conversions == 0:
                anomalies["zero_conversion_campaigns"].append(
                    f"{c.campaign_name}: {c.cost:.2f} EUR ausgegeben, 0 Conversions"
                )
                anomalies["wasted_spend"] += c.cost

        # Budget concentration (top campaign % of total)
        if overview.total_cost > 0:
            sorted_by_cost = sorted(overview.campaigns, key=lambda x: x.cost, reverse=True)
            top_cost = sorted_by_cost[0].cost if sorted_by_cost else 0
            concentration = (top_cost / overview.total_cost) * 100
            anomalies["budget_concentration"] = (
                f"{sorted_by_cost[0].campaign_name} verbraucht {concentration:.0f}% des Gesamtbudgets"
            )

        # Top converters
        converting = [c for c in overview.campaigns if c.conversions > 0]
        converting.sort(key=lambda x: x.cost_per_conversion if x.cost_per_conversion > 0 else float('inf'))
        for c in converting[:3]:
            anomalies["top_converters"].append(
                f"{c.campaign_name}: {c.conversions:.1f} Conv. bei {c.cost_per_conversion:.2f} EUR/Conv."
            )

    # Keyword-level anomalies
    if keywords:
        # Wasted spend: keywords with clicks but zero conversions
        for kw in keywords:
            if kw.clicks > 5 and kw.conversions == 0 and kw.cost > 5:
                anomalies["wasted_keywords"].append(
                    f"\"{kw.keyword_text}\" [{kw.match_type}]: {kw.cost:.2f} EUR, {kw.clicks} Klicks, 0 Conv."
                )
                anomalies["wasted_spend"] += kw.cost

        # Low quality scores
        for kw in keywords:
            if kw.quality_score is not None and kw.quality_score < 5:
                anomalies["low_quality_keywords"].append(
                    f"\"{kw.keyword_text}\": QS={kw.quality_score}, CTR={kw.ctr}%"
                )

        # High CPC outliers (> 2x average)
        cpcs = [kw.avg_cpc for kw in keywords if kw.avg_cpc > 0]
        if cpcs:
            avg_cpc = mean(cpcs)
            for kw in keywords:
                if kw.avg_cpc > avg_cpc * 2 and kw.clicks > 3:
                    anomalies["high_cpc_outliers"].append(
                        f"\"{kw.keyword_text}\": CPC={kw.avg_cpc:.2f} EUR (Ø {avg_cpc:.2f} EUR)"
                    )

        # CTR outliers
        ctrs = [kw.ctr for kw in keywords if kw.impressions > 50]
        if len(ctrs) > 2:
            avg_ctr = mean(ctrs)
            try:
                std_ctr = stdev(ctrs)
            except Exception:
                std_ctr = avg_ctr * 0.5
            for kw in keywords:
                if kw.impressions > 50:
                    if kw.ctr < max(avg_ctr - std_ctr, 0.5):
                        anomalies["ctr_outliers_low"].append(
                            f"\"{kw.keyword_text}\": CTR={kw.ctr}% (Ø {avg_ctr:.1f}%)"
                        )
                    elif kw.ctr > avg_ctr + std_ctr * 1.5:
                        anomalies["ctr_outliers_high"].append(
                            f"\"{kw.keyword_text}\": CTR={kw.ctr}% (Ø {avg_ctr:.1f}%)"
                        )

    return anomalies


# ============================================================
# DATA FORMATTING: Structure data for the AI prompt
# ============================================================
def _prepare_campaign_data(
    overview: CampaignOverview,
    keywords: Optional[list[KeywordMetrics]] = None,
    ad_groups: Optional[list[AdGroupMetrics]] = None,
) -> str:
    """Format campaign data with pre-computed anomalies highlighted."""

    anomalies = _compute_anomalies(overview, keywords)
    data_parts = []

    # ---- ANOMALY HIGHLIGHTS (most important — AI reads this first) ----
    data_parts.append("=" * 60)
    data_parts.append("⚠️  VORANALYSE — IDENTIFIZIERTE PROBLEME")
    data_parts.append("=" * 60)

    data_parts.append(f"\nVerschwendetes Budget: {anomalies['wasted_spend']:.2f} EUR")
    data_parts.append(f"(= Kosten für Keywords/Kampagnen ohne Conversions)")

    if anomalies["zero_conversion_campaigns"]:
        data_parts.append(f"\n🔴 Kampagnen ohne Conversions ({len(anomalies['zero_conversion_campaigns'])}):")
        for item in anomalies["zero_conversion_campaigns"][:5]:
            data_parts.append(f"  - {item}")

    if anomalies["wasted_keywords"]:
        data_parts.append(f"\n🔴 Keywords mit Kosten aber ohne Conversions ({len(anomalies['wasted_keywords'])}):")
        for item in anomalies["wasted_keywords"][:10]:
            data_parts.append(f"  - {item}")

    if anomalies["low_quality_keywords"]:
        data_parts.append(f"\n🟡 Keywords mit niedrigem Quality Score ({len(anomalies['low_quality_keywords'])}):")
        for item in anomalies["low_quality_keywords"][:10]:
            data_parts.append(f"  - {item}")

    if anomalies["high_cpc_outliers"]:
        data_parts.append(f"\n🟡 CPC-Ausreißer ({len(anomalies['high_cpc_outliers'])}):")
        for item in anomalies["high_cpc_outliers"][:5]:
            data_parts.append(f"  - {item}")

    if anomalies["ctr_outliers_low"]:
        data_parts.append(f"\n🔴 Unterdurchschnittliche CTR:")
        for item in anomalies["ctr_outliers_low"][:5]:
            data_parts.append(f"  - {item}")

    if anomalies["ctr_outliers_high"]:
        data_parts.append(f"\n🟢 Überdurchschnittliche CTR (Best Practices):")
        for item in anomalies["ctr_outliers_high"][:5]:
            data_parts.append(f"  - {item}")

    if anomalies["top_converters"]:
        data_parts.append(f"\n🟢 Top Performer:")
        for item in anomalies["top_converters"]:
            data_parts.append(f"  - {item}")

    if anomalies["budget_concentration"]:
        data_parts.append(f"\n📊 Budget-Konzentration: {anomalies['budget_concentration']}")

    # ---- CAMPAIGN OVERVIEW ----
    data_parts.append("\n" + "=" * 60)
    data_parts.append("📊 KAMPAGNEN-ÜBERSICHT")
    data_parts.append("=" * 60)
    data_parts.append(f"Zeitraum: {overview.date_range.start_date} bis {overview.date_range.end_date}")
    days = (overview.date_range.end_date - overview.date_range.start_date).days or 1
    data_parts.append(f"Analysezeitraum: {days} Tage")
    data_parts.append(f"Gesamtausgaben: {overview.total_cost:.2f} EUR ({overview.total_cost / days:.2f} EUR/Tag)")
    data_parts.append(f"Gesamt-Klicks: {overview.total_clicks:,}")
    data_parts.append(f"Gesamt-Impressionen: {overview.total_impressions:,}")
    data_parts.append(f"Gesamt-Conversions: {overview.total_conversions:.1f}")
    data_parts.append(f"Durchschnittliche CTR: {overview.avg_ctr:.2f}%")
    data_parts.append(f"Durchschnittlicher CPC: {overview.avg_cpc:.2f} EUR")
    if overview.total_conversions > 0:
        avg_cpa = overview.total_cost / overview.total_conversions
        data_parts.append(f"Durchschnittliche Kosten/Conversion: {avg_cpa:.2f} EUR")
    data_parts.append(f"Anzahl Kampagnen: {len(overview.campaigns)}")

    # ---- INDIVIDUAL CAMPAIGNS ----
    data_parts.append("\n" + "-" * 40)
    data_parts.append("EINZELNE KAMPAGNEN (sortiert nach Kosten)")
    data_parts.append("-" * 40)
    for i, c in enumerate(overview.campaigns, 1):
        pct_budget = (c.cost / overview.total_cost * 100) if overview.total_cost > 0 else 0
        data_parts.append(f"\n[{i}] {c.campaign_name} (campaign_id={c.campaign_id})")
        data_parts.append(f"    Status: {c.status} | Budget-Anteil: {pct_budget:.1f}%")
        data_parts.append(f"    Impressionen: {c.impressions:,} | Klicks: {c.clicks:,} | CTR: {c.ctr:.2f}%")
        data_parts.append(f"    Kosten: {c.cost:.2f} EUR | CPC: {c.avg_cpc:.2f} EUR")
        data_parts.append(f"    Conversions: {c.conversions:.1f} | Conv. Rate: {c.conversion_rate:.2f}% | CPA: {c.cost_per_conversion:.2f} EUR")

    # ---- AD GROUPS ----
    if ad_groups:
        data_parts.append("\n" + "-" * 40)
        data_parts.append("ANZEIGENGRUPPEN")
        data_parts.append("-" * 40)
        for ag in ad_groups:
            data_parts.append(f"\n  {ag.campaign_name} > {ag.ad_group_name} (ad_group_id={ag.ad_group_id}, campaign_id={ag.campaign_id}) ({ag.status})")
            data_parts.append(f"    Imp: {ag.impressions:,} | Klicks: {ag.clicks:,} | CTR: {ag.ctr:.2f}%")
            data_parts.append(f"    Kosten: {ag.cost:.2f} EUR | CPC: {ag.avg_cpc:.2f} EUR | Conv: {ag.conversions:.1f}")

    # ---- KEYWORDS ----
    if keywords:
        # Separate by quality score groups
        qs_groups = {"high": [], "mid": [], "low": [], "none": []}
        for kw in keywords:
            if kw.quality_score is None:
                qs_groups["none"].append(kw)
            elif kw.quality_score >= 8:
                qs_groups["high"].append(kw)
            elif kw.quality_score >= 5:
                qs_groups["mid"].append(kw)
            else:
                qs_groups["low"].append(kw)

        data_parts.append("\n" + "-" * 40)
        data_parts.append(f"KEYWORDS ({len(keywords)} total)")
        data_parts.append(f"  QS 8-10: {len(qs_groups['high'])} | QS 5-7: {len(qs_groups['mid'])} | QS 1-4: {len(qs_groups['low'])} | Kein QS: {len(qs_groups['none'])}")
        data_parts.append("-" * 40)

        # Match type distribution
        match_types = {}
        for kw in keywords:
            mt = kw.match_type
            match_types[mt] = match_types.get(mt, 0) + 1
        data_parts.append(f"  Match Types: {', '.join(f'{mt}: {count}' for mt, count in match_types.items())}")

        for kw in keywords:
            qs_str = f"QS:{kw.quality_score}" if kw.quality_score else "QS:–"
            conv_str = f"{kw.conversions:.1f} Conv" if kw.conversions > 0 else "0 Conv"
            flag = ""
            if kw.quality_score is not None and kw.quality_score < 5:
                flag = " ⚠️"
            if kw.clicks > 5 and kw.conversions == 0 and kw.cost > 5:
                flag = " 🔴"
            data_parts.append(
                f"  [{kw.match_type}] \"{kw.keyword_text}\" (keyword_id={kw.keyword_id}, ad_group_id={kw.ad_group_id}, campaign_id={kw.campaign_id}) {qs_str} | "
                f"Imp:{kw.impressions:,} Klicks:{kw.clicks} CTR:{kw.ctr:.1f}% "
                f"CPC:{kw.avg_cpc:.2f}€ Kosten:{kw.cost:.2f}€ {conv_str}{flag}"
            )

    return "\n".join(data_parts)


# ============================================================
# MAIN ANALYSIS
# ============================================================
def analyze_campaigns(
    overview: CampaignOverview,
    keywords: Optional[list[KeywordMetrics]] = None,
    ad_groups: Optional[list[AdGroupMetrics]] = None,
    focus_areas: Optional[list[str]] = None,
) -> AnalysisResponse:
    """
    Send campaign data to Gemini for analysis and get recommendations.
    Uses pre-computed anomalies + expert prompt for precise results.
    """
    _configure_gemini()

    # Prepare the data with anomaly highlights
    campaign_data = _prepare_campaign_data(overview, keywords, ad_groups)

    # Build the user prompt with analysis instructions
    user_prompt = f"""Analysiere die folgenden Google Ads Kampagnendaten.

Gehe systematisch die 6 Checkpoints durch (Budget-Effizienz, Quality Scores, CTR, Conversions, Keyword-Strategie, Quick Wins).

Die Voranalyse hat bereits Probleme identifiziert — bewerte diese und ergänze weitere Erkenntnisse.

{campaign_data}"""

    if focus_areas:
        focus_map = {
            "ctr": "CTR-Optimierung (Anzeigentexte, Keywords, Relevanz)",
            "quality_score": "Quality Score Verbesserung (Relevanz, Landingpage, erwartete CTR)",
            "budget": "Budget-Effizienz (Waste reduzieren, Scaling-Potenzial)",
            "conversions": "Conversion-Optimierung (Rate verbessern, CPA senken)",
            "keywords": "Keyword-Strategie (Match Types, Negative Keywords, Struktur)",
            "structure": "Account-Struktur (Kampagnen-/Ad Group-Organisation)",
        }
        focus_descriptions = [focus_map.get(f, f) for f in focus_areas]
        user_prompt += f"\n\n🎯 PRIORITÄRER FOKUS: {', '.join(focus_descriptions)}"

    # Call Gemini with optimized settings
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.2,       # Low temp = more precise, less creative
            top_p=0.85,
            top_k=40,
            max_output_tokens=8192,  # More room for detailed analysis
            response_mime_type="application/json",
        ),
    )

    response = model.generate_content(user_prompt)

    # Parse the response
    try:
        result = json.loads(response.text)

        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recs = result.get("recommendations", [])
        recs.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 2))

        # Parse proposals
        raw_proposals = result.get("proposals", [])
        proposals = []
        for idx, p in enumerate(raw_proposals):
            try:
                action_str = p.get("action", "")
                # Validate action is a known ProposalAction
                try:
                    action = ProposalAction(action_str)
                except ValueError:
                    logger.warning(f"Unknown proposal action: {action_str}, skipping")
                    continue

                proposal = Proposal(
                    id=f"proposal-{idx + 1}",
                    action=action,
                    priority=p.get("priority", "medium"),
                    title=p.get("title", ""),
                    reason=p.get("reason", ""),
                    expected_impact=p.get("expected_impact", ""),
                    campaign_id=str(p["campaign_id"]) if p.get("campaign_id") else None,
                    campaign_name=p.get("campaign_name"),
                    ad_group_id=str(p["ad_group_id"]) if p.get("ad_group_id") else None,
                    ad_group_name=p.get("ad_group_name"),
                    keyword_id=str(p["keyword_id"]) if p.get("keyword_id") else None,
                    keyword_text=p.get("keyword_text"),
                    current_value=str(p["current_value"]) if p.get("current_value") is not None else None,
                    new_value=str(p["new_value"]) if p.get("new_value") is not None else None,
                )
                proposals.append(proposal)
            except Exception as e:
                logger.warning(f"Failed to parse proposal {idx}: {e}")
                continue

        # Sort proposals by priority
        proposals.sort(key=lambda p: priority_order.get(p.priority, 2))

        return AnalysisResponse(
            summary=result.get("summary", ""),
            recommendations=recs,
            insights=result.get("insights", []),
            raw_data_summary=result.get("raw_data_summary", {}),
            proposals=proposals,
        )
    except json.JSONDecodeError:
        return AnalysisResponse(
            summary=response.text[:500],
            recommendations=[
                {
                    "priority": "medium",
                    "category": "general",
                    "title": "Analyse-Ergebnis",
                    "description": response.text,
                    "expected_impact": "Siehe Details",
                    "action_items": [],
                }
            ],
            insights=[],
            raw_data_summary={},
            proposals=[],
        )


# ============================================================
# CHAT
# ============================================================
def chat_about_campaigns(
    overview: CampaignOverview,
    user_question: str,
    keywords: Optional[list[KeywordMetrics]] = None,
) -> str:
    """
    Have a conversational exchange about campaign data.
    Uses pre-computed anomalies for context-aware answers.
    """
    _configure_gemini()

    campaign_data = _prepare_campaign_data(overview, keywords)

    chat_prompt = f"""Hier sind die aktuellen Google Ads Kampagnendaten mit Voranalyse:

{campaign_data}

---

FRAGE DES NUTZERS: {user_question}

Antworte präzise mit Bezug auf die Daten. Nenne konkrete Zahlen.
Gib am Ende 1-2 konkrete nächste Schritte als Empfehlung.
Formatiere mit Aufzählungszeichen für Lesbarkeit."""

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=CHAT_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.4,
            top_p=0.9,
            max_output_tokens=3072,
        ),
    )

    response = model.generate_content(chat_prompt)
    return response.text
