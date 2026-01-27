import random

import os
from datetime import date, datetime, timedelta

import requests
import streamlit as st
from streamlit_echarts import st_echarts

BASE_URL = os.getenv("DJ_BASE_URL", "http://dz.szdjct.com").strip()
GET_ACCESS_TOKEN_URL = f"{BASE_URL}/djData/access/getAccessToken"
GET_INDEX_MIN_LIST_URL = f"{BASE_URL}/djData/index/getIndexMinList"
GET_INDEX_DAY_LIST_URL = f"{BASE_URL}/djData/index/getIndexDayList"

INDEX_MIN_MAP = {
    "上证指数": {"code": "000001", "exponentId": 1},
    "深证综指": {"code": "399101", "exponentId": 6},
    "沪深300": {"code": "000300", "exponentId": 3},
    "创业板指": {"code": "399006", "exponentId": 11},
    "科创50": {"code": "000688", "exponentId": 10},
    "中证1000": {"code": "000852", "exponentId": 12},
}


def read_simple_config(config_path):
    values = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("#") or line.startswith(";"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (
                    len(value) >= 2
                    and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"))
                ):
                    value = value[1:-1]
                if key:
                    values[key] = value
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return values


def get_refresh_token():
    token = os.getenv("DJ_REFRESH_TOKEN") or os.getenv("REFRESH_TOKEN")
    if token:
        return token
    try:
        if "DJ_REFRESH_TOKEN" in st.secrets:
            return st.secrets["DJ_REFRESH_TOKEN"]
        if "REFRESH_TOKEN" in st.secrets:
            return st.secrets["REFRESH_TOKEN"]
    except Exception:
        pass

    config_path = os.path.join(os.path.dirname(__file__), ".config")
    config_values = read_simple_config(config_path)
    for key in (
        "DJ_REFRESH_TOKEN",
        "REFRESH_TOKEN",
        "refresh_token",
        "dj_refresh_token",
        "Refresh-Token",
        "refreshToken",
    ):
        value = config_values.get(key)
        if value:
            return value
    return None


def fetch_access_token(refresh_token):
    headers = {"Refresh-Token": refresh_token, "Accept": "application/json"}
    resp = requests.get(GET_ACCESS_TOKEN_URL, headers=headers, timeout=15)
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getAccessToken失败")
    payload = data.get("data") or {}
    token = payload.get("Access-Token") or payload.get("accessToken") or payload.get("token")
    if not token:
        raise RuntimeError("getAccessToken返回缺少Access-Token")
    return token


def get_access_token():
    refresh_token = get_refresh_token()
    if not refresh_token:
        raise RuntimeError("未配置refresh-token")
    if st.session_state.get("dj_access_token"):
        return st.session_state["dj_access_token"]
    token = fetch_access_token(refresh_token)
    st.session_state["dj_access_token"] = token
    return token


@st.cache_data(ttl=60)
def fetch_index_min_list(start_date_str, end_date_str, exponent_id, period, field_list):
    access_token = get_access_token()
    headers = {"Access-Token": access_token, "Accept": "application/json"}
    params = {
        "startDate": start_date_str,
        "endDate": end_date_str,
        "exponentId": exponent_id,
        "period": period,
        "fieldList": field_list,
    }
    resp = requests.get(GET_INDEX_MIN_LIST_URL, headers=headers, params=params, timeout=20)
    data = resp.json()
    if data.get("code") == 401:
        refresh_token = get_refresh_token()
        if not refresh_token:
            raise RuntimeError("refresh-token失效且无法刷新")
        new_token = fetch_access_token(refresh_token)
        st.session_state["dj_access_token"] = new_token
        headers["Access-Token"] = new_token
        resp = requests.get(
            GET_INDEX_MIN_LIST_URL, headers=headers, params=params, timeout=20
        )
        data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getIndexMinList失败")
    return data.get("data") or []


@st.cache_data(ttl=300)
def fetch_index_day_list(start_date_str, end_date_str, exponent_ids_str, field_list):
    access_token = get_access_token()
    headers = {"Access-Token": access_token, "Accept": "application/json"}
    exponent_ids_str = (exponent_ids_str or "").strip()
    if not exponent_ids_str:
        raise RuntimeError("exponentIdList不能为空")
    params = {
        "startDate": start_date_str,
        "endDate": end_date_str,
        "exponentIdList": exponent_ids_str,
        "fieldList": field_list,
    }
    resp = requests.get(GET_INDEX_DAY_LIST_URL, headers=headers, params=params, timeout=25)
    data = resp.json()
    if data.get("code") == 401:
        refresh_token = get_refresh_token()
        if not refresh_token:
            raise RuntimeError("refresh-token失效且无法刷新")
        new_token = fetch_access_token(refresh_token)
        st.session_state["dj_access_token"] = new_token
        headers["Access-Token"] = new_token
        resp = requests.get(
            GET_INDEX_DAY_LIST_URL, headers=headers, params=params, timeout=25
        )
        data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getIndexDayList失败")
    return data.get("data") or []


def apply_index_date_preset():
    preset = (st.session_state.get("index_date_preset") or "").strip()
    today = date.today()
    if preset == "今日":
        start_dt = today
        end_dt = today
    elif preset == "昨日":
        d = today - timedelta(days=1)
        start_dt = d
        end_dt = d
    elif preset == "近一周":
        start_dt = today - timedelta(days=6)
        end_dt = today
    else:
        return
    st.session_state["index_min_start_date"] = start_dt
    st.session_state["index_min_end_date"] = end_dt


def get_trading_minutes_of_day(period_minutes):
    try:
        step = int(period_minutes or 1)
    except Exception:
        step = 1
    step = max(1, step)


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


def get_first_value(d, keys):
    if not isinstance(d, dict):
        return None
    for key in keys:
        if key in d and d.get(key) is not None:
            return d.get(key)
    return None


def format_minute_x(x_val, start_dt=None):
    if x_val is None:
        return None
    text = str(x_val).strip()
    if not text:
        return None

    if " " in text and ":" in text:
        parts = text.split(" ", 1)
        if len(parts) == 2:
            return f"{parts[0]}\n{parts[1]}"
        return text
    if "T" in text and "-" in text and ":" in text:
        parts = text.split("T", 1)
        if len(parts) == 2:
            time_part = parts[1].split(".", 1)[0]
            if len(time_part) >= 5:
                time_part = time_part[:5]
            return f"{parts[0]}\n{time_part}"
        return text
    if "-" in text and ":" in text:
        return text.replace(" ", "\n")
    if ":" in text:
        return text
    if len(text) == 3 and text.isdigit():
        hh = f"0{text[0]}"
        mm = text[1:]
        return f"{hh}:{mm}"
    if len(text) == 4 and text.isdigit():
        hh = text[:2]
        mm = text[2:]
        return f"{hh}:{mm}"
    if len(text) == 6 and text.isdigit():
        hh = text[:2]
        mm = text[2:4]
        ss = text[4:]
        return f"{hh}:{mm}:{ss}"
    return text


def parse_indicator_day_series(data_list, value_key, start_dt=None):
    x_data = []
    y_data = []
    value_keys = value_key if isinstance(value_key, (list, tuple)) else [value_key]
    for idx, item in enumerate(data_list):
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
        if x_val is None:
            if start_dt is not None:
                try:
                    x_val = (start_dt + timedelta(days=idx)).isoformat()
                except Exception:
                    x_val = idx
            else:
                x_val = idx
        y_val = get_first_value(item, value_keys)
        if y_val is None:
            continue
        x_data.append(x_val)
        y_data.append(y_val)
    return x_data, y_data


def parse_index_min_series(data_list, start_dt=None, period_minutes=None):
    x_data = []
    y_data = []
    trading_minutes = None
    if start_dt is not None and period_minutes:
        trading_minutes = get_trading_minutes_of_day(period_minutes)
        if not trading_minutes:
            trading_minutes = None
    for idx, item in enumerate(data_list):
        if not isinstance(item, dict):
            continue
        x_val = get_first_value(
            item,
            [
                "dateTime",
                "datetime",
                "tradeDateTime",
                "tradeDatetime",
                "tradeTime",
                "time",
                "tradeDate",
                "date",
            ],
        )
        x_text = format_minute_x(x_val, start_dt=start_dt)
        if x_text is not None and ":" in x_text and "-" not in x_text and "\n" not in x_text:
            date_val = get_first_value(item, ["tradeDate", "trade_date", "date"])
            date_text = None
            if date_val is not None:
                dt = str(date_val).strip()
                if len(dt) == 8 and dt.isdigit():
                    date_text = f"{dt[:4]}-{dt[4:6]}-{dt[6:]}"
                elif " " in dt:
                    date_text = dt.split(" ", 1)[0]
                elif "T" in dt:
                    date_text = dt.split("T", 1)[0]
                else:
                    date_text = dt
            if not date_text and start_dt is not None:
                date_text = start_dt.isoformat()
            if date_text:
                x_text = f"{date_text}\n{x_text}"
        if x_text is None and start_dt is not None and trading_minutes is not None:
            try:
                day_offset = idx // len(trading_minutes)
                minute_of_day = trading_minutes[idx % len(trading_minutes)]
                trading_date = add_trading_days(start_dt, day_offset) or start_dt
                ts = datetime.combine(trading_date, datetime.min.time()) + timedelta(
                    minutes=minute_of_day
                )
                x_text = ts.strftime("%Y-%m-%d\n%H:%M")
            except Exception:
                x_text = None
        if x_text is None:
            x_text = idx
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
        x_data.append(x_text)
        y_data.append(y_val)
    return x_data, y_data


def generate_random_series(length=30, base=3000, fluctuation=50):
    x_data = list(range(length))
    value = base
    y_data = []
    for _ in x_data:
        value += random.randint(-fluctuation, fluctuation)
        y_data.append(value)
    return x_data, y_data


def generate_period_series(period, start_dt=None, base=3000, fluctuation=50):
    period_length = {
        "1分钟": 60,
        "5分钟": 48,
        "30分钟": 32,
        "60分钟": 24,
    }.get(period, 30)
    step_minutes = {"1分钟": 1, "5分钟": 5, "30分钟": 30, "60分钟": 60}.get(period, 1)
    if start_dt is None:
        start_dt = date.today()
    trading_minutes = get_trading_minutes_of_day(step_minutes)
    x_data = []
    for i in range(period_length):
        day_offset = i // len(trading_minutes)
        minute_of_day = trading_minutes[i % len(trading_minutes)]
        trading_date = add_trading_days(start_dt, day_offset) or start_dt
        ts = datetime.combine(trading_date, datetime.min.time()) + timedelta(
            minutes=minute_of_day
        )
        x_data.append(ts.strftime("%Y-%m-%d\n%H:%M"))

    _, y_data = generate_random_series(length=period_length, base=base, fluctuation=fluctuation)
    return x_data, y_data


def build_line_option(title, x_data=None, y_data=None, show_title=True):
    if x_data is None or y_data is None:
        x_data, y_data = generate_random_series()
    option = {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "boundaryGap": False,
            "axisLabel": {"hideOverlap": True, "fontSize": 10},
        },
        "yAxis": {"type": "value", "scale": True},
        "grid": {"left": 40, "right": 10, "top": 40, "bottom": 56, "containLabel": True},
        "series": [
            {
                "type": "line",
                "data": y_data,
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 2},
                "areaStyle": {
                    "opacity": 0.3,
                },
            }
        ],
    }
    if show_title:
        option["title"] = {
            "text": title,
            "left": "center",
            "textStyle": {"fontSize": 14},
        }
    return option


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
                "data": [
                    {"value": v, "itemStyle": {"color": c}} for v, c in zip(values, colors)
                ],
                "barWidth": "60%",
            }
        ],
    }
    if show_title:
        option["title"] = {
            "text": title,
            "left": "center",
            "textStyle": {"fontSize": 14},
        }
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


def render_monitor_overview():
    row = st.columns(3)
    panels = ["价格追踪与当日趋势预测", "成交量能变动", "大小风格走势"]
    for col, title in zip(row, panels):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="height:240px; display:flex; align-items:center; justify-content:center;">
                      <div style="font-size:16px; font-weight:800; color:#666666; text-align:center;">
                        {title}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


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
        base = 3100
        price = []
        value = base
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
                },
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
            categories, values, colors = generate_distribution_data(
                f"{metric}-{scope}-全市场"
            )
            option = build_bar_option("涨跌分布", categories, values, colors, show_title=False)
            st_echarts(option, height="280px", key="dist_chart")
            stats = [("上涨", u), ("平盘", flat), ("停牌", halt), ("下跌", d)]
            card_html_list = []
            for name, value in stats:
                card_html_list.append(
                    f'''
<div style="flex:1;background:#f5f5f5;border-radius:10px;padding:6px 12px;text-align:center;font-size:12px;min-width:0;">
  <div style="font-size:14px;font-weight:700;color:#111827;white-space:nowrap;">{name} {value}家</div>
</div>
'''
                )
            cards_html = "".join(card_html_list)
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


def render_card(title, height="260px"):
    x_data, y_data = generate_random_series()
    option = build_line_option(title, x_data, y_data, show_title=True)
    st_echarts(option, height=height, key=title)


def render_index_card(title, adjustable=False, height="320px"):
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
        cfg = INDEX_MIN_MAP.get(base_name)
        start_dt = st.session_state.get("index_min_start_date") or date.today()
        end_dt = st.session_state.get("index_min_end_date") or date.today()
        if period == "日线":
            if cfg:
                try:
                    data_list = fetch_index_day_list(
                        start_dt.isoformat(),
                        end_dt.isoformat(),
                        str(cfg["exponentId"]),
                        "open,high,low,close",
                    )
                    if not data_list:
                        st.caption(f"{base_name} 日线接口返回为空")
                        return
                    x_data, y_data = parse_indicator_day_series(
                        data_list,
                        ["close", "closePrice", "close_price", "price"],
                        start_dt=start_dt,
                    )
                    if not y_data:
                        x_data, y_data = parse_indicator_day_series(
                            data_list,
                            ["open", "openPrice", "open_price"],
                            start_dt=start_dt,
                        )
                    if not x_data or not y_data:
                        st.caption(f"{base_name} 日线数据缺少可绘制字段")
                        return
                except Exception as e:
                    st.caption(f"{base_name} 日线数据获取失败：{e}")
                    return
            else:
                st.caption(f"{base_name} 缺少指数映射")
                return
        else:
            period_int = {"1分钟": 1, "5分钟": 5, "30分钟": 30, "60分钟": 60}.get(period, 1)
            field_list = "time,open,high,low,close"
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
                x_data, y_data = generate_period_series(period, start_dt=start_dt)
    else:
        x_data, y_data = generate_random_series()
    option = build_line_option(title, x_data, y_data, show_title=False)
    st_echarts(option, height=height, key=option_key)


def set_active_tab(name):
    st.session_state["tab"] = name


def render_layout():
    st.set_page_config(page_title="指标监控", layout="wide")

    st.markdown(
        """
        <style>
          section[data-testid="stSidebar"] details summary p{
            text-align: center;
            width: 100%;
            font-size: 20px;
            font-weight: 700;
          }
          section[data-testid="stSidebar"] div.stButton > button{
            width: 100%;
          }
          section[data-testid="stSidebar"] div.stButton > button p{
            text-align: center;
            width: 100%;
            font-size: 14px;
          }
          div[data-testid="stMetric"]{
            background: #f5f5f5;
            border-radius: 10px;
            padding: 6px 10px;
            margin-bottom: 8px;
          }
          div[data-testid="stMetric"] label{
            font-size: 12px;
          }
          div[data-testid="stMetricValue"]{
            font-size: 20px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 维度")
        tabs = ["指数", "板块", "个股", "资金"]
        if "tab" not in st.session_state:
            st.session_state["tab"] = "指数"

        subtab_map = {
            "指数": ["指数同比", "指数监控"],
            "板块": ["行业板块", "概念板块", "地区板块", "主题板块", "风格板块"],
            "个股": ["沪市个股", "深市个股", "创业板个股", "科创板个股", "其他市场"],
            "资金": ["北向资金", "南向资金", "场内资金", "场外资金", "其他资金"],
        }

        for name in tabs:
            subtabs = subtab_map.get(name, [])
            expanded = name == st.session_state["tab"]
            with st.expander(name, expanded=expanded):
                if subtabs:
                    subtab_key = f"subtab_{name}"
                    if subtab_key not in st.session_state:
                        st.session_state[subtab_key] = subtabs[0]
                    for sub in subtabs:
                        if st.button(
                            sub,
                            key=f"{subtab_key}_{sub}",
                            use_container_width=True,
                        ):
                            st.session_state[subtab_key] = sub
                            set_active_tab(name)

    tab = st.session_state["tab"]
    current_subtab = st.session_state.get(f"subtab_{tab}")

    if tab == "指数":
        if current_subtab == "指数监控":
            title_text = "指数监控"
            desc_text = "结合市场热点对指数信息监控"
        elif current_subtab == "指数同比":
            title_text = "指数同比"
            desc_text = "A股市场复盘系统-指数同比对比"
        else:
            title_text = "大盘指数"
            desc_text = "展示的是指数数据" if not current_subtab else f"展示的是指数 - {current_subtab}"
        st.markdown(
            f"""
            <div style="padding: 10px 24px; border-bottom: 1px solid #e5e5e5; background-color: #ffffff;">
                <div style="font-size: 24px; font-weight: 1000;">{title_text}</div>
                <div style="font-size: 14px; color: #888888; margin-top: 6px;">
                    {desc_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        if current_subtab == "指数监控":
            render_monitor_overview()
            st.write("")
            left, right = st.columns(2)
            with left:
                render_divergence_signal()
            with right:
                render_stock_distribution()
        else:
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
                            render_index_card(title, adjustable="分时" in title)

                row2 = st.columns(3)
                titles_row2 = ["创业板指分时", "科创50分时", "中证1000分时"]
                for col, title in zip(row2, titles_row2):
                    with col:
                        with st.container(border=True):
                            render_index_card(title, adjustable="分时" in title)

            st.write("")

            bottom_container = st.container()
            with bottom_container:
                row3 = st.columns(2)
                titles_row3 = [
                    "成交量、换手率监控表",
                    "成交金额与异动个股联动监控",
                ]
                for col, title in zip(row3, titles_row3):
                    with col:
                        with st.container(border=True):
                            render_card(title, height="320px")
    else:
        st.write("")
        subtitle = f"{tab} - {current_subtab}" if current_subtab else tab
        st.markdown(f"### {subtitle} 页面布局待定")


def main():
    render_layout()


if __name__ == "__main__":
    main()

