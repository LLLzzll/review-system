from datetime import date, timedelta

import streamlit as st
from streamlit_echarts import JsCode, st_echarts
from index_monitor import render_volume_tun_panel


def to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def get_first_value(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None


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


def parse_min_volume_series(data_list):
    volumes = []
    for item in data_list or []:
        if not isinstance(item, dict):
            continue
        y_val = (
            item.get("close")
            or item.get("closePrice")
            or item.get("price")
            or item.get("open")
            or item.get("high")
            or item.get("low")
        )
        if y_val is None:
            continue
        vol_val = (
            item.get("volume")
            or item.get("vol")
            or item.get("amount")
            or item.get("turnover")
            or item.get("turnoverAmount")
        )
        vol_f = to_float(vol_val)
        volumes.append(0 if vol_f is None else max(0, vol_f))
    return volumes


def build_synthetic_volume(price_series):
    out = []
    last = None
    for v in price_series or []:
        vf = to_float(v)
        if vf is None:
            out.append(0)
            continue
        if last is None:
            out.append(0)
        else:
            out.append(abs(vf - last) * 1000)
        last = vf
    return out


def build_price_volume_option(x_data, kind, price_series=None, candlestick_series=None, volume_series=None):
    tooltip_formatter = JsCode(
        "function (params) { if (!params || !params.length) { return ''; } var axisLabel = params[0].axisValueLabel || params[0].axisValue || ''; var rows = ['<div style=\"margin:0 0 6px 0;\">' + axisLabel + '</div>']; function fmtPrice(v) { var n = Number(v); if (!isFinite(n)) return v == null ? '--' : String(v); return n.toFixed(2); } function fmtVol(v) { var n = Number(v); if (!isFinite(n)) return v == null ? '--' : String(v); return String(Math.round(n)); } function pickCandle(p) { if (!p) return null; if (p.seriesType !== 'candlestick') return null; var d = p.data != null ? p.data : p.value; if (!d) return null; if (d && typeof d === 'object' && !Array.isArray(d)) { if (d.open != null || d.close != null || d.low != null || d.high != null) { return { o: d.open, c: d.close, l: d.low, h: d.high }; } if (d.value != null) d = d.value; } if (Array.isArray(d) && d.length >= 4) { return { o: d[0], c: d[1], l: d[2], h: d[3] }; } return null; } for (var i = 0; i < params.length; i++) { var p = params[i]; if (!p) continue; var marker = p.marker || ''; var name = p.seriesName || ''; var candle = pickCandle(p); if (candle) { rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;\">' + '<span>' + marker + name + '</span>' + '<span style=\"font-weight:600;\">K线</span>' + '</div>'); rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;padding-left:14px;\">' + '<span>开盘价</span><span style=\"font-weight:600;\">' + fmtPrice(candle.o) + '</span></div>'); rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;padding-left:14px;\">' + '<span>收盘价</span><span style=\"font-weight:600;\">' + fmtPrice(candle.c) + '</span></div>'); rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;padding-left:14px;\">' + '<span>最高价</span><span style=\"font-weight:600;\">' + fmtPrice(candle.h) + '</span></div>'); rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;padding-left:14px;\">' + '<span>最低价</span><span style=\"font-weight:600;\">' + fmtPrice(candle.l) + '</span></div>'); continue; } var v = (p.data != null ? p.data : p.value); if (v && typeof v === 'object' && !Array.isArray(v) && v.value != null) { v = v.value; } var valueText = (p.seriesType === 'bar' || name === '成交量') ? fmtVol(v) : fmtPrice(v); rows.push('<div style=\"display:flex;justify-content:space-between;gap:12px;white-space:nowrap;\">' + '<span>' + marker + name + '</span>' + '<span style=\"font-weight:600;\">' + valueText + '</span>' + '</div>'); } return rows.join(''); }"
    ).js_code

    x_data = x_data or []
    volume_series = volume_series or [0] * len(x_data)
    grid = [
        {"left": 40, "right": 10, "top": 10, "bottom": "28%", "containLabel": True},
        {"left": 40, "right": 10, "top": "78%", "bottom": 18, "containLabel": True},
    ]
    x_axis = [
        {
            "type": "category",
            "data": x_data,
            "boundaryGap": kind == "candlestick",
            "axisLabel": {"show": False},
            "axisTick": {"show": False},
            "axisPointer": {"label": {"show": False}},
        },
        {
            "type": "category",
            "gridIndex": 1,
            "data": x_data,
            "boundaryGap": True,
            "axisLabel": {"hideOverlap": True, "fontSize": 10},
            "axisTick": {"alignWithLabel": True},
        },
    ]
    y_axis = [
        {"type": "value", "scale": True, "splitArea": {"show": False}},
        {"type": "value", "scale": True, "gridIndex": 1, "splitNumber": 2, "axisLabel": {"show": False}},
    ]

    if kind == "candlestick":
        normalized_candles = []
        price_change_flags = []
        for row in candlestick_series or []:
            value = None
            if isinstance(row, dict):
                value = row.get("value")
            elif isinstance(row, (list, tuple)):
                value = list(row)

            if not isinstance(value, (list, tuple)) or len(value) < 2:
                normalized_candles.append({"value": [None, None, None, None], "open": None, "close": None, "low": None, "high": None})
                price_change_flags.append(True)
                continue

            o = to_float(value[0])
            c = to_float(value[1])
            l = to_float(value[2]) if len(value) > 2 else None
            h = to_float(value[3]) if len(value) > 3 else None
            if o is None or c is None:
                price_change_flags.append(True)
            else:
                price_change_flags.append(c >= o)
            normalized_candles.append({"value": [o, c, l, h], "open": o, "close": c, "low": l, "high": h})
        price_series_conf = {
            "name": "价格",
            "type": "candlestick",
            "data": normalized_candles,
            "itemStyle": {
                "color": "#EF4444",
                "color0": "#22C55E",
                "borderColor": "#EF4444",
                "borderColor0": "#22C55E",
            },
        }
    else:
        price_vals = [to_float(v) for v in (price_series or [])]
        price_change_flags = []
        last = None
        for v in price_vals:
            if v is None:
                price_change_flags.append(True)
                continue
            if last is None:
                price_change_flags.append(True)
            else:
                price_change_flags.append(v >= last)
            last = v
        price_series_conf = {
            "name": "价格",
            "type": "line",
            "data": price_vals,
            "smooth": True,
            "showSymbol": False,
            "lineStyle": {"width": 2, "color": "#2563EB"},
        }

    vol_data = []
    for idx, v in enumerate(volume_series or []):
        up = True
        if idx < len(price_change_flags):
            up = bool(price_change_flags[idx])
        color = "#EF4444" if up else "#22C55E"
        vol_f = to_float(v)
        vol_val = 0 if vol_f is None else max(0, vol_f) * 100
        vol_data.append({"value": vol_val, "itemStyle": {"color": color}})

    option = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": tooltip_formatter,
            "backgroundColor": "#ffffff",
            "borderColor": "#e5e7eb",
            "borderWidth": 1,
            "textStyle": {"color": "#111827"},
            "extraCssText": "box-shadow:0 10px 25px rgba(0,0,0,0.12);",
        },
        "axisPointer": {
            "link": [{"xAxisIndex": "all"}],
            "label": {
                "backgroundColor": "#ffffff",
                "borderColor": "#e5e7eb",
                "borderWidth": 1,
                "color": "#111827",
            },
        },
        "grid": grid,
        "xAxis": x_axis,
        "yAxis": y_axis,
        "series": [
            price_series_conf,
            {
                "name": "成交量",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "data": vol_data,
                "barWidth": "60%",
            },
        ],
    }
    return option


def render_index_card(ctx, title, adjustable=False, height="320px"):
    index_min_map = ctx["INDEX_MIN_MAP"]
    fetch_index_day_list = ctx["fetch_index_day_list"]
    fetch_index_min_list = ctx["fetch_index_min_list"]
    generate_period_series = ctx["generate_period_series"]
    generate_random_series = ctx["generate_random_series"]
    parse_indicator_day_series = ctx["parse_indicator_day_series"]
    parse_index_min_series = ctx["parse_index_min_series"]

    option_key = f"{title}_option" if adjustable else title
    period_key = f"{title}_period"
    header_left, header_right = st.columns([2.2, 1.3])
    period = None
    if adjustable:
        with header_right:
            period = st.selectbox(
                "周期",
                ["1分钟", "5分钟", "30分钟", "60分钟", "日线"],
                index=0,
                key=period_key,
                label_visibility="collapsed",
            )
    with header_left:
        st.markdown(f"**{title}**")
    x_data = None
    y_data = None
    if adjustable and period is not None:
        base_name = title.replace("分时", "").strip()
        cfg = index_min_map.get(base_name)
        start_dt = st.session_state.get("index_min_start_date") or date.today()
        end_dt = st.session_state.get("index_min_end_date") or date.today()
        if period == "日线":
            if cfg:
                try:
                    data_list = fetch_index_day_list(
                        start_dt.isoformat(),
                        end_dt.isoformat(),
                        str(cfg["exponentId"]),
                        "open,high,low,close,volume",
                    )
                    if not data_list:
                        st.caption(f"{base_name} 日线接口返回为空")
                        return
                except Exception as e:
                    st.caption(f"{base_name} 日线数据获取失败：{e}")
                    return
            else:
                st.caption(f"{base_name} 缺少指数映射")
                return
        else:
            period_int = {"1分钟": 1, "5分钟": 5, "30分钟": 30, "60分钟": 60}.get(period, 1)
            field_list = "time,open,high,low,close,volume"
            if cfg:
                try:
                    data_list = fetch_index_min_list(
                        start_dt.isoformat(),
                        end_dt.isoformat(),
                        cfg["exponentId"],
                        period_int,
                        field_list,
                    )
                    x_data, y_data = parse_index_min_series(
                        data_list, start_dt=start_dt, period_minutes=period_int
                    )
                except Exception as e:
                    st.caption(f"{base_name} 数据获取失败，使用模拟数据：{e}")
            if not x_data or not y_data:
                x_data, y_data = generate_period_series(
                    period,
                    start_dt=start_dt,
                    seed_text=f"{base_name}|{period}|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
    else:
        x_data, y_data = generate_random_series(seed_text=title)

    if adjustable and period == "日线":
        try:
            expected_code = None if not cfg else cfg.get("code")
            x_data = []
            candlestick_data = []
            volume_data = []
            last_close = None
            seq = 0
            for item in data_list or []:
                if not isinstance(item, dict):
                    continue

                item_code = item.get("code")
                if expected_code and item_code and str(item_code) != str(expected_code):
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
                if x_val is None:
                    x_text = (add_trading_days(start_dt, seq) or start_dt).isoformat() if start_dt else str(seq)
                else:
                    s = str(x_val).strip()
                    if len(s) == 8 and s.isdigit():
                        x_text = f"{s[:4]}-{s[4:6]}-{s[6:]}"
                    elif "T" in s:
                        x_text = s.split("T", 1)[0]
                    elif " " in s:
                        x_text = s.split(" ", 1)[0]
                    else:
                        x_text = s

                o = to_float(get_first_value(item, ["open", "openPrice", "open_price"]))
                c = to_float(
                    get_first_value(item, ["close", "closePrice", "close_price", "price", "last"])
                )
                h = to_float(get_first_value(item, ["high", "highPrice", "high_price"]))
                l = to_float(get_first_value(item, ["low", "lowPrice", "low_price"]))

                if o is None and last_close is not None:
                    o = last_close
                if c is None:
                    c = o if o is not None else last_close
                if c is None:
                    continue
                if o is None:
                    o = c

                candidates = [v for v in (o, c, h, l) if v is not None]
                hi = max(candidates) if candidates else None
                lo = min(candidates) if candidates else None
                candlestick_data.append([o, c, lo, hi])

                vol = to_float(get_first_value(item, ["volume", "vol", "amount"]))
                volume_data.append(0 if vol is None else max(0, vol))
                x_data.append(x_text)
                last_close = c
                seq += 1

            if not x_data:
                st.caption(f"{base_name} 日线数据缺少可绘制字段")
                return

            option = build_price_volume_option(
                x_data,
                "candlestick",
                candlestick_series=candlestick_data,
                volume_series=volume_data,
            )
        except Exception as e:
            st.caption(f"{base_name} 日线绘制失败：{e}")
            return
    else:
        volume_data = None
        if adjustable and period is not None and period != "日线" and "data_list" in locals():
            try:
                volume_data = parse_min_volume_series(data_list)
                if volume_data and y_data and len(volume_data) != len(y_data):
                    volume_data = volume_data[: len(y_data)]
            except Exception:
                volume_data = None
        if not volume_data:
            volume_data = build_synthetic_volume(y_data)
        option = build_price_volume_option(
            x_data,
            "line",
            price_series=y_data,
            volume_series=volume_data,
        )

    st_echarts(option, height=height, key=option_key)


def render_card(ctx, title, height="320px"):
    generate_random_series = ctx["generate_random_series"]
    build_line_option = ctx["build_line_option"]

    x_data, y_data = generate_random_series(seed_text=title)
    option = build_line_option(title, x_data, y_data, show_title=True)
    st_echarts(option, height=height, key=title)


def render_index_compare(ctx):
    apply_index_date_preset = ctx["apply_index_date_preset"]
    get_refresh_token = ctx["get_refresh_token"]

    controls = st.columns([0.8, 0.8, 0.9, 1.2, 1.2, 3])
    with controls[0]:
        if st.button(
            "今日",
            key="index_date_preset_today",
            disabled=st.session_state.get("index_date_preset") == "今日",
        ):
            st.session_state["index_date_preset"] = "今日"
            apply_index_date_preset()
    with controls[1]:
        if st.button(
            "昨日",
            key="index_date_preset_yesterday",
            disabled=st.session_state.get("index_date_preset") == "昨日",
        ):
            st.session_state["index_date_preset"] = "昨日"
            apply_index_date_preset()
    with controls[2]:
        if st.button(
            "近一周",
            key="index_date_preset_week",
            disabled=st.session_state.get("index_date_preset") == "近一周",
        ):
            st.session_state["index_date_preset"] = "近一周"
            apply_index_date_preset()
    with controls[3]:
        st.date_input(
            "开始日期",
            value=date.today(),
            key="index_min_start_date",
            label_visibility="collapsed",
        )
    with controls[4]:
        st.date_input(
            "结束日期",
            value=date.today(),
            key="index_min_end_date",
            label_visibility="collapsed",
        )
    with controls[5]:
        if not get_refresh_token():
            st.warning("未配置DJ_REFRESH_TOKEN/REFRESH_TOKEN，指数分时将使用模拟数据")

    top_container = st.container()
    with top_container:
        row1 = st.columns(3)
        titles_row1 = ["上证指数分时", "深证综指分时", "沪深300分时"]
        for col, title in zip(row1, titles_row1):
            with col:
                with st.container(border=True):
                    render_index_card(ctx, title, adjustable="分时" in title)

        row2 = st.columns(3)
        titles_row2 = ["创业板指分时", "科创50分时", "中证1000分时"]
        for col, title in zip(row2, titles_row2):
            with col:
                with st.container(border=True):
                    render_index_card(ctx, title, adjustable="分时" in title)

        st.write("")
        render_volume_tun_panel(ctx)
