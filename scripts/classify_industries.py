#!/usr/bin/env python3
"""
Phase 4: Industry Classification & Per-Industry P:C Ratio Analysis

Classifies all companies from OPPT (123) and OPP-115 (115) corpora into
industry sectors and computes per-industry statistics for the
commitment avoidance paper.

Author: Research team
"""

import json
import math
import statistics
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
INPUT_FILE = DATA_DIR / "phase3_ratio_analysis.json"
OUTPUT_FILE = DATA_DIR / "industry_analysis.json"

# ── Industry Sectors ───────────────────────────────────────────────────────
SECTORS = [
    "Technology/Software",
    "Social Media",
    "E-Commerce/Retail",
    "Financial Services",
    "Healthcare/Pharma",
    "Media/Entertainment",
    "Telecommunications",
    "Government/Education",
    "Data Broker/Analytics",
    "Travel/Hospitality",
    "Automotive",
    "Food/Beverage",
    "Other",
]

# ── OPPT Company → Industry Mapping (123 companies) ───────────────────────
OPPT_INDUSTRY = {
    # Technology/Software
    "adobe": "Technology/Software",
    "anthropic": "Technology/Software",
    "apple": "Technology/Software",
    "cursor": "Technology/Software",
    "dropbox": "Technology/Software",
    "github": "Technology/Software",
    "google": "Technology/Software",
    "grammarly": "Technology/Software",
    "jasper": "Technology/Software",
    "khan-academy": "Technology/Software",
    "microsoft": "Technology/Software",
    "midjourney": "Technology/Software",
    "notion": "Technology/Software",
    "openai": "Technology/Software",
    "perplexity": "Technology/Software",
    "replit": "Technology/Software",
    "rosetta-stone": "Technology/Software",
    "runway": "Technology/Software",
    "salesforce": "Technology/Software",
    "slack": "Technology/Software",
    "vercel": "Technology/Software",
    "zoom": "Technology/Software",
    "duolingo": "Technology/Software",

    # Social Media
    "bumble": "Social Media",
    "discord": "Social Media",
    "grindr": "Social Media",
    "linkedin": "Social Media",
    "meta": "Social Media",
    "ngl": "Social Media",
    "pinterest": "Social Media",
    "reddit": "Social Media",
    "snapchat": "Social Media",
    "tiktok": "Social Media",
    "tinder": "Social Media",
    "x": "Social Media",

    # E-Commerce/Retail
    "alibaba": "E-Commerce/Retail",
    "amazon": "E-Commerce/Retail",
    "doordash": "E-Commerce/Retail",
    "ebay": "E-Commerce/Retail",
    "instacart": "E-Commerce/Retail",
    "shopify": "E-Commerce/Retail",
    "walmart": "E-Commerce/Retail",
    "xiaomi": "E-Commerce/Retail",
    "zillow": "E-Commerce/Retail",
    "realtor": "E-Commerce/Retail",
    "redfin": "E-Commerce/Retail",

    # Financial Services
    "binance": "Financial Services",
    "chase": "Financial Services",
    "coinbase": "Financial Services",
    "equifax": "Financial Services",
    "kraken": "Financial Services",
    "paypal": "Financial Services",
    "robinhood": "Financial Services",
    "stripe": "Financial Services",
    "venmo": "Financial Services",
    "wells-fargo": "Financial Services",
    "wise": "Financial Services",
    "experian": "Financial Services",

    # Healthcare/Pharma
    "23andme": "Healthcare/Pharma",
    "betterhelp": "Healthcare/Pharma",
    "cerebral": "Healthcare/Pharma",
    "cvs-health": "Healthcare/Pharma",
    "peloton": "Healthcare/Pharma",
    "premom": "Healthcare/Pharma",
    "monument": "Healthcare/Pharma",

    # Media/Entertainment
    "disney": "Media/Entertainment",
    "draftkings": "Media/Entertainment",
    "epic-games": "Media/Entertainment",
    "fanduel": "Media/Entertainment",
    "netflix": "Media/Entertainment",
    "roblox": "Media/Entertainment",
    "spotify": "Media/Entertainment",
    "steam": "Media/Entertainment",
    "strava": "Media/Entertainment",
    "twitch": "Media/Entertainment",

    # Telecommunications
    "att": "Telecommunications",
    "nordvpn": "Telecommunications",
    "t-mobile": "Telecommunications",
    "verizon": "Telecommunications",
    "vonage": "Telecommunications",
    "ring": "Telecommunications",

    # Government/Education  (incl. corrections/gov contractors)
    "coursera": "Government/Education",

    # Data Broker/Analytics
    "appriss": "Data Broker/Analytics",
    "babel-street": "Data Broker/Analytics",
    "bluehawk": "Data Broker/Analytics",
    "clearview-ai": "Data Broker/Analytics",
    "corsight-ai": "Data Broker/Analytics",
    "eyematch-ai": "Data Broker/Analytics",
    "flock-safety": "Data Broker/Analytics",
    "gravy-analytics": "Data Broker/Analytics",
    "kochava": "Data Broker/Analytics",
    "lexisnexis": "Data Broker/Analytics",
    "pimeyes": "Data Broker/Analytics",
    "safegraph": "Data Broker/Analytics",
    "thomson-reuters": "Data Broker/Analytics",
    "x-mode-social": "Data Broker/Analytics",
    "zignal-labs": "Data Broker/Analytics",
    "palantir": "Data Broker/Analytics",
    "avast": "Data Broker/Analytics",

    # Travel/Hospitality
    "airbnb": "Travel/Hospitality",
    "american-airlines": "Travel/Hospitality",
    "booking": "Travel/Hospitality",
    "delta": "Travel/Hospitality",
    "hilton": "Travel/Hospitality",
    "hyatt": "Travel/Hospitality",
    "ihg": "Travel/Hospitality",
    "lyft": "Travel/Hospitality",
    "marriott": "Travel/Hospitality",
    "southwest-airlines": "Travel/Hospitality",
    "uber": "Travel/Hospitality",
    "united-airlines": "Travel/Hospitality",

    # Automotive
    "tesla": "Automotive",

    # Defense/Surveillance → Other
    "anduril": "Other",
    "bi-incorporated": "Other",
    "cellebrite": "Other",
    "corecivic": "Other",
    "geo-group": "Other",
    "l3harris": "Other",
    "magnet-forensics": "Other",
    "motorola-solutions": "Other",
    "northrop-grumman": "Other",
    "penlink": "Other",
    "sosi": "Other",
}

# ── OPP-115 Company → Industry Mapping (115 companies) ────────────────────
OPP115_INDUSTRY = {
    # Technology/Software
    "aol.com": "Technology/Software",
    "google.com": "Technology/Software",
    "msn.com": "Technology/Software",
    "yahoo.com": "Technology/Software",
    "lynda.com": "Technology/Software",
    "internetbrands.com": "Technology/Software",
    "playstation.com": "Technology/Software",
    "rockstargames.com": "Technology/Software",
    "steampowered.com": "Technology/Software",
    "jibjab.com": "Technology/Software",
    "thefreedictionary.com": "Technology/Software",
    "reference.com": "Technology/Software",
    "minecraft.gamepedia.com": "Technology/Software",

    # Social Media
    "instagram.com": "Social Media",
    "reddit.com": "Social Media",
    "gawker.com": "Social Media",
    "boardgamegeek.com": "Social Media",
    "geocaching.com": "Social Media",

    # E-Commerce/Retail
    "amazon.com": "E-Commerce/Retail",
    "barnesandnoble.com": "E-Commerce/Retail",
    "gamestop.com": "E-Commerce/Retail",
    "lids.com": "E-Commerce/Retail",
    "lodgemfg.com": "E-Commerce/Retail",
    "tangeroutlet.com": "E-Commerce/Retail",
    "walmart.com": "E-Commerce/Retail",
    "ticketmaster.com": "E-Commerce/Retail",

    # Financial Services
    "bankofamerica.com": "Financial Services",
    "chasepaymentech.com": "Financial Services",
    "fool.com": "Financial Services",
    "zacks.com": "Financial Services",
    "stlouisfed.org": "Financial Services",
    "opensecrets.org": "Financial Services",
    "allstate.com": "Financial Services",

    # Healthcare/Pharma
    "everydayhealth.com": "Healthcare/Pharma",
    "kaleidahealth.org": "Healthcare/Pharma",
    "naturalnews.com": "Healthcare/Pharma",
    "uptodate.com": "Healthcare/Pharma",
    "foodallergy.org": "Healthcare/Pharma",
    "gwdocs.com": "Healthcare/Pharma",

    # Media/Entertainment
    "abcnews.com": "Media/Entertainment",
    "adweek.com": "Media/Entertainment",
    "cbsinteractive.com": "Media/Entertainment",
    "dailynews.com": "Media/Entertainment",
    "esquire.com": "Media/Entertainment",
    "fortune.com": "Media/Entertainment",
    "foxsports.com": "Media/Entertainment",
    "fredericknewspost.com": "Media/Entertainment",
    "freep.com": "Media/Entertainment",
    "highgearmedia.com": "Media/Entertainment",
    "imdb.com": "Media/Entertainment",
    "latinpost.com": "Media/Entertainment",
    "meredith.com": "Media/Entertainment",
    "miaminewtimes.com": "Media/Entertainment",
    "mlb.mlb.com": "Media/Entertainment",
    "nbcuniversal.com": "Media/Entertainment",
    "newsbusters.org": "Media/Entertainment",
    "nytimes.com": "Media/Entertainment",
    "ocregister.com": "Media/Entertainment",
    "pbs.org": "Media/Entertainment",
    "post-gazette.com": "Media/Entertainment",
    "redorbit.com": "Media/Entertainment",
    "sci-news.com": "Media/Entertainment",
    "sheknows.com": "Media/Entertainment",
    "sltrib.com": "Media/Entertainment",
    "sports-reference.com": "Media/Entertainment",
    "style.com": "Media/Entertainment",
    "taylorswift.com": "Media/Entertainment",
    "ted.com": "Media/Entertainment",
    "theatlantic.com": "Media/Entertainment",
    "thehill.com": "Media/Entertainment",
    "timeinc.com": "Media/Entertainment",
    "tulsaworld.com": "Media/Entertainment",
    "voxmedia.com": "Media/Entertainment",
    "washingtonian.com": "Media/Entertainment",
    "washingtonpost.com": "Media/Entertainment",
    "wnep.com": "Media/Entertainment",
    "wsmv.com": "Media/Entertainment",
    "acbj.com": "Media/Entertainment",
    "dailyillini.com": "Media/Entertainment",
    "disinfo.com": "Media/Entertainment",
    "enthusiastnetwork.com": "Media/Entertainment",
    "randomhouse.com": "Media/Entertainment",
    "sidearmsports.com": "Media/Entertainment",
    "liquor.com": "Media/Entertainment",

    # Telecommunications
    # (none clearly in OPP-115)

    # Government/Education
    "archives.gov": "Government/Education",
    "austincc.edu": "Government/Education",
    "citizen.org": "Government/Education",
    "dcccd.edu": "Government/Education",
    "earthkam.org": "Government/Education",
    "education.jlab.org": "Government/Education",
    "ifsa-butler.org": "Government/Education",
    "sciencemag.org": "Government/Education",
    "si.edu": "Government/Education",
    "usa.gov": "Government/Education",
    "uh.edu": "Government/Education",
    "www.loc.gov": "Government/Education",
    "cincymuseum.org": "Government/Education",
    "solarviews.com": "Government/Education",

    # Data Broker/Analytics
    # (none clearly in OPP-115)

    # Travel/Hospitality
    "mohegansun.com": "Travel/Hospitality",
    "neworleansonline.com": "Travel/Hospitality",
    "vikings.com": "Travel/Hospitality",
    "military.com": "Travel/Hospitality",

    # Automotive
    "honda.com": "Automotive",

    # Food/Beverage
    "abita.com": "Food/Beverage",
    "buffalowildwings.com": "Food/Beverage",
    "cariboucoffee.com": "Food/Beverage",
    "coffeereview.com": "Food/Beverage",
    "communitycoffee.com": "Food/Beverage",
    "dairyqueen.com": "Food/Beverage",
    "eatchicken.com": "Food/Beverage",
    "ironhorsevineyards.com": "Food/Beverage",
    "kraftrecipes.com": "Food/Beverage",
    "restaurantnews.com": "Food/Beverage",
    "tgifridays.com": "Food/Beverage",

    # Other
    "dogbreedinfo.com": "Other",
}


def load_data():
    """Load the phase3 ratio analysis JSON."""
    with open(INPUT_FILE) as f:
        return json.load(f)


def validate_mappings(data):
    """Ensure every company is mapped to an industry."""
    oppt_companies = {c["company"] for c in data["oppt"]["company_ratios"]}
    opp115_companies = {c["company"] for c in data["opp115"]["company_ratios"]}

    oppt_mapped = set(OPPT_INDUSTRY.keys())
    opp115_mapped = set(OPP115_INDUSTRY.keys())

    oppt_missing = oppt_companies - oppt_mapped
    opp115_missing = opp115_companies - opp115_mapped

    if oppt_missing:
        print(f"WARNING: {len(oppt_missing)} OPPT companies unmapped: {sorted(oppt_missing)}")
    if opp115_missing:
        print(f"WARNING: {len(opp115_missing)} OPP-115 companies unmapped: {sorted(opp115_missing)}")

    oppt_extra = oppt_mapped - oppt_companies
    opp115_extra = opp115_mapped - opp115_companies
    if oppt_extra:
        print(f"NOTE: {len(oppt_extra)} extra OPPT mappings (not in data): {sorted(oppt_extra)}")
    if opp115_extra:
        print(f"NOTE: {len(opp115_extra)} extra OPP-115 mappings (not in data): {sorted(opp115_extra)}")

    return len(oppt_missing) == 0 and len(opp115_missing) == 0


def get_ratio_value(ratio_raw):
    """Convert ratio from JSON (number or 'Infinity') to float."""
    if ratio_raw == "Infinity":
        return float("inf")
    return float(ratio_raw)


def compute_industry_stats(company_ratios, industry_map, corpus_label):
    """Compute per-industry statistics for one corpus."""
    # Group companies by industry
    industry_companies = defaultdict(list)
    for c in company_ratios:
        name = c["company"]
        industry = industry_map.get(name, "Other")
        ratio_val = get_ratio_value(c["ratio"])
        industry_companies[industry].append({
            "company": name,
            "practices": c["practices"],
            "commitments": c["commitments"],
            "user_control": c["user_control"],
            "total_statements": c["total_statements"],
            "ratio": ratio_val,
        })

    results = []
    for industry in SECTORS:
        companies = industry_companies.get(industry, [])
        if not companies:
            continue

        n = len(companies)
        total_practices = sum(c["practices"] for c in companies)
        total_commitments = sum(c["commitments"] for c in companies)
        total_user_control = sum(c["user_control"] for c in companies)
        total_statements = sum(c["total_statements"] for c in companies)

        # Separate finite and infinite ratios
        finite_ratios = [c["ratio"] for c in companies if not math.isinf(c["ratio"])]
        zero_commitment = sum(1 for c in companies if c["commitments"] == 0)

        if finite_ratios:
            mean_ratio = statistics.mean(finite_ratios)
            median_ratio = statistics.median(finite_ratios)
            std_ratio = statistics.stdev(finite_ratios) if len(finite_ratios) > 1 else 0.0
        else:
            mean_ratio = None
            median_ratio = None
            std_ratio = None

        # Aggregate ratio (total practices / total commitments)
        agg_ratio = total_practices / total_commitments if total_commitments > 0 else float("inf")

        results.append({
            "industry": industry,
            "n_companies": n,
            "zero_commitment_companies": zero_commitment,
            "total_practices": total_practices,
            "total_commitments": total_commitments,
            "total_user_control": total_user_control,
            "total_statements": total_statements,
            "aggregate_ratio": agg_ratio,
            "mean_ratio": mean_ratio,
            "median_ratio": median_ratio,
            "std_ratio": std_ratio,
            "companies": sorted([c["company"] for c in companies]),
        })

    # Sort by aggregate ratio descending (inf first, then by value)
    def sort_key(r):
        if r["mean_ratio"] is None:
            return (1, float("inf"))  # All-infinity → top
        return (0, -r["mean_ratio"])

    results.sort(key=sort_key)
    return results


def print_table(results, title):
    """Print a formatted table of per-industry statistics."""
    print(f"\n{'=' * 110}")
    print(f"  {title}")
    print(f"{'=' * 110}")

    header = (
        f"{'Industry':<25} {'N':>3} {'Zero-C':>6} {'Pract':>6} {'Commit':>6} "
        f"{'UsrCtl':>6} {'Agg P:C':>8} {'Mean':>7} {'Median':>7} {'Std':>7}"
    )
    print(header)
    print("-" * 110)

    for r in results:
        agg_str = f"{r['aggregate_ratio']:.1f}" if not math.isinf(r["aggregate_ratio"]) else "inf"
        mean_str = f"{r['mean_ratio']:.1f}" if r["mean_ratio"] is not None else "N/A"
        med_str = f"{r['median_ratio']:.1f}" if r["median_ratio"] is not None else "N/A"
        std_str = f"{r['std_ratio']:.1f}" if r["std_ratio"] is not None else "N/A"

        print(
            f"{r['industry']:<25} {r['n_companies']:>3} {r['zero_commitment_companies']:>6} "
            f"{r['total_practices']:>6} {r['total_commitments']:>6} {r['total_user_control']:>6} "
            f"{agg_str:>8} {mean_str:>7} {med_str:>7} {std_str:>7}"
        )

    # Totals
    total_n = sum(r["n_companies"] for r in results)
    total_zero = sum(r["zero_commitment_companies"] for r in results)
    total_prac = sum(r["total_practices"] for r in results)
    total_com = sum(r["total_commitments"] for r in results)
    total_uc = sum(r["total_user_control"] for r in results)
    agg_total = total_prac / total_com if total_com > 0 else float("inf")
    agg_total_str = f"{agg_total:.1f}" if not math.isinf(agg_total) else "inf"
    print("-" * 110)
    print(
        f"{'TOTAL':<25} {total_n:>3} {total_zero:>6} "
        f"{total_prac:>6} {total_com:>6} {total_uc:>6} "
        f"{agg_total_str:>8} {'':>7} {'':>7} {'':>7}"
    )


def print_company_detail(results, title):
    """Print which companies are in each industry."""
    print(f"\n{'─' * 80}")
    print(f"  Company Assignments: {title}")
    print(f"{'─' * 80}")
    for r in results:
        companies_str = ", ".join(r["companies"])
        print(f"  {r['industry']} ({r['n_companies']}): {companies_str}")


def combine_results(oppt_results, opp115_results):
    """Create a combined view merging both corpora."""
    # Merge by industry
    combined = {}
    for r in oppt_results + opp115_results:
        ind = r["industry"]
        if ind not in combined:
            combined[ind] = {
                "industry": ind,
                "n_companies": 0,
                "zero_commitment_companies": 0,
                "total_practices": 0,
                "total_commitments": 0,
                "total_user_control": 0,
                "total_statements": 0,
                "all_finite_ratios": [],
                "companies": [],
            }
        c = combined[ind]
        c["n_companies"] += r["n_companies"]
        c["zero_commitment_companies"] += r["zero_commitment_companies"]
        c["total_practices"] += r["total_practices"]
        c["total_commitments"] += r["total_commitments"]
        c["total_user_control"] += r["total_user_control"]
        c["total_statements"] += r["total_statements"]
        c["companies"].extend(r["companies"])

    # Now recompute aggregate stats; we need the raw finite ratios from both corpora
    # We'll recompute from the raw data instead
    return combined


def main():
    data = load_data()

    print("Phase 4: Industry Classification & Per-Industry P:C Ratio Analysis")
    print("=" * 70)

    # Validate mappings
    all_mapped = validate_mappings(data)
    if not all_mapped:
        print("\nFix unmapped companies before proceeding.")
        return

    print(f"\nOPPT companies: {len(data['oppt']['company_ratios'])}")
    print(f"OPP-115 companies: {len(data['opp115']['company_ratios'])}")

    # ── OPPT Analysis ──────────────────────────────────────────────────────
    oppt_results = compute_industry_stats(
        data["oppt"]["company_ratios"], OPPT_INDUSTRY, "OPPT"
    )
    print_table(oppt_results, "OPPT Corpus — Per-Industry P:C Ratio Statistics")
    print_company_detail(oppt_results, "OPPT")

    # ── OPP-115 Analysis ───────────────────────────────────────────────────
    opp115_results = compute_industry_stats(
        data["opp115"]["company_ratios"], OPP115_INDUSTRY, "OPP-115"
    )
    print_table(opp115_results, "OPP-115 Corpus — Per-Industry P:C Ratio Statistics")
    print_company_detail(opp115_results, "OPP-115")

    # ── Combined Analysis ──────────────────────────────────────────────────
    # Merge both corpora's company_ratios and industry maps
    all_companies = []
    combined_map = {}
    for c in data["oppt"]["company_ratios"]:
        key = f"oppt:{c['company']}"
        entry = dict(c)
        entry["company"] = key
        all_companies.append(entry)
        combined_map[key] = OPPT_INDUSTRY.get(c["company"], "Other")
    for c in data["opp115"]["company_ratios"]:
        key = f"opp115:{c['company']}"
        entry = dict(c)
        entry["company"] = key
        all_companies.append(entry)
        combined_map[key] = OPP115_INDUSTRY.get(c["company"], "Other")

    combined_results = compute_industry_stats(all_companies, combined_map, "Combined")
    print_table(combined_results, "Combined (OPPT + OPP-115) — Per-Industry P:C Ratio Statistics")

    # ── Save to JSON ───────────────────────────────────────────────────────
    def clean_for_json(results):
        """Make results JSON-serializable."""
        out = []
        for r in results:
            r2 = dict(r)
            if r2["aggregate_ratio"] == float("inf"):
                r2["aggregate_ratio"] = "Infinity"
            if r2.get("mean_ratio") is not None and math.isinf(r2["mean_ratio"]):
                r2["mean_ratio"] = "Infinity"
            out.append(r2)
        return out

    output = {
        "metadata": {
            "analysis": "Phase 4: Industry Classification & P:C Ratio by Sector",
            "source": str(INPUT_FILE.relative_to(BASE)),
            "sectors": SECTORS,
        },
        "oppt": {
            "industry_stats": clean_for_json(oppt_results),
            "company_mappings": OPPT_INDUSTRY,
        },
        "opp115": {
            "industry_stats": clean_for_json(opp115_results),
            "company_mappings": OPP115_INDUSTRY,
        },
        "combined": {
            "industry_stats": clean_for_json(combined_results),
        },
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
