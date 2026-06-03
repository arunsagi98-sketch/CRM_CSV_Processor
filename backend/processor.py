"""
Core processing logic - Python port of the n8n JS workflow.
"""
import math
import random
import re
from datetime import datetime, timezone


def safe_int(val) -> int:
    if val is None or str(val).strip() in ('', 'nan', 'NaN', 'None', 'NaT'):
        return 0
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return 0


def excel_serial_to_date_string(serial: float) -> str:
    dt = datetime.utcfromtimestamp((serial - 25569) * 86400)
    return dt.strftime("%d/%m/%Y")


def normalize_date_string(val: str) -> str:
    s = val.strip()
    m = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', s)
    if m:
        return f"{m.group(3).zfill(2)}/{m.group(2).zfill(2)}/{m.group(1)}"
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', s)
    if m:
        return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
    return s


def parse_date_field(raw) -> str:
    if raw is None or str(raw).strip() == '':
        return raw
    try:
        n = float(raw)
        if not math.isnan(n):
            return excel_serial_to_date_string(n)
    except (ValueError, TypeError):
        pass
    return normalize_date_string(str(raw))


def get_gap_range(impressions: int) -> tuple:
    if impressions < 500:
        return (1, 20)
    elif impressions <= 3000:
        return (50, 100)
    else:
        return (100, 200)


def enforce_gap(value: int, impressions: int) -> int:
    if value == 0:
        return 0
    min_gap, max_gap = get_gap_range(impressions)
    gap = value - impressions
    if -max_gap <= gap <= -min_gap:
        return value
    forced_gap = random.randint(min_gap, max_gap)
    return max(0, impressions - forced_gap)


OUTPUT_COLUMNS = [
    'Advertiser', 'Advertiser ID', 'Advertiser Currency',
    'Insertion Order', 'Insertion Order ID',
    'Line Item', 'Line Item ID',
    'Date', 'Campaign', 'Campaign ID',
    'Impressions', 'Billable Impressions',
    'Clicks', 'Click Rate (CTR)',
    'Revenue (Adv Currency)', 'Media Cost (Advertiser Currency)',
    'Start Views', '1st Quartile Views', 'Midpoint Views',
    '3rd Quartile Views', 'Complete Views', 'Video Completion Rate',
    'Viewable Impressions', 'Measurable Impressions', 'Viewability',
    'For Checking (Measurable-Impression)', 'Start Views-Impression',
]


def process_rows(rows, yesterday_memory, global_min_ctr=0.37, global_max_ctr=0.55, campaign_ctr_rules=None):
    if campaign_ctr_rules is None:
        campaign_ctr_rules = {}

    def normalize_lid(val):
        s = str(val).strip().split('|')[0].strip()
        if s.endswith('.0') and s[:-2].lstrip('-').isdigit():
            s = s[:-2]
        return s

    def find_rule(row):
        """
        Priority (most specific first):
          1. Exact Line Item ID  e.g. "LI07459"
          2. Line Item name      e.g. "MPN - Secondary - NSW - Indian - Banner"
          3. Full Line Item key  e.g. "LI07459|MPN - Secondary - NSW - Indian - Banner"
          4. Campaign name       e.g. "CA01221"
          5. Campaign ID         e.g. "CA01221" (numeric)
        """
        li_id   = normalize_lid(row.get('Line Item ID') or '').lower()
        li_name = str(row.get('Line Item') or '').strip().lower()
        li_full = f"{li_id}|{li_name}" if li_id and li_name else ''
        camp    = str(row.get('Campaign') or '').strip().lower()
        camp_id = normalize_lid(row.get('Campaign ID') or '').lower()

        for key in [li_id, li_name, li_full, camp, camp_id]:
            if key and key in campaign_ctr_rules:
                return campaign_ctr_rules[key]
        return {}

    def metric_bounds(rule, min_key, max_key, default_min=75, default_max=89):
        min_pct = rule.get(min_key)
        max_pct = rule.get(max_key)
        min_pct = default_min if min_pct is None else float(min_pct)
        max_pct = default_max if max_pct is None else float(max_pct)
        if min_pct > max_pct:
            max_pct = min_pct
        return min_pct / 100, max_pct / 100

    original_keys = list(rows[0].keys()) if rows else []
    for i, row in enumerate(rows):
        row['_originalIndex'] = i

    for row in rows:
        raw = row.get('Date')
        if raw is not None and str(raw).strip() != '':
            row['Date'] = parse_date_field(raw)

    # Step 1: CTR calculation
    for row in rows:
        impressions = safe_int(row.get('Impressions'))
        line_id = normalize_lid(row.get('Line Item ID') or '')
        rule = find_rule(row)
        min_pct = rule.get('min_ctr', global_min_ctr)
        max_pct = rule.get('max_ctr', global_max_ctr)

        if impressions <= 0:
            row['Clicks'] = 0
            row['Click Rate (CTR)'] = '0.00%'
            row['_min'] = 0
            row['_max'] = 0
            continue

        min_clicks = math.ceil((min_pct / 100) * impressions)
        max_clicks = math.floor((max_pct / 100) * impressions)

        if max_clicks < min_clicks:
            # Range too tight for this impression count — use nearest click to midpoint
            # This ensures rows with low impressions always get a click assigned
            best_click = max(1, round(((min_pct + max_pct) / 2 / 100) * impressions))
            ctr = (best_click / impressions) * 100
            row['Clicks'] = best_click
            row['Click Rate (CTR)'] = f"{ctr:.2f}%"
            row['_min'] = best_click
            row['_max'] = best_click
            continue

        prev_entries = yesterday_memory.get(line_id, [])

        def is_dupe(clicks, imp=impressions, prev=prev_entries):
            if not prev:
                return False
            this_ctr = f"{(clicks / imp * 100):.2f}%"
            return any(p['clicks'] == clicks or p['ctr'] == this_ctr for p in prev)

        selected = min_clicks
        for _ in range(100):
            selected = random.randint(min_clicks, max_clicks)
            if not is_dupe(selected):
                break

        ctr = (selected / impressions) * 100
        row['Clicks'] = selected
        row['Click Rate (CTR)'] = f"{ctr:.2f}%"
        row['_min'] = min_clicks
        row['_max'] = max_clicks

    # Step 2: Group by Line Item ID
    grouped = {}
    for row in rows:
        lid = normalize_lid(row.get('Line Item ID') or 'UNKNOWN')
        grouped.setdefault(lid, []).append(row)

    # Step 3: Remove duplicates and consecutive sequences
    for line_id, group in grouped.items():
        prev_entries = yesterday_memory.get(line_id, [])
        used_clicks = set(p['clicks'] for p in prev_entries)
        used_ctrs = set(p['ctr'] for p in prev_entries)
        last_click = None

        group.sort(key=lambda r: safe_int(r.get('Impressions')))

        for row in group:
            current_click = row['Clicks']
            mn = row['_min']
            mx = row['_max']
            impressions = safe_int(row.get('Impressions'))

            if mn == 0 and mx == 0:
                used_clicks.add(current_click)
                last_click = current_click
                continue

            current_ctr = f"{(current_click / impressions * 100):.2f}%" if impressions > 0 else '0.00%'
            needs_change = (
                current_click in used_clicks
                or current_ctr in used_ctrs
                or (last_click is not None and abs(current_click - last_click) == 1)
            )

            if needs_change:
                new_click = current_click
                new_ctr = current_ctr
                for _ in range(100):
                    new_click = random.randint(mn, mx)
                    new_ctr = f"{(new_click / impressions * 100):.2f}%" if impressions > 0 else '0.00%'
                    if (
                        new_click not in used_clicks
                        and new_ctr not in used_ctrs
                        and (last_click is None or abs(new_click - last_click) != 1)
                    ):
                        break
                current_click = new_click
                row['Clicks'] = current_click
                row['Click Rate (CTR)'] = f"{(current_click / impressions * 100):.2f}%" if impressions > 0 else '0.00%'

            used_clicks.add(current_click)
            used_ctrs.add(f"{(current_click / impressions * 100):.2f}%" if impressions > 0 else '0.00%')
            last_click = current_click

    rows.sort(key=lambda r: r['_originalIndex'])

    for row in rows:
        for key in original_keys:
            if key not in row:
                row[key] = ''

    for row in rows:
        row.pop('_min', None)
        row.pop('_max', None)
        row.pop('_originalIndex', None)

    today_snapshot = {}
    for row in rows:
        lid = normalize_lid(row.get('Line Item ID') or '')
        if not lid:
            continue
        clicks = safe_int(row.get('Clicks'))
        ctr = str(row.get('Click Rate (CTR)') or '').strip()
        today_snapshot.setdefault(lid, []).append({'clicks': clicks, 'ctr': ctr})

    for row in rows:
        row['_originalSV'] = safe_int(row.get('Start Views'))

    for row in rows:
        rule = find_rule(row)
        vcr_min, vcr_max = metric_bounds(rule, 'min_vcr', 'max_vcr')
        view_min, view_max = metric_bounds(rule, 'min_viewability', 'max_viewability')
        impressions = safe_int(row.get('Impressions'))
        row.setdefault('Video Completion Rate', '0.00%')
        row.setdefault('Viewability', '0.00%')

        start_views = safe_int(row.get('Start Views'))
        complete_views = safe_int(row.get('Complete Views'))

        if start_views == 0:
            row['Video Completion Rate'] = '0.00%'
        else:
            start_views = enforce_gap(start_views, impressions)
            row['Start Views'] = start_views
            vcr = complete_views / start_views if start_views > 0 else 0
            if not (vcr_min <= vcr <= vcr_max):
                min_gap, max_gap = get_gap_range(impressions)
                sv_min = max(1, impressions - max_gap)
                sv_max = max(1, impressions - min_gap)
                new_sv = start_views
                if sv_max >= sv_min and impressions > 0:
                    new_sv = random.randint(sv_min, sv_max)
                cv_min = math.ceil(vcr_min * new_sv)
                cv_max = math.floor(vcr_max * new_sv)
                new_cv = complete_views
                if cv_max >= cv_min:
                    new_cv = random.randint(cv_min, cv_max)
                else:
                    new_cv = max(0, round(((vcr_min + vcr_max) / 2) * new_sv))
                row['Start Views'] = new_sv
                row['Complete Views'] = new_cv
                start_views = new_sv
                complete_views = new_cv
            final_vcr = (complete_views / start_views * 100) if start_views > 0 else 0
            row['Video Completion Rate'] = f"{final_vcr:.2f}%"

        measurable = safe_int(row.get('Measurable Impressions'))
        viewable = safe_int(row.get('Viewable Impressions'))
        measurable = enforce_gap(measurable, impressions)
        row['Measurable Impressions'] = measurable

        viewability = viewable / measurable if measurable > 0 else 0
        if measurable > 0 and not (view_min <= viewability <= view_max):
            min_gap, max_gap = get_gap_range(impressions)
            mi_min = max(1, impressions - max_gap)
            mi_max = max(1, impressions - min_gap)
            new_m = measurable
            if mi_max >= mi_min and impressions > 0:
                new_m = random.randint(mi_min, mi_max)
            vi_min = math.ceil(view_min * new_m)
            vi_max = math.floor(view_max * new_m)
            new_v = viewable
            if vi_max >= vi_min:
                new_v = random.randint(vi_min, vi_max)
            else:
                new_v = max(0, round(((view_min + view_max) / 2) * new_m))
            row['Measurable Impressions'] = new_m
            row['Viewable Impressions'] = new_v
            measurable = new_m
            viewable = new_v

        final_view = (viewable / measurable * 100) if measurable > 0 else 0
        row['Viewability'] = f"{final_view:.2f}%"

    output = []
    for row in rows:
        impressions = safe_int(row.get('Impressions'))
        measurable_after = safe_int(row.get('Measurable Impressions'))
        start_after = safe_int(row.get('Start Views'))
        original_sv = safe_int(row.get('_originalSV'))

        row['For Checking (Measurable-Impression)'] = (
            0 if measurable_after == 0 else measurable_after - impressions
        )

        sv_diff = 0
        if original_sv != 0 and impressions != 0:
            sv_diff = start_after - impressions
        row['Start Views-Impression'] = sv_diff
        row.pop('_originalSV', None)

        new_row = {}
        for col in OUTPUT_COLUMNS:
            if col == 'Date':
                val = row.get(col)
                new_row[col] = str(val) if val is not None else None
            else:
                val = row.get(col, None)
                if isinstance(val, str):
                    val = val.strip()
                new_row[col] = val
        output.append(new_row)

    return output, today_snapshot
