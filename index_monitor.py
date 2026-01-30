import random

from datetime import date, timedelta

import streamlit as st
from streamlit_echarts import st_echarts


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
                x_large, y_large = generate_period_series("60分钟", start_dt=start_dt, base=4200, fluctuation=20)
                x_small, y_small = generate_period_series("60分钟", start_dt=start_dt, base=6200, fluctuation=25)
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
                x_large, y_large = generate_period_series(period, start_dt=start_dt, base=4200, fluctuation=20)
                x_small, y_small = generate_period_series(period, start_dt=start_dt, base=6200, fluctuation=25)
    except Exception:
        x_large, y_large = generate_period_series("5分钟", start_dt=start_dt, base=4200, fluctuation=20)
        x_small, y_small = generate_period_series("5分钟", start_dt=start_dt, base=6200, fluctuation=25)

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
    st_echarts(option, height="220px", key="size_style_chart")


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


def render_divergence_signal():
    with st.container(border=True):
        header = st.columns([2.2, 1.5, 1.5, 1.5, 1.8])
        with header[0]:
            render_panel_title("背离信号")
        with header[1]:
            st.date_input("开始", key="divergence_start", label_visibility="collapsed")
        with header[2]:
            st.date_input("结束", key="divergence_end", label_visibility="collapsed")
        with header[3]:
            period = st.selectbox(
                "周期",
                ["1分钟", "5分钟", "30分钟", "60分钟"],
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

        length = 45
        x_data = list(range(length))
        price = []
        value = 3100
        for _ in x_data:
            value += random.randint(-25, 25)
            price.append(value)

        random.seed(f"{index_name}-{period}")
        signal_defs = [
            ("MACD背离", show_macd, "#3B82F6", "MACD顶"),
            ("KDJ背离", show_kdj, "#F59E0B", "KDJ顶"),
            ("RSI背离", show_rsi, "#EC4899", "RSI顶"),
        ]
        scatter_series = []
        for name, enabled, color, label_text in signal_defs:
            if not enabled:
                continue
            points_count = random.randint(3, 6)
            xs = sorted(random.sample(range(3, length - 3), points_count))
            data = []
            for x in xs:
                data.append(
                    {
                        "value": [x, price[x]],
                        "label": {"show": True, "formatter": label_text, "color": "#666666"},
                    }
                )
            scatter_series.append(
                {
                    "name": name,
                    "type": "scatter",
                    "data": data,
                    "symbolSize": 10,
                    "itemStyle": {"color": color},
                }
            )
        random.seed()

        option = {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["价格"] + [s[0] for s in signal_defs if s[1]], "top": 0},
            "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
            "yAxis": [{"type": "value", "scale": True}],
            "grid": {"left": 40, "right": 20, "top": 50, "bottom": 30},
            "series": [
                {
                    "name": "价格",
                    "type": "line",
                    "data": price,
                    "smooth": True,
                    "showSymbol": False,
                    "lineStyle": {"width": 2, "color": "#3B82F6"},
                }
            ]
            + scatter_series,
        }
        st_echarts(option, height="320px", key="divergence_chart")


def render_stock_distribution():
    with st.container(border=True):
        header = st.columns([3, 1.4, 1.4, 1.2])
        with header[0]:
            render_panel_title("个股涨跌分布")
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
            st.selectbox(
                "分组",
                ["今日", "昨日"],
                key="dist_bucket",
                label_visibility="collapsed",
            )

        chart_col, side_col = st.columns([3, 1])

        u = random.randint(800, 4200)
        d = random.randint(800, 4200)
        flat = random.randint(50, 300)
        halt = random.randint(10, 80)
        limit_up = random.randint(0, 120)
        limit_down = random.randint(0, 80)
        total = max(u + d + flat + halt, 1)
        up_ratio = round(limit_up * 100 / total, 2)
        down_ratio = round(limit_down * 100 / total, 2)

        with chart_col:
            categories, values, colors = generate_distribution_data(f"{metric}-{scope}-全市场")
            option = build_bar_option("涨跌分布", categories, values, colors, show_title=False)
            st_echarts(option, height="320px", key="dist_chart")
            stats = [("上涨", u), ("平盘", flat), ("停牌", halt), ("下跌", d)]
            cards_html = "".join(
                [
                    f'''
<div style="flex:1;background:#f5f5f5;border-radius:10px;padding:6px 12px;text-align:center;font-size:12px;min-width:0;">
  <div style="font-size:14px;font-weight:700;color:#111827;white-space:nowrap;">{name} {value}家</div>
</div>
'''
                    for name, value in stats
                ]
            )
            st.markdown(
                f'''
<div style="display:flex;gap:12px;margin:18px 8px 4px 8px;">
  {cards_html}
</div>
''',
                unsafe_allow_html=True,
            )

        with side_col:
            st.metric("涨跌停占比", f"{up_ratio}%")
            st.metric("指标2", f"{down_ratio}%")
            st.metric("指标3", f"{down_ratio}%")
            st.metric("指标4", f"{down_ratio}%")


def render_index_monitor(ctx):
    render_monitor_overview(ctx)
    st.write("")
    left, right = st.columns(2)
    with left:
        render_divergence_signal()
    with right:
        render_stock_distribution()
