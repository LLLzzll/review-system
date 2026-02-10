import random
import pandas as pd

from datetime import date, datetime, timedelta

import streamlit as st
from streamlit_echarts import JsCode, st_echarts


def render_panel_title(title, subtitle=None):
    if subtitle:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
              <div style="font-size:16px; font-weight:800;">{title}</div>
              <div style="font-size:12px; color:#999999;">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="font-size:16px; font-weight:800; text-align:left;">{title}</div>
            """,
            unsafe_allow_html=True,
        )


def build_bar_option(title, categories, values, colors=None, show_title=True):
    if colors is None:
        colors = ["#5470C6"] * len(values)
    option = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "xAxis": {"type": "category", "data": categories, "axisLabel": {"interval": 0}},
        "yAxis": {"type": "value"},
        "grid": {"left": 40, "right": 10, "top": 40, "bottom": 30},
        "series": [
            {
                "type": "bar",
                "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(values, colors)],
                "barWidth": "60%",
                "label": {"show": True, "position": "top", "color": "#111827", "fontSize": 11},
            }
        ],
    }
    if show_title:
        option["title"] = {"text": title, "left": "center", "textStyle": {"fontSize": 14}}
    return option


def generate_distribution_data(seed_text):
    random.seed(seed_text)
    buckets = [
        "涨停",
        ">10%",
        "8%",
        "6%",
        "4%",
        "2%",
        "0%",
        "-2%",
        "-4%",
        "-6%",
        "-8%",
        "<-10%",
        "跌停",
    ]
    values = [random.randint(10, 220) for _ in buckets]
    colors = []
    for name in buckets:
        if name in ("涨停", ">10%", "8%", "6%", "4%", "2%"):
            colors.append("#E94B3C")
        elif name in ("跌停", "<-10%", "-8%", "-6%", "-4%", "-2%"):
            colors.append("#2EBD85")
        else:
            colors.append("#999999")
    random.seed()
    return buckets, values, colors


@st.cache_data(ttl=3600)
def generate_stock_distribution_stats(seed_text):
    rnd = random.Random(str(seed_text))
    u = rnd.randint(800, 4200)
    d = rnd.randint(800, 4200)
    flat = rnd.randint(50, 300)
    halt = rnd.randint(10, 80)
    limit_up = rnd.randint(0, 120)
    limit_down = rnd.randint(0, 80)
    return u, d, flat, halt, limit_up, limit_down


def calc_step_return_series(prices):
    values = []
    prev = None
    for p in prices or []:
        try:
            v = float(p)
        except Exception:
            v = None
        if v is None:
            values.append(None)
            continue
        if prev is None or not prev:
            values.append(None)
            prev = v
            continue
        values.append((v / prev - 1) * 100)
        prev = v
    return values


def rolling_sum_series(values, window):
    try:
        window = int(window or 1)
    except Exception:
        window = 1
    window = max(1, window)

    out = []
    seq = values or []
    for i in range(len(seq)):
        s = 0.0
        count = 0
        start = max(0, i - window + 1)
        for j in range(start, i + 1):
            v = seq[j]
            if v is None:
                continue
            try:
                s += float(v)
                count += 1
            except Exception:
                continue
        out.append(s if count else None)
    return out


def format_day_label(x, start_dt=None):
    if x is None:
        return None
    if isinstance(x, int):
        text = str(x)
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:]}"
        if start_dt is not None and 0 <= x < 10000:
            try:
                return (start_dt + timedelta(days=x)).isoformat()
            except Exception:
                return text
        return text
    text = str(x).strip()
    if "/" in text:
        base = text.split(" ", 1)[0].split("T", 1)[0].strip()
        if len(base) == 10 and base[4] == "/" and base[7] == "/":
            text = base.replace("/", "-")
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if " " in text:
        return text.split(" ", 1)[0]
    if "T" in text:
        return text.split("T", 1)[0]
    return text


def normalize_minute_key(x, start_dt=None):
    if x is None:
        return None
    if isinstance(x, int):
        return str(x)
    text = str(x).strip()
    if "\n" in text:
        parts = text.split("\n")
        if len(parts) >= 2 and "-" in parts[0] and ":" in parts[1]:
            return f"{parts[0]} {parts[1][:5]}"
    if " " in text and "-" in text and ":" in text:
        parts = text.split(" ", 1)
        if len(parts) == 2:
            return f"{parts[0]} {parts[1][:5]}"
    if "T" in text and "-" in text and ":" in text:
        parts = text.split("T", 1)
        if len(parts) == 2:
            time_part = parts[1].split(".", 1)[0]
            return f"{parts[0]} {time_part[:5]}"
    if ":" in text and start_dt is not None:
        return f"{start_dt.isoformat()} {text[:5]}"
    return text


def format_minute_label(key_text):
    if key_text is None:
        return None
    text = str(key_text)
    if " " in text and "-" in text and ":" in text:
        parts = text.split(" ", 1)
        if len(parts) == 2:
            return f"{parts[0]}\n{parts[1]}"
    return text


def extract_label_date(x):
    if x is None:
        return None
    text = str(x).strip()
    if not text:
        return None
    if "\n" in text:
        text = text.split("\n", 1)[0].strip()
    if "T" in text:
        text = text.split("T", 1)[0].strip()
    if " " in text and "-" in text:
        text = text.split(" ", 1)[0].strip()
    if "/" in text and len(text) == 10 and text[4] == "/" and text[7] == "/":
        text = text.replace("/", "-")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return None


def build_trading_dates(start_dt, end_dt):
    out = []
    if start_dt is None or end_dt is None:
        return out
    if start_dt > end_dt:
        return out
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:
            out.append(current.isoformat())
        current = current + timedelta(days=1)
    return out


def align_series_by_x(x1, y1, x2, y2, key_func=None, label_func=None):
    m2 = {}
    for x, v in zip(x2 or [], y2 or []):
        k = key_func(x) if key_func else x
        if k is None:
            continue
        if k not in m2:
            m2[k] = v
    aligned_x = []
    aligned_y1 = []
    aligned_y2 = []
    for x, v1 in zip(x1 or [], y1 or []):
        k = key_func(x) if key_func else x
        if k is None:
            continue
        if k in m2:
            aligned_x.append(label_func(k) if label_func else x)
            aligned_y1.append(v1)
            aligned_y2.append(m2[k])
    return aligned_x, aligned_y1, aligned_y2


def decide_size_style(diff_series, threshold=0.3):
    if not diff_series:
        return "未知"
    last = None
    for v in reversed(diff_series):
        if v is not None:
            last = v
            break
    if last is None:
        return "未知"
    if last >= threshold:
        return "小盘风格"
    if last <= -threshold:
        return "大盘风格"
    return "均衡"


def build_size_style_option(x_data, diff_ret, threshold):
    threshold_up_color = "#EF4444"
    threshold_mid_color = "#6B7280"
    threshold_down_color = "#22C55E"
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"show": False},
        "grid": {"left": 48, "right": 44, "top": 20, "bottom": 34},
        "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}%"}},
        "series": [
            {
                "name": "强度",
                "type": "line",
                "data": diff_ret,
                "smooth": True,
                "connectNulls": True,
                "showSymbol": False,
                "lineStyle": {"width": 2, "color": "#10B981"},
                "markLine": {
                    "symbol": "none",
                    "label": {"show": False},
                    "data": [
                        {
                            "yAxis": float(threshold),
                            "lineStyle": {"type": "dashed", "width": 1, "color": threshold_up_color},
                        },
                        {
                            "yAxis": 0,
                            "lineStyle": {"type": "dashed", "width": 1, "color": threshold_mid_color},
                        },
                        {
                            "yAxis": float(-threshold),
                            "lineStyle": {"type": "dashed", "width": 1, "color": threshold_down_color},
                        },
                    ],
                },
            },
        ],
    }


def render_size_style_legend(threshold):
    threshold_text = f"{float(threshold):.2f}%"
    items = [
        ("#EF4444", "dashed", f"小盘风格阈值(+{threshold_text})"),
        ("#6B7280", "solid", "均衡线(0)"),
        ("#22C55E", "dashed", f"大盘风格阈值(-{threshold_text})"),
    ]
    parts = []
    for color, line_style, label in items:
        parts.append(
            f'<div style="display:flex;align-items:center;gap:6px;white-space:nowrap;">'
            f'<span style="width:16px;height:0;border-top:2px {line_style} {color};display:inline-block;"></span>'
            f'<span style="font-size:12px;color:#111827;">{label}</span>'
            f"</div>"
        )
    html = "".join(parts)
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:14px;margin:6px 0 2px 0;">{html}</div>',
        unsafe_allow_html=True,
    )


def render_size_style_trend(ctx):
    fetch_index_day_list = ctx["fetch_index_day_list"]
    fetch_index_min_list = ctx["fetch_index_min_list"]
    generate_period_series = ctx["generate_period_series"]
    get_refresh_token = ctx["get_refresh_token"]
    parse_indicator_day_series = ctx["parse_indicator_day_series"]
    parse_index_min_series = ctx["parse_index_min_series"]

    st.markdown(
        '<div style="text-align:center;font-size:22px;font-weight:800;color:#111827;line-height:22px;">大小风格趋势</div>',
        unsafe_allow_html=True,
    )

    controls = st.columns(3)
    with controls[0]:
        period = st.selectbox(
            "周期",
            ["1分钟", "5分钟", "30分钟", "60分钟", "日线"],
            index=0,
            key="size_style_period",
            label_visibility="collapsed",
        )
    with controls[1]:
        start_dt = st.date_input(
            "开始",
            value=st.session_state.get("size_style_start") or date.today(),
            key="size_style_start",
            label_visibility="collapsed",
        )
    with controls[2]:
        end_dt = st.date_input(
            "结束",
            value=st.session_state.get("size_style_end") or date.today(),
            key="size_style_end",
            label_visibility="collapsed",
        )
    prefetch_start_dt = start_dt - timedelta(days=7)

    large_exponent_id = 3
    small_exponent_id = 12

    x_large = []
    y_large = []
    x_small = []
    y_small = []

    has_token = bool(get_refresh_token())
    try:
        if period == "日线":
            if has_token:
                large_list = fetch_index_day_list(
                    prefetch_start_dt.isoformat(), end_dt.isoformat(), str(large_exponent_id), "close"
                )
                small_list = fetch_index_day_list(
                    prefetch_start_dt.isoformat(), end_dt.isoformat(), str(small_exponent_id), "close"
                )
                x_large, y_large = parse_indicator_day_series(
                    large_list, ["close", "closePrice", "price"], start_dt=prefetch_start_dt
                )
                x_small, y_small = parse_indicator_day_series(
                    small_list, ["close", "closePrice", "price"], start_dt=prefetch_start_dt
                )
            else:
                x_large, y_large = generate_period_series(
                    "60分钟",
                    start_dt=start_dt,
                    base=4200,
                    fluctuation=20,
                    seed_text=f"size_style|large|60|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
                x_small, y_small = generate_period_series(
                    "60分钟",
                    start_dt=start_dt,
                    base=6200,
                    fluctuation=25,
                    seed_text=f"size_style|small|60|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
        else:
            period_int = {"1分钟": 1, "5分钟": 5, "30分钟": 30, "60分钟": 60}.get(period, 5)
            if has_token:
                field_list = "time,close"
                large_list = fetch_index_min_list(
                    prefetch_start_dt.isoformat(), end_dt.isoformat(), large_exponent_id, period_int, field_list
                )
                small_list = fetch_index_min_list(
                    prefetch_start_dt.isoformat(), end_dt.isoformat(), small_exponent_id, period_int, field_list
                )
                x_large, y_large = parse_index_min_series(
                    large_list, start_dt=prefetch_start_dt, period_minutes=period_int
                )
                x_small, y_small = parse_index_min_series(
                    small_list, start_dt=prefetch_start_dt, period_minutes=period_int
                )
            else:
                x_large, y_large = generate_period_series(
                    period,
                    start_dt=start_dt,
                    base=4200,
                    fluctuation=20,
                    seed_text=f"size_style|large|{period}|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
                x_small, y_small = generate_period_series(
                    period,
                    start_dt=start_dt,
                    base=6200,
                    fluctuation=25,
                    seed_text=f"size_style|small|{period}|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
    except Exception:
        x_large, y_large = generate_period_series(
            "5分钟",
            start_dt=start_dt,
            base=4200,
            fluctuation=20,
            seed_text=f"size_style|large|5|{start_dt.isoformat()}|{end_dt.isoformat()}",
        )
        x_small, y_small = generate_period_series(
            "5分钟",
            start_dt=start_dt,
            base=6200,
            fluctuation=25,
            seed_text=f"size_style|small|5|{start_dt.isoformat()}|{end_dt.isoformat()}",
        )

    if period == "日线":
        x_large = [format_day_label(v, start_dt=prefetch_start_dt) for v in (x_large or [])]
        x_small = [format_day_label(v, start_dt=prefetch_start_dt) for v in (x_small or [])]

    if period == "日线":
        x_data, large_price, small_price = align_series_by_x(
            x_large,
            y_large,
            x_small,
            y_small,
            key_func=lambda v: format_day_label(v, start_dt=prefetch_start_dt),
            label_func=lambda k: k,
        )
    else:
        x_data, large_price, small_price = align_series_by_x(
            x_large,
            y_large,
            x_small,
            y_small,
            key_func=normalize_minute_key,
            label_func=format_minute_label,
        )
    if not x_data and x_large and x_small and y_large and y_small:
        n = min(len(x_large), len(x_small), len(y_large), len(y_small))
        if n > 0:
            x_data = x_large[:n]
            large_price = y_large[:n]
            small_price = y_small[:n]
    large_step = calc_step_return_series(large_price)
    small_step = calc_step_return_series(small_price)
    diff_step = []
    for a, b in zip(small_step, large_step):
        if a is None or b is None:
            diff_step.append(None)
        else:
            diff_step.append(a - b)
    if period == "日线":
        window = 3
    elif period == "30分钟" or period == "60分钟":
        window = 5
    else:
        window = 10
    diff_ret = rolling_sum_series(diff_step, window)
 
    threshold = 0.3
    start_key = start_dt.isoformat()
    end_key = end_dt.isoformat()
    keep_idx = []
    for i, x in enumerate(x_data or []):
        d = extract_label_date(x)
        if d is None or (d >= start_key and d <= end_key):
            keep_idx.append(i)
    if keep_idx and len(keep_idx) != len(x_data or []):
        x_data = [x_data[i] for i in keep_idx]
        diff_ret = [diff_ret[i] for i in keep_idx]

    if period == "日线":
        expected_dates = build_trading_dates(start_dt, end_dt)
        if expected_dates:
            m = {}
            for x, v in zip(x_data or [], diff_ret or []):
                d = extract_label_date(x)
                if d is not None and d not in m:
                    m[d] = v
            x_data = expected_dates
            diff_ret = [m.get(d) for d in expected_dates]

    style = decide_size_style(diff_ret, threshold=threshold)
    last_diff = None
    for v in reversed(diff_ret):
        if v is not None:
            last_diff = v
            break
    diff_text = "--" if last_diff is None else f"{last_diff:+.4f}%"
    st.markdown(
        f'<div style="color:#111827;font-size:12px;margin-top:2px;">当前风格：{style}（滚动{window}期 强度：{diff_text}）</div>',
        unsafe_allow_html=True,
    )

    diff_ret_display = []
    for v in diff_ret:
        if v is None:
            diff_ret_display.append(None)
        else:
            try:
                diff_ret_display.append(f"{float(v):.4f}")
            except Exception:
                diff_ret_display.append(None)

    render_size_style_legend(threshold)
    option = build_size_style_option(x_data, diff_ret_display, threshold)
    st_echarts(option, height="170px", key="size_style_chart")


def render_monitor_overview(ctx):
    row = st.columns(3)

    with row[0]:
        with st.container(border=True):
            st.markdown(
                """
                <div style="height:320px; display:flex; align-items:center; justify-content:center;">
                  <div style="font-size:22px; font-weight:800; color:#666666; text-align:center;">
                    价格追踪与当日趋势预测
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with row[1]:
        with st.container(border=True):
            st.markdown(
                """
                <div style="height:320px; display:flex; align-items:center; justify-content:center;">
                  <div style="font-size:22px; font-weight:800; color:#666666; text-align:center;">
                    成交量能变动
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with row[2]:
        with st.container(border=True):
            render_size_style_trend(ctx)


def get_first_value(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None


def get_trading_minutes_of_day(period_minutes):
    try:
        step = int(period_minutes or 1)
    except Exception:
        step = 1
    step = max(1, step)

    if step == 1:
        morning_start = 9 * 60 + 30
    else:
        morning_start = 9 * 60 + 30 + step
    morning_end = 11 * 60 + 30 
    afternoon_start = 13 * 60 + step
    afternoon_end = 15 * 60

    minutes = list(range(morning_start, morning_end + 1, step))
    minutes.extend(range(afternoon_start, afternoon_end + 1, step))
    return minutes


def add_trading_days(start_dt, trading_days):
    if start_dt is None:
        return None
    try:
        days = int(trading_days or 0)
    except Exception:
        days = 0
    if days < 0:
        days = 0

    current = start_dt
    while current.weekday() >= 5:
        current = current + timedelta(days=1)

    for _ in range(days):
        current = current + timedelta(days=1)
        while current.weekday() >= 5:
            current = current + timedelta(days=1)
    return current


def format_minute_x(x_val, start_dt=None):
    if x_val is None:
        return None
    text = str(x_val).strip()
    if not text:
        return None

    if " " in text and ":" in text:
        d, t = text.split(" ", 1)
        t = t.split(".", 1)[0].strip()
        if len(t) >= 5:
            t = t[:5]
        return f"{d}\n{t}"
    if "T" in text and "-" in text and ":" in text:
        d, t = text.split("T", 1)
        t = t.split(".", 1)[0].strip()
        if len(t) >= 5:
            t = t[:5]
        return f"{d}\n{t}"
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if len(text) == 6 and text.isdigit():
        hh = text[:2]
        mm = text[2:4]
        return f"{start_dt.isoformat() if start_dt else ''}\n{hh}:{mm}".strip()
    if len(text) == 4 and text.isdigit():
        hh = text[:2]
        mm = text[2:]
        return f"{start_dt.isoformat() if start_dt else ''}\n{hh}:{mm}".strip()
    if ":" in text and start_dt is not None and "-" not in text and "\n" not in text:
        return f"{start_dt.isoformat()}\n{text[:5]}"
    return text.replace(" ", "\n")


def parse_index_min_ohlc(data_list, start_dt=None, period_minutes=None):
    x_data = []
    close_data = []
    high_data = []
    low_data = []

    trading_minutes = None
    if start_dt is not None and period_minutes:
        trading_minutes = get_trading_minutes_of_day(period_minutes)
        if not trading_minutes:
            trading_minutes = None

    for idx, item in enumerate(data_list or []):
        if not isinstance(item, dict):
            continue

        x_val = get_first_value(
            item,
            [
                "time",
                "dateTime",
                "datetime",
                "tradeDateTime",
                "tradeDatetime",
                "tradeTime",
                "tradeDate",
                "date",
            ],
        )
        x_text = format_minute_x(x_val, start_dt=start_dt)
        if x_text is None and start_dt is not None and trading_minutes is not None:
            try:
                day_offset = idx // len(trading_minutes)
                minute_of_day = trading_minutes[idx % len(trading_minutes)]
                trading_date = add_trading_days(start_dt, day_offset) or start_dt
                ts = datetime.combine(trading_date, datetime.min.time()) + timedelta(minutes=minute_of_day)
                x_text = ts.strftime("%Y-%m-%d\n%H:%M")
            except Exception:
                x_text = None
        if x_text is None:
            x_text = str(idx)

        close_val = get_first_value(item, ["close", "closePrice", "close_price", "price", "last"])
        if close_val is None:
            continue
        high_val = get_first_value(item, ["high", "highPrice", "high_price"])
        low_val = get_first_value(item, ["low", "lowPrice", "low_price"])

        try:
            close_f = float(close_val)
        except Exception:
            continue
        try:
            high_f = float(high_val) if high_val is not None else close_f
        except Exception:
            high_f = close_f
        try:
            low_f = float(low_val) if low_val is not None else close_f
        except Exception:
            low_f = close_f

        x_data.append(x_text)
        close_data.append(close_f)
        high_data.append(high_f)
        low_data.append(low_f)
    return x_data, close_data, high_data, low_data


def parse_index_day_ohlc(data_list, start_dt=None):
    x_data = []
    close_data = []
    high_data = []
    low_data = []

    for idx, item in enumerate(data_list or []):
        if not isinstance(item, dict):
            continue

        x_val = get_first_value(
            item,
            [
                "tradeDate",
                "trade_date",
                "date",
                "datetime",
                "dateTime",
                "time",
                "tradeTime",
            ],
        )
        if x_val is None and start_dt is not None:
            try:
                x_val = (add_trading_days(start_dt, idx) or start_dt).isoformat()
            except Exception:
                x_val = idx
        x_text = format_day_label(x_val, start_dt=start_dt)
        if x_text is None:
            x_text = str(idx)

        close_val = get_first_value(item, ["close", "closePrice", "close_price", "price", "last"])
        if close_val is None:
            continue
        high_val = get_first_value(item, ["high", "highPrice", "high_price"])
        low_val = get_first_value(item, ["low", "lowPrice", "low_price"])

        try:
            close_f = float(close_val)
        except Exception:
            continue
        try:
            high_f = float(high_val) if high_val is not None else close_f
        except Exception:
            high_f = close_f
        try:
            low_f = float(low_val) if low_val is not None else close_f
        except Exception:
            low_f = close_f

        x_data.append(x_text)
        close_data.append(close_f)
        high_data.append(high_f)
        low_data.append(low_f)

    rows = list(zip(x_data, close_data, high_data, low_data))
    rows.sort(key=lambda r: extract_label_date(r[0]) or str(r[0]))
    if rows:
        x_data, close_data, high_data, low_data = map(list, zip(*rows))

    return x_data, close_data, high_data, low_data


def ema_series(values, period):
    try:
        period = int(period or 1)
    except Exception:
        period = 1
    period = max(1, period)
    alpha = 2.0 / (period + 1.0)
    out = []
    ema = None
    for v in values or []:
        if v is None:
            out.append(None)
            continue
        try:
            x = float(v)
        except Exception:
            out.append(None)
            continue
        if ema is None:
            ema = x
        else:
            ema = alpha * x + (1 - alpha) * ema
        out.append(ema)
    return out


def macd_series(close, fast=12, slow=26, signal=9):
    fast_ema = ema_series(close, fast)
    slow_ema = ema_series(close, slow)
    dif = []
    for a, b in zip(fast_ema, slow_ema):
        if a is None or b is None:
            dif.append(None)
        else:
            dif.append(a - b)
    dea = ema_series(dif, signal)
    hist = []
    for d, s in zip(dif, dea):
        if d is None or s is None:
            hist.append(None)
        else:
            hist.append((d - s) * 2)
    return dif, dea, hist


def rsi_series(close, period=14):
    try:
        period = int(period or 14)
    except Exception:
        period = 14
    period = max(1, period)

    rsis = []
    avg_gain = None
    avg_loss = None
    prev = None
    for i, v in enumerate(close or []):
        if v is None:
            rsis.append(None)
            prev = None
            continue
        try:
            price = float(v)
        except Exception:
            rsis.append(None)
            prev = None
            continue
        if prev is None:
            rsis.append(None)
            prev = price
            continue
        change = price - prev
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        if avg_gain is None:
            avg_gain = gain
            avg_loss = loss
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if i < period:
            rsis.append(None)
        else:
            if avg_loss == 0:
                rsis.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsis.append(100.0 - 100.0 / (1.0 + rs))
        prev = price
    return rsis


def kdj_series(high, low, close, period=9):
    try:
        period = int(period or 9)
    except Exception:
        period = 9
    period = max(1, period)

    k = []
    d = []
    j = []
    last_k = 50.0
    last_d = 50.0
    for i in range(len(close or [])):
        h_window = []
        l_window = []
        start = max(0, i - period + 1)
        for t in range(start, i + 1):
            hv = high[t] if t < len(high or []) else None
            lv = low[t] if t < len(low or []) else None
            if hv is not None:
                try:
                    h_window.append(float(hv))
                except Exception:
                    pass
            if lv is not None:
                try:
                    l_window.append(float(lv))
                except Exception:
                    pass
        c = close[i]
        try:
            c = float(c)
        except Exception:
            k.append(None)
            d.append(None)
            j.append(None)
            continue
        if not h_window or not l_window:
            rsv = 50.0
        else:
            hh = max(h_window)
            ll = min(l_window)
            if hh == ll:
                rsv = 50.0
            else:
                rsv = (c - ll) / (hh - ll) * 100.0
        last_k = last_k * 2 / 3 + rsv / 3
        last_d = last_d * 2 / 3 + last_k / 3
        last_j = 3 * last_k - 2 * last_d
        k.append(last_k)
        d.append(last_d)
        j.append(last_j)
    return k, d, j


def find_pivots(values, window, kind):
    try:
        window = int(window or 3)
    except Exception:
        window = 3
    window = max(1, window)

    pivots = []
    seq = values or []
    for i in range(window, len(seq) - window):
        v = seq[i]
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        left = seq[i - window : i]
        right = seq[i + 1 : i + 1 + window]
        left_vals = []
        right_vals = []
        for t in left:
            if t is None:
                continue
            try:
                left_vals.append(float(t))
            except Exception:
                continue
        for t in right:
            if t is None:
                continue
            try:
                right_vals.append(float(t))
            except Exception:
                continue
        if not left_vals or not right_vals:
            continue
        if kind == "high":
            if v > max(left_vals) and v > max(right_vals):
                pivots.append(i)
        else:
            if v < min(left_vals) and v < min(right_vals):
                pivots.append(i)
    return pivots


def detect_divergence(price, indicator, x_data, pivot_window=3, max_bars=200):
    highs = find_pivots(price, pivot_window, "high")
    lows = find_pivots(price, pivot_window, "low")

    signals = []
    for pivots, kind in ((highs, "bearish"), (lows, "bullish")):
        prev = None
        for idx in pivots:
            if prev is None:
                prev = idx
                continue
            if idx - prev > max_bars:
                prev = idx
                continue
            p1 = price[prev]
            p2 = price[idx]
            i1 = indicator[prev] if prev < len(indicator or []) else None
            i2 = indicator[idx] if idx < len(indicator or []) else None
            if p1 is None or p2 is None or i1 is None or i2 is None:
                prev = idx
                continue
            try:
                p1 = float(p1)
                p2 = float(p2)
                i1 = float(i1)
                i2 = float(i2)
            except Exception:
                prev = idx
                continue
            if kind == "bearish":
                if p2 > p1 and i2 < i1:
                    signals.append(
                        {
                            "kind": "顶背离",
                            "x": x_data[idx] if idx < len(x_data or []) else str(idx),
                            "price": p2,
                            "indicator": i2,
                            "idx": idx,
                        }
                    )
            else:
                if p2 < p1 and i2 > i1:
                    signals.append(
                        {
                            "kind": "底背离",
                            "x": x_data[idx] if idx < len(x_data or []) else str(idx),
                            "price": p2,
                            "indicator": i2,
                            "idx": idx,
                        }
                    )
            prev = idx
    signals.sort(key=lambda s: s.get("idx", 0))
    return signals


@st.cache_data(ttl=300)
def compute_divergence_payload(x_data, close, high, low):
    dif, dea, hist = macd_series(close)
    k, d, j = kdj_series(high, low, close)
    rsi = rsi_series(close)
    macd_signals = detect_divergence(close, dif, x_data)
    for s in macd_signals:
        s["source"] = "MACD"
    kdj_signals = detect_divergence(close, j, x_data)
    for s in kdj_signals:
        s["source"] = "KDJ"
    rsi_signals = detect_divergence(close, rsi, x_data)
    for s in rsi_signals:
        s["source"] = "RSI"
    return {
        "close": close,
        "macd": {"dif": dif, "dea": dea, "hist": hist, "signals": macd_signals},
        "kdj": {"k": k, "d": d, "j": j, "signals": kdj_signals},
        "rsi": {"rsi": rsi, "signals": rsi_signals},
    }


def build_divergence_option(x_data, close, hidden_indicator_series, scatter_series, period_text, legend_items):
    formatter = JsCode(
        "function (params) { if (!params || !params.length) { return ''; } var axisLabel = params[0].axisValueLabel || params[0].axisValue || ''; var signal = '无'; var close = null; var lines = [axisLabel]; for (var i = 0; i < params.length; i++) { var p = params[i]; if (!p) continue; if (p.seriesName === '背离信号') { if (p.data && p.data.signal) { signal = p.data.signal; } continue; } if (p.seriesName === '价格') { close = p.value; } } lines.push('背离信号：' + (signal || '无')); if (close !== null && close !== undefined && close !== '') { lines.push('价格 ' + close); } for (var i = 0; i < params.length; i++) { var p = params[i]; if (!p) continue; if (p.seriesName === '价格' || p.seriesName === '背离信号') continue; if (p.value === null || typeof p.value === 'undefined') continue; lines.push(p.seriesName + ' ' + p.value); } return lines.join('<br/>'); }"
    ).js_code
    return {
        "tooltip": {"trigger": "axis", "formatter": formatter},
        "legend": {"top": 0, "data": legend_items or [], "selectedMode": False},
        "grid": {"left": 48, "right": 18, "top": 44, "bottom": 30, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "boundaryGap": False,
            "axisLabel": {"hideOverlap": True, "showMinLabel": True, "showMaxLabel": True},
            "axisLine": {"onZero": False},
        },
        "yAxis": [
            {"type": "value", "scale": True},
            {"type": "value", "scale": True, "show": False},
        ],
        "series": [
            {
                "name": "价格",
                "type": "line",
                "data": close,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 2, "color": "#2563EB"},
            },
        ]
        + (hidden_indicator_series or [])
        + (scatter_series or []),
    }


def render_divergence_signal(ctx):
    with st.container(border=True):
        header = st.columns([2.2, 1.5, 1.5, 1.5, 1.8])
        with header[0]:
            render_panel_title("背离信号")
        with header[1]:
            start_dt = st.date_input(
                "开始",
                value=st.session_state.get("divergence_start") or (date.today() - timedelta(days=2)),
                key="divergence_start",
                label_visibility="collapsed",
            )
        with header[2]:
            end_dt = st.date_input(
                "结束",
                value=st.session_state.get("divergence_end") or date.today(),
                key="divergence_end",
                label_visibility="collapsed",
            )
        with header[3]:
            period = st.selectbox(
                "周期",
                ["1分钟", "5分钟", "30分钟", "60分钟", "日线"],
                key="divergence_period",
                label_visibility="collapsed",
            )
        with header[4]:
            index_name = st.selectbox(
                "指数",
                ["上证指数", "深证综指", "沪深300", "创业板指", "科创50", "中证1000"],
                key="divergence_index",
                label_visibility="collapsed",
            )

        c1, c2, c3 = st.columns(3)
        with c1:
            show_macd = st.checkbox("MACD背离", value=True, key="divergence_show_macd")
        with c2:
            show_kdj = st.checkbox("KDJ背离", value=True, key="divergence_show_kdj")
        with c3:
            show_rsi = st.checkbox("RSI背离", value=True, key="divergence_show_rsi")

        if start_dt and end_dt and start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        period_int = {"1分钟": 1, "5分钟": 5, "30分钟": 30, "60分钟": 60}.get(period, 5)

        fetch_index_min_list = ctx["fetch_index_min_list"]
        fetch_index_day_list = ctx["fetch_index_day_list"]
        generate_random_series = ctx["generate_random_series"]
        generate_period_series = ctx["generate_period_series"]
        get_refresh_token = ctx["get_refresh_token"]
        index_min_map = ctx["INDEX_MIN_MAP"]
        parse_indicator_day_series = ctx["parse_indicator_day_series"]

        cfg = index_min_map.get(index_name)
        has_token = bool(get_refresh_token()) and bool(cfg)
        day_mode = period == "日线"
        calc_x_full = None
        day_end_dt = None
        if day_mode:
            day_end_dt = end_dt
            while day_end_dt.weekday() >= 5:
                day_end_dt = day_end_dt - timedelta(days=1)
            rough_start_dt = day_end_dt - timedelta(days=220)
            calc_x_full = build_trading_dates(rough_start_dt, day_end_dt)
            if len(calc_x_full) > 100:
                calc_x_full = calc_x_full[-100:]
            prefetch_start_dt = rough_start_dt
            if calc_x_full:
                try:
                    prefetch_start_dt = date.fromisoformat(calc_x_full[0])
                except Exception:
                    prefetch_start_dt = rough_start_dt
        else:
            prefetch_start_dt = start_dt - timedelta(days=10)

        if has_token:
            try:
                if day_mode:
                    data_list = fetch_index_day_list(
                        prefetch_start_dt.isoformat(),
                        (day_end_dt or end_dt).isoformat(),
                        str(cfg["exponentId"]),
                        "open,high,low,close",
                    )
                    date_keys = [
                        "tradeDate",
                        "trade_date",
                        "date",
                        "datetime",
                        "dateTime",
                        "time",
                        "tradeTime",
                    ]
                    has_date_field = False
                    for it in data_list or []:
                        if not isinstance(it, dict):
                            continue
                        if get_first_value(it, date_keys) is not None:
                            has_date_field = True
                            break

                    if has_date_field:
                        x_close_raw, close_raw = parse_indicator_day_series(
                            data_list,
                            ["close", "closePrice", "close_price", "price", "last"],
                            start_dt=prefetch_start_dt,
                        )
                        x_high_raw, high_raw = parse_indicator_day_series(
                            data_list,
                            ["high", "highPrice", "high_price"],
                            start_dt=prefetch_start_dt,
                        )
                        x_low_raw, low_raw = parse_indicator_day_series(
                            data_list,
                            ["low", "lowPrice", "low_price"],
                            start_dt=prefetch_start_dt,
                        )
                    else:
                        n = len(data_list or [])
                        anchor_end = day_end_dt or end_dt
                        anchor_end_key = anchor_end.isoformat()
                        rough_start = anchor_end - timedelta(days=max(30, n * 3 + 10))
                        synth_dates = build_trading_dates(rough_start, anchor_end)
                        if len(synth_dates) >= n and n > 0:
                            synth_dates = synth_dates[-n:]
                        elif n > 0:
                            synth_dates = (synth_dates or []) + [anchor_end_key] * max(0, n - len(synth_dates or []))
                        x_close_raw = synth_dates
                        x_high_raw = synth_dates
                        x_low_raw = synth_dates

                        close_raw = []
                        high_raw = []
                        low_raw = []
                        for it in data_list or []:
                            if not isinstance(it, dict):
                                close_raw.append(None)
                                high_raw.append(None)
                                low_raw.append(None)
                                continue
                            close_raw.append(
                                get_first_value(it, ["close", "closePrice", "close_price", "price", "last"])
                            )
                            high_raw.append(get_first_value(it, ["high", "highPrice", "high_price"]))
                            low_raw.append(get_first_value(it, ["low", "lowPrice", "low_price"]))

                    close_src = {}
                    for x, v in zip(x_close_raw or [], close_raw or []):
                        k = format_day_label(x, start_dt=prefetch_start_dt)
                        if k is None or k in close_src:
                            continue
                        try:
                            close_src[k] = float(v)
                        except Exception:
                            continue

                    high_src = {}
                    for x, v in zip(x_high_raw or [], high_raw or []):
                        k = format_day_label(x, start_dt=prefetch_start_dt)
                        if k is None or k in high_src:
                            continue
                        try:
                            high_src[k] = float(v)
                        except Exception:
                            continue

                    low_src = {}
                    for x, v in zip(x_low_raw or [], low_raw or []):
                        k = format_day_label(x, start_dt=prefetch_start_dt)
                        if k is None or k in low_src:
                            continue
                        try:
                            low_src[k] = float(v)
                        except Exception:
                            continue

                    if day_end_dt is not None:
                        end_key = day_end_dt.isoformat()
                        avail = [k for k in close_src.keys() if k <= end_key]
                        if avail:
                            last_avail = max(avail)
                            if last_avail != end_key:
                                try:
                                    day_end_dt = date.fromisoformat(last_avail)
                                except Exception:
                                    pass

                    if day_end_dt is None:
                        x_full, close_full, high_full, low_full = [], [], [], []
                    else:
                        if calc_x_full is None:
                            rough_start_dt = day_end_dt - timedelta(days=220)
                            calc_x_full = build_trading_dates(rough_start_dt, day_end_dt)
                            if len(calc_x_full) > 100:
                                calc_x_full = calc_x_full[-100:]

                        if calc_x_full and calc_x_full[-1] != day_end_dt.isoformat():
                            calc_x_full = build_trading_dates(date.fromisoformat(calc_x_full[0]), day_end_dt)
                            if len(calc_x_full) > 100:
                                calc_x_full = calc_x_full[-100:]

                        if calc_x_full:
                            prefetch_start_dt = date.fromisoformat(calc_x_full[0])

                        x_full = calc_x_full or []
                        close_full = [close_src.get(k) for k in (x_full or [])]
                        high_full = [high_src.get(k, close_src.get(k)) for k in (x_full or [])]
                        low_full = [low_src.get(k, close_src.get(k)) for k in (x_full or [])]
                else:
                    data_list = fetch_index_min_list(
                        prefetch_start_dt.isoformat(),
                        end_dt.isoformat(),
                        cfg["exponentId"],
                        period_int,
                        "time,open,high,low,close",
                    )
                    x_full, close_full, high_full, low_full = parse_index_min_ohlc(
                        data_list, start_dt=prefetch_start_dt, period_minutes=period_int
                    )
            except Exception:
                x_full, close_full, high_full, low_full = [], [], [], []
        else:
            x_full = []
            close_full = []
            high_full = []
            low_full = []
            base = {
                "上证指数": 3000,
                "深证综指": 1900,
                "沪深300": 3800,
                "创业板指": 2200,
                "科创50": 950,
                "中证1000": 6200,
            }.get(index_name, 3000)
            period_label = period
            if day_mode:
                if not calc_x_full:
                    day_end_dt = end_dt
                    while day_end_dt.weekday() >= 5:
                        day_end_dt = day_end_dt - timedelta(days=1)
                    rough_start_dt = day_end_dt - timedelta(days=220)
                    calc_x_full = build_trading_dates(rough_start_dt, day_end_dt)
                    if len(calc_x_full) > 100:
                        calc_x_full = calc_x_full[-100:]
                if not calc_x_full:
                    calc_x_full = [start_dt.isoformat()]
                x_full = calc_x_full
                _, ys = generate_random_series(
                    length=len(x_full),
                    base=base,
                    fluctuation=25,
                    seed_text=f"divergence|{index_name}|{period_label}|{x_full[0]}|{x_full[-1]}",
                )
                close_full = [float(v) for v in ys]
                rnd = random.Random(
                    f"divergence_hilo|{index_name}|{period_label}|{x_full[0]}|{x_full[-1]}"
                )
                for v in close_full:
                    spread = max(0.8, abs(v) * 0.01)
                    high_full.append(v + rnd.random() * spread)
                    low_full.append(v - rnd.random() * spread)
            else:
                days = max(1, (end_dt - start_dt).days + 1)
                for i in range(days):
                    day = add_trading_days(start_dt, i) or (start_dt + timedelta(days=i))
                    xs, ys = generate_period_series(
                        period_label,
                        start_dt=day,
                        base=base,
                        fluctuation=25,
                        seed_text=f"divergence|{index_name}|{period_label}|{day.isoformat()}",
                    )
                    x_full.extend(xs)
                    close_full.extend([float(v) for v in ys])
                rnd = random.Random(
                    f"divergence_hilo|{index_name}|{period_label}|{start_dt}|{end_dt}"
                )
                for v in close_full:
                    spread = max(0.5, abs(v) * 0.0008)
                    high_full.append(v + rnd.random() * spread)
                    low_full.append(v - rnd.random() * spread)

        if not x_full or not close_full:
            st.warning("背离信号数据为空")
            return

        start_key = start_dt.isoformat()
        end_key = end_dt.isoformat()

        if day_mode:
            payload = compute_divergence_payload(x_full, close_full, high_full, low_full)

            x_data = build_trading_dates(start_dt, day_end_dt or end_dt)
            if not x_data:
                st.warning("背离信号数据为空")
                return

            close_map = {k: v for k, v in zip(x_full, payload["close"])}
            close_data = []
            for k in x_data:
                v = close_map.get(k)
                if v is None:
                    close_data.append(None)
                    continue
                try:
                    close_data.append(f"{float(v):.2f}")
                except Exception:
                    close_data.append(None)

            keep = None
        else:
            payload = compute_divergence_payload(x_full, close_full, high_full, low_full)
            keep = []
            for x in x_full:
                d = extract_label_date(x)
                if d is None or (d >= start_key and d <= end_key):
                    keep.append(True)
                else:
                    keep.append(False)

            x_data = [x for x, ok in zip(x_full, keep) if ok]
            close_data = []
            for v, ok in zip(payload["close"], keep):
                if not ok:
                    continue
                if v is None:
                    close_data.append(None)
                    continue
                try:
                    close_data.append(f"{float(v):.2f}")
                except Exception:
                    close_data.append(None)

        indicator_defs = [
            ("macd", "MACD(DIF)", payload["macd"]["dif"], payload["macd"]["signals"], "#3B82F6", show_macd),
            ("kdj", "KDJ(J)", payload["kdj"]["j"], payload["kdj"]["signals"], "#F59E0B", show_kdj),
            ("rsi", "RSI(14)", payload["rsi"]["rsi"], payload["rsi"]["signals"], "#EC4899", show_rsi),
        ]
        if not (show_macd or show_kdj or show_rsi):
            indicator_defs[0] = (*indicator_defs[0][:5], True)

        indicator_lines = []
        scatter_series = []
        active_signals = []
        legend_items = []

        signal_tag_series = []
        idx_by_x = {}
        for i, x in enumerate(x_data):
            if x not in idx_by_x:
                idx_by_x[x] = i
        signal_labels = [[] for _ in x_data]

        for key, title, series_full, signals_full, color, enabled in indicator_defs:
            if not enabled:
                continue

            series_data = []
            if day_mode:
                series_map = {}
                for k, v in zip(x_full, series_full):
                    if k is None:
                        continue
                    if k not in series_map:
                        series_map[k] = v
                for k in x_data:
                    v = series_map.get(k)
                    if v is None:
                        series_data.append(None)
                        continue
                    try:
                        series_data.append(f"{float(v):.2f}")
                    except Exception:
                        series_data.append(None)
            else:
                for v, ok in zip(series_full, keep):
                    if not ok:
                        continue
                    if v is None:
                        series_data.append(None)
                        continue
                    try:
                        series_data.append(f"{float(v):.2f}")
                    except Exception:
                        series_data.append(None)

            indicator_lines.append(
                {
                    "name": title,
                    "type": "line",
                    "data": series_data,
                    "yAxisIndex": 1,
                    "smooth": True,
                    "showSymbol": False,
                    "lineStyle": {"width": 0, "opacity": 0},
                    "itemStyle": {"opacity": 0},
                }
            )

            div_name_map = {
                "MACD(DIF)": "MACD背离",
                "KDJ(J)": "KDJ背离",
                "RSI(14)": "RSI背离",
            }
            div_name = div_name_map.get(title, f"{title}背离")
            legend_items.append({"name": div_name, "icon": "triangle", "itemStyle": {"color": color}})

            points = []
            for s in signals_full:
                if not s or "x" not in s:
                    continue
                if day_mode:
                    d = extract_label_date(s["x"])
                    if d is None:
                        d = format_day_label(s["x"], start_dt=prefetch_start_dt)
                    if d is None or d < start_key or d > end_key:
                        continue
                else:
                    d = extract_label_date(s["x"])
                    if d is not None and (d < start_key or d > end_key):
                        continue
                kind = s.get("kind")
                points.append(
                    {
                        "value": [d if day_mode else s["x"], s["price"]],
                        "symbol": "triangle",
                        "symbolRotate": 180 if kind == "顶背离" else 0,
                        "symbolSize": 11,
                        "z": 10,
                        "label": {"show": False},
                    }
                )
            if points:
                scatter_series.append(
                    {
                        "name": div_name,
                        "type": "scatter",
                        "data": points,
                        "itemStyle": {"opacity": 0.95, "color": color},
                        "tooltip": {"show": False},
                        "z": 10,
                    }
                )
            active_signals.extend(signals_full)

            for s in signals_full:
                if not s or "x" not in s:
                    continue
                if day_mode:
                    d = extract_label_date(s["x"])
                    if d is None:
                        d = format_day_label(s["x"], start_dt=prefetch_start_dt)
                    if d is None or d < start_key or d > end_key:
                        continue
                else:
                    d = extract_label_date(s["x"])
                    if d is not None and (d < start_key or d > end_key):
                        continue

                idx = idx_by_x.get(d if day_mode else s["x"])
                if idx is None:
                    continue
                if div_name not in signal_labels[idx]:
                    signal_labels[idx].append(div_name)

        signal_tag_data = []
        for labels in signal_labels:
            text = "无" if not labels else "、".join(labels)
            signal_tag_data.append({"value": 0, "signal": text})

        signal_tag_series = [
            {
                "name": "背离信号",
                "type": "line",
                "data": signal_tag_data,
                "yAxisIndex": 1,
                "showSymbol": False,
                "lineStyle": {"width": 0, "opacity": 0},
                "itemStyle": {"opacity": 0},
            }
        ]
        option = build_divergence_option(
            x_data,
            close_data,
            (signal_tag_series + indicator_lines),
            scatter_series,
            period,
            legend_items,
        )
        st_echarts(option, height="353px", key="divergence_chart")
        st.markdown('</div>', unsafe_allow_html=True)


def render_stock_distribution(ctx):
    with st.container(border=True):
        header = st.columns([3, 1.4, 1.4, 1.2])
        with header[0]:
            title_holder = st.empty()
        with header[1]:
            metric = st.selectbox(
                "口径",
                ["涨跌幅", "代办1"],
                key="dist_metric",
                label_visibility="collapsed",
            )
        with header[2]:
            scope = st.selectbox(
                "范围",
                ["全部A股", "代办1"],
                key="dist_scope",
                label_visibility="collapsed",
            )
        with header[3]:
            bucket = st.selectbox(
                "分组",
                ["今日", "昨日"],
                key="dist_bucket",
                label_visibility="collapsed",
            )

        categories = [
            ">30%",
            "30%",
            "20%",
            "10%",
            "7%",
            "4%",
            "2%",
            "0%",
            "-2%",
            "-4%",
            "-7%",
            "-10%",
            "-20%",
            "-30%",
            "<-30%",
        ]
        colors = []
        for name in categories:
            if name in {">30%", "30%", "20%", "10%", "7%", "4%", "2%"}:
                colors.append("#E94B3C")
            elif name in {"-2%", "-4%", "-7%", "-10%", "-20%", "-30%", "<-30%"}:
                colors.append("#2EBD85")
            else:
                colors.append("#999999")
        values = [0 for _ in categories]

        def decide_bucket(pct):
            try:
                v = float(pct)
            except Exception:
                return None
            if v >= 30.0:
                return ">30%"
            if v >= 20.0:
                return "30%"
            if v >= 10.0:
                return "20%"
            if v >= 7.0:
                return "10%"
            if v >= 4.0:
                return "7%"
            if v >= 2.0:
                return "4%"
            if v > 0:
                return "2%"
            if v == 0:
                return "0%"
            if v > -2.0:
                return "-2%"
            if v >= -4.0:
                return "-4%"
            if v >= -7.0:
                return "-7%"
            if v >= -10.0:
                return "-10%"
            if v >= -20.0:
                return "-20%"
            if v >= -30.0:
                return "-30%"
            return "<-30%"

        fetch_stock_list = ctx.get("fetch_stock_list_by_date_and_fields")
        get_refresh_token = ctx.get("get_refresh_token")
        has_token = bool(get_refresh_token())
        deal_day = date.today()
        if bucket == "昨日":
            deal_day = deal_day - timedelta(days=1)
        while deal_day.weekday() >= 5:
            deal_day = deal_day - timedelta(days=1)
        median_val = 0.0
        halt_count_calc = 0
        if metric == "涨跌幅" and has_token and fetch_stock_list:
            try:
                field_list = "stockCode,stockName,close,preClose,limitUpPrice,limitDownPrice,volume"
                data_list = fetch_stock_list(deal_day.isoformat(), field_list, "1")
                pct_list = []
                limit_up_count = 0
                limit_down_count = 0
                seen_codes = set()
                actual_date_text = None
                bshare_filtered = 0
                for item in data_list or []:
                    code = get_first_value(item, ["stockCode", "code"])
                    if code is None:
                        continue
                    code_text = str(code).strip()
                    if not code_text or not code_text.isdigit():
                        continue
                    if code_text.startswith("200") or code_text.startswith("900"):
                        bshare_filtered += 1
                        continue
                    if code_text in seen_codes:
                        continue
                    seen_codes.add(code_text)
                    if actual_date_text is None:
                        actual_date_text = get_first_value(item, ["dealDate", "tradeDate", "date"])
                    close_val = get_first_value(item, ["close", "closePrice", "price"])
                    pre_close_val = get_first_value(item, ["preClose", "pre_close", "lastClose", "prevClose"])
                    lup = get_first_value(item, ["limitUpPrice"])
                    ldn = get_first_value(item, ["limitDownPrice"])
                    v = get_first_value(item, ["volume", "vol"])
                    pct = None
                    pct_raw = get_first_value(item, ["changePercent", "pct_chg", "change_percent"])
                    try:
                        if pct_raw is not None and str(pct_raw).strip() != "":
                            pct = float(pct_raw)
                    except Exception:
                        pct = None
                    try:
                        c = float(close_val) if close_val is not None else None
                        p = float(pre_close_val) if pre_close_val is not None else None
                        if pct is None and c is not None and p is not None and p > 0:
                            pct = round((c / p - 1.0) * 100.0, 4)
                    except Exception:
                        pct = None
                    bucket_name = decide_bucket(pct)
                    if bucket_name is not None:
                        try:
                            idx = categories.index(bucket_name)
                            values[idx] += 1
                        except Exception:
                            pass
                        try:
                            pct_list.append(float(pct))
                        except Exception:
                            pass
                    try:
                        vv = float(v) if v is not None else None
                    except Exception:
                        vv = None
                    if vv is not None and vv <= 0:
                        halt_count_calc += 1
                    try:
                        c = float(close_val) if close_val is not None else None
                        up = float(lup) if lup is not None else None
                        dn = float(ldn) if ldn is not None else None
                        if c is not None and up is not None and c >= up:
                            limit_up_count += 1
                        if c is not None and dn is not None and c <= dn:
                            limit_down_count += 1
                    except Exception:
                        pass
                if pct_list:
                    s = sorted(pct_list)
                    n = len(s)
                    if n % 2 == 1:
                        median_val = s[n // 2]
                    else:
                        median_val = (s[n // 2 - 1] + s[n // 2]) / 2.0
            except Exception:
                categories, values, colors = generate_distribution_data(f"{metric}-{scope}-{bucket}")
                halt_count_calc = 0
                median_val = 0.0
        else:
            categories, values, colors = generate_distribution_data(f"{metric}-{scope}-{bucket}")
            halt_count_calc = 0
            median_val = 0.0

        def bucket_value(name):
            t = str(name).strip()
            if t == "涨停":
                return 10.0
            if t == "跌停":
                return -10.0
            if t == ">10%":
                return 10.5
            if t == "<-10%":
                return -10.5
            if t.endswith("%"):
                try:
                    return float(t.replace("%", ""))
                except Exception:
                    return 0.0
            return 0.0

        if median_val is None:
            median_val = 0.0
        median_text = f"{float(median_val):+.2f}%"

        with header[0]:
            title_holder.markdown(
                f'''
<div style="display:flex; justify-content:space-between; align-items:flex-end;">
  <div style="font-size:16px; font-weight:800;">个股涨跌分布</div>
  <div style="font-size:12px; color:#e94b3c;">涨跌中位数：{median_text}</div>
</div>
''',
                unsafe_allow_html=True,
            )
            if locals().get("actual_date_text"):
                st.markdown(
                    f'<div style="font-size:12px;color:#6B7280;">数据日期：{str(locals().get("actual_date_text"))}（去重样本：{len(locals().get("seen_codes", set()))}，过滤B股：{locals().get("bshare_filtered",0)}）</div>',
                    unsafe_allow_html=True,
                )

        chart_col, side_col = st.columns([3, 1])

        up_buckets = {">30%", "30%", "20%", "10%", "7%", "4%", "2%"}
        down_buckets = {"-2%", "-4%", "-7%", "-10%", "-20%", "-30%", "<-30%"}
        flat_bucket = "0%"
        up_count = sum(v for c, v in zip(categories, values) if c in up_buckets)
        down_count = sum(v for c, v in zip(categories, values) if c in down_buckets)
        flat_count = sum(v for c, v in zip(categories, values) if c == flat_bucket)
        limit_up_count = locals().get("limit_up_count", 0)
        limit_down_count = locals().get("limit_down_count", 0)

        halt = halt_count_calc
        total_all = max(up_count + down_count + flat_count + (halt or 0), 1)
        up_limit_ratio = round(limit_up_count * 100 / total_all, 2)
        down_limit_ratio = round(limit_down_count * 100 / total_all, 2)
        strength = round((up_count - down_count) * 100.0 / total_all, 2)
        if up_count > 0 and down_count > 0:
            if up_count >= down_count:
                ratio_text = f"{up_count / down_count:.2f}:1"
            else:
                ratio_text = f"1:{down_count / up_count:.2f}"
        elif up_count > 0 and down_count == 0:
            ratio_text = "∞:1"
        elif down_count > 0 and up_count == 0:
            ratio_text = "1:∞"
        else:
            ratio_text = "1:1"

        with chart_col:
            option = build_bar_option("涨跌分布", categories, values, colors, show_title=False)
            st_echarts(option, height="300px", key="dist_chart")

        strong_count = up_count
        weak_count = down_count
        strong_ratio = round(strong_count * 100.0 / total_all, 2)
        weak_ratio = round(weak_count * 100.0 / total_all, 2)
        if strong_count > 0 and weak_count > 0:
            if strong_count >= weak_count:
                strong_weak_ratio_text = f"{strong_count / weak_count:.2f}:1"
            else:
                strong_weak_ratio_text = f"1:{weak_count / strong_count:.2f}"
        elif strong_count > 0 and weak_count == 0:
            strong_weak_ratio_text = "∞:1"
        elif weak_count > 0 and strong_count == 0:
            strong_weak_ratio_text = "1:∞"
        else:
            strong_weak_ratio_text = "1:1"
        if limit_up_count > 0 and limit_down_count > 0:
            if limit_up_count >= limit_down_count:
                limit_ratio_text = f"{limit_up_count / limit_down_count:.2f}:1"
            else:
                limit_ratio_text = f"1:{limit_down_count / limit_up_count:.2f}"
        elif limit_up_count > 0 and limit_down_count == 0:
            limit_ratio_text = "∞:1"
        elif limit_down_count > 0 and limit_up_count == 0:
            limit_ratio_text = "1:∞"
        else:
            limit_ratio_text = "1:1"
        strength_color = "#E94B3C" if strength >= 0 else "#2EBD85"

        with side_col:
            side_html = f'''
<div style="border:1px solid #e5e5e5;border-radius:10px;overflow:hidden;height:320px;">
  <div style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto 1fr 1fr;height:100%;">
    <div style="grid-column:1 / span 2;border-bottom:1px solid #e5e5e5;padding:10px 12px;">
      <div style="font-size:12px;color:#666666;">全市涨跌停比例</div>
      <div style="font-size:18px;font-weight:800;color:#111827;">{limit_ratio_text}</div>
    </div>
    <div style="border-right:1px solid #e5e5e5;border-bottom:1px solid #e5e5e5;padding:10px 12px;">
      <div style="font-size:12px;color:#666666;">行情强度</div>
      <div style="font-size:18px;font-weight:800;color:{strength_color};">{strength:+.2f}%</div>
    </div>
    <div style="border-bottom:1px solid #e5e5e5;padding:10px 12px;">
      <div style="font-size:12px;color:#666666;">强弱比</div>
      <div style="font-size:18px;font-weight:800;color:#111827;">{strong_weak_ratio_text}</div>
    </div>
    <div style="border-right:1px solid #e5e5e5;padding:10px 12px;">
      <div style="font-size:12px;color:#666666;">强势个股占比</div>
      <div style="font-size:18px;font-weight:800;color:#E94B3C;">{strong_ratio}%</div>
    </div>
    <div style="padding:10px 12px;">
      <div style="font-size:12px;color:#666666;">弱势个股占比</div>
      <div style="font-size:18px;font-weight:800;color:#2EBD85;">{weak_ratio}%</div>
    </div>
  </div>
</div>
'''
            st.markdown(side_html, unsafe_allow_html=True)

        bottom_stats = [("上涨", up_count), ("平盘", flat_count), ("停牌", halt), ("下跌", down_count)]
        color_map = {"上涨": "#E94B3C", "下跌": "#2EBD85", "平盘": "#6B7280", "停牌": "#6B7280"}
        cards_full = []
        for name, value in bottom_stats:
            extra = ""
            if name == "上涨":
                extra = f'<div style="font-size:12px;color:#E94B3C;white-space:nowrap;">其中：涨停 {limit_up_count}家</div>'
            elif name == "下跌":
                extra = f'<div style="font-size:12px;color:#2EBD85;white-space:nowrap;">其中：跌停 {limit_down_count}家</div>'
            cards_full.append(
                f'''
<div style="background:#f5f5f5;border-radius:12px;padding:8px 12px;text-align:center;">
  <div style="font-size:12px;color:#666666;white-space:nowrap;">{name}</div>
  <div style="font-size:16px;font-weight:800;color:{color_map.get(name,"#111827")};white-space:nowrap;">{value}家</div>
  {extra}
</div>
'''
            )
        st.markdown(
            f'''
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 4px 0;">
  {''.join(cards_full)}
</div>
''',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


def render_index_monitor(ctx):
    render_monitor_overview(ctx)
    st.write("")
    left, right = st.columns(2)
    with left:
        render_divergence_signal(ctx)
    with right:
        render_stock_distribution(ctx)
    st.write("")


def render_volume_tun_panel(ctx):
    fetch_index_day_list = ctx["fetch_index_day_list"]
    parse_indicator_day_series = ctx["parse_indicator_day_series"]
    index_min_map = ctx["INDEX_MIN_MAP"]
    build_line_option = ctx["build_line_option"]

    names = list(index_min_map.keys())
    if "volume_tun_selected_index" not in st.session_state:
        st.session_state["volume_tun_selected_index"] = names[0]
    
    current_selected = st.session_state.get("volume_tun_selected_index")
    if current_selected not in names:
        current_selected = names[0]
        st.session_state["volume_tun_selected_index"] = current_selected

    with st.container(border=True):
        h1, h2, h3 = st.columns([3, 0.8, 1.2])
        with h1:
            st.markdown(
                '<div style="text-align:left;font-size:16px;font-weight:800;color:#111827;display:flex;align-items:center;height:100%;">成交量与换手率监测</div>',
                unsafe_allow_html=True,
            )
        with h2:
            date_opt = st.selectbox(
                "日期",
                ["今日", "昨日"],
                key="vol_tun_date_opt",
                label_visibility="collapsed",
            )
        with h3:
            selected = st.selectbox(
                "选择指数",
                names,
                index=names.index(current_selected),
                key="vol_tun_index_select",
                label_visibility="collapsed",
            )
            st.session_state["volume_tun_selected_index"] = selected

        today = date.today()
        end_dt = today
        while end_dt.weekday() >= 5:
            end_dt = end_dt - timedelta(days=1)
        
        if date_opt == "昨日":
            end_dt = end_dt - timedelta(days=1)
            while end_dt.weekday() >= 5:
                end_dt = end_dt - timedelta(days=1)
        
        start_dt = end_dt - timedelta(days=14)
        # 监测表格只需要最近几天的数据（今日、昨日、前日），取7天缓冲以涵盖周末和节假日
        start_dt_table = end_dt - timedelta(days=7)

        st.divider()

        ids = [index_min_map[n]["exponentId"] for n in names]
        table_rows = []
        t_label = "今日"
        prev_label = "昨日"

        for name, eid in zip(names, ids):
            try:
                all_list = fetch_index_day_list(
                    start_dt_table.isoformat(),
                    end_dt.isoformat(),
                    str(eid),
                    "volume,amount,turnoverRate,tun,turnoverRatio,turnover",
                )
                x_vol_tmp, y_vol_tmp = parse_indicator_day_series(all_list, ["volume", "vol"], start_dt=start_dt_table)
                x_tun_tmp, y_tun_tmp = parse_indicator_day_series(
                    all_list,
                    ["tun", "turnoverRate", "turnover_rate", "turnover", "turnoverRatio", "turnover_ratio"],
                    start_dt=start_dt_table,
                )
            except Exception:
                x_vol_tmp, y_vol_tmp = [], []
                x_tun_tmp, y_tun_tmp = [], []

            valid_vol = [v for v in (y_vol_tmp or []) if v is not None]
            last_vol = valid_vol[-1] if valid_vol else None
            prev_vol = valid_vol[-2] if len(valid_vol) > 1 else None

            vol_yoy = None
            try:
                lv = float(last_vol) if last_vol is not None else None
                pv = float(prev_vol) if prev_vol is not None else None
                if lv is not None and pv is not None and pv != 0:
                    vol_yoy = (lv / pv - 1) * 100.0
            except Exception:
                vol_yoy = None

            valid_tun = [v for v in (y_tun_tmp or []) if v is not None]
            last_tun = valid_tun[-1] if valid_tun else None
            prev_tun = valid_tun[-2] if len(valid_tun) > 1 else None

            tun_yoy = None
            try:
                lt = float(last_tun) if last_tun is not None else None
                pt = float(prev_tun) if prev_tun is not None else None
                if lt is not None and pt is not None and pt != 0:
                    tun_yoy = (lt / pt - 1) * 100.0
            except Exception:
                tun_yoy = None

            def fmt_vol(v):
                if v is None:
                    return "--"
                try:
                    fv = float(v)
                    return f"{fv:,.2f}"
                except Exception:
                    return "--"

            table_rows.append(
                {
                    "指数": name,
                    f"{prev_label}成交量(手)": fmt_vol(prev_vol),
                    f"{t_label}成交量(手)": fmt_vol(last_vol),
                    "成交量同比": f"{float(vol_yoy):+.2f}%" if vol_yoy is not None else "--",
                    f"{prev_label}换手率": f"{float(prev_tun):.2f}%" if prev_tun is not None else "--",
                    f"{t_label}换手率": f"{float(last_tun):.2f}%" if last_tun is not None else "--",
                    "换手率同比": f"{float(tun_yoy):+.2f}%" if tun_yoy is not None else "--",
                }
            )

        if table_rows:
            df = pd.DataFrame(table_rows)
            html = df.to_html(index=False, border=0, classes="custom-table")
            st.markdown(
                """
                <style>
                .custom-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 1rem;
                }
                .custom-table th, .custom-table td {
                    text-align: center !important;
                    padding: 8px;
                    border: 1px solid #e5e7eb;
                    font-size: 14px;
                    color: #374151;
                }
                .custom-table th:nth-child(4), .custom-table td:nth-child(4) {
                    border-right: 3px solid #d1d5db !important;
                }
                .custom-table th {
                    background-color: #f9fafb;
                    font-weight: 600;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("暂无数据")

        eid = index_min_map[selected]["exponentId"]
        try:
            all_list = fetch_index_day_list(
                start_dt.isoformat(),
                end_dt.isoformat(),
                str(eid),
                "volume,amount,turnoverRate,tun,turnoverRatio,turnover",
            )
            x_vol, y_vol = parse_indicator_day_series(all_list, ["volume", "vol"], start_dt=start_dt)
            x_tun, y_tun = parse_indicator_day_series(
                all_list,
                ["tun", "turnoverRate", "turnover_rate", "turnover", "turnoverRatio", "turnover_ratio"],
                start_dt=start_dt,
            )
        except Exception:
            x_vol, y_vol = [], []
            x_tun, y_tun = [], []
        x_vol = [format_day_label(v, start_dt=start_dt) for v in (x_vol or [])]
        x_tun = [format_day_label(v, start_dt=start_dt) for v in (x_tun or [])]
        expected_dates = build_trading_dates(start_dt, end_dt)
        if expected_dates:
            m_vol = {}
            for x, v in zip(x_vol or [], y_vol or []):
                d = extract_label_date(x)
                if d is not None and d not in m_vol:
                    m_vol[d] = v
            m_tun = {}
            for x, v in zip(x_tun or [], y_tun or []):
                d = extract_label_date(x)
                if d is not None and d not in m_tun:
                    m_tun[d] = v
            x_vol = expected_dates
            y_vol = [m_vol.get(d) for d in expected_dates]
            x_tun = expected_dates
            y_tun = [m_tun.get(d) for d in expected_dates]

        vol_option = build_line_option(f"{selected} - 成交量", x_vol, y_vol, show_title=True)
        tun_option = build_line_option(f"{selected} - 换手率(%)", x_tun, y_tun, show_title=True)

        charts = st.columns(2)
        with charts[0]:
            with st.container(border=True):
                st_echarts(vol_option, height="320px", key="vol_trend_chart")
        with charts[1]:
            with st.container(border=True):
                st_echarts(tun_option, height="320px", key="tun_trend_chart")
