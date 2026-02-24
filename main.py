import random

import os
from datetime import date, datetime, timedelta

import requests
import streamlit as st

from index_compare import render_index_compare
from index_monitor import render_index_monitor

BASE_URL = os.getenv("DJ_BASE_URL", "http://dz.szdjct.com").strip()
GET_ACCESS_TOKEN_URL = f"{BASE_URL}/djData/access/getAccessToken"
GET_INDEX_MIN_LIST_URL = f"{BASE_URL}/djData/index/getIndexMinList"
GET_INDEX_DAY_LIST_URL = f"{BASE_URL}/djData/index/getIndexDayList"
GET_STOCK_LIST_URL = f"{BASE_URL}/djData/stock/getAllStockListByDateAndFields"

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
    resp = requests.get(GET_INDEX_MIN_LIST_URL, headers=headers, params=params, timeout=10)
    data = resp.json()
    if isinstance(data, dict) and data.get("code") == 401:
        refresh_token = get_refresh_token()
        if not refresh_token:
            raise RuntimeError("refresh-token失效且无法刷新")
        new_token = fetch_access_token(refresh_token)
        st.session_state["dj_access_token"] = new_token
        headers["Access-Token"] = new_token
        resp = requests.get(
            GET_INDEX_MIN_LIST_URL, headers=headers, params=params, timeout=10
        )
        data = resp.json()
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getIndexMinList失败")
    payload = data.get("data")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("list", "rows", "items", "data"):
            if isinstance(payload.get(key), list):
                return payload.get(key)
    for key in ("list", "rows", "items", "result"):
        if isinstance(data.get(key), list):
            return data.get(key)
    return []


@st.cache_data(ttl=900)
def fetch_stock_list_by_date_and_fields(deal_date_str, field_list, start_with=None):
    access_token = get_access_token()
    headers = {"Access-Token": access_token, "Accept": "application/json"}
    params = {"dealDate": deal_date_str, "fieldList": field_list}
    if start_with is not None:
        params["startWith"] = start_with
    resp = requests.get(GET_STOCK_LIST_URL, headers=headers, params=params, timeout=25)
    data = resp.json()
    if isinstance(data, dict) and data.get("code") == 401:
        refresh_token = get_refresh_token()
        if not refresh_token:
            raise RuntimeError("refresh-token失效且无法刷新")
        new_token = fetch_access_token(refresh_token)
        st.session_state["dj_access_token"] = new_token
        headers["Access-Token"] = new_token
        resp = requests.get(GET_STOCK_LIST_URL, headers=headers, params=params, timeout=25)
        data = resp.json()
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getAllStockListByDateAndFields失败")
    payload = data.get("data")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("list", "rows", "items", "data"):
            if isinstance(payload.get(key), list):
                return payload.get(key)
    for key in ("list", "rows", "items", "result"):
        if isinstance(data.get(key), list):
            return data.get(key)
    return []

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
    if isinstance(data, dict) and data.get("code") == 401:
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
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if data.get("code") != 200:
        raise RuntimeError(data.get("msg") or data.get("message") or "getIndexDayList失败")
    payload = data.get("data")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("list", "rows", "items", "data"):
            if isinstance(payload.get(key), list):
                return payload.get(key)
    for key in ("list", "rows", "items", "result"):
        if isinstance(data.get(key), list):
            return data.get(key)
    return []


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
                    x_val = (add_trading_days(start_dt, idx) or start_dt).isoformat()
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


@st.cache_data(ttl=3600)
def generate_random_series(length=30, base=3000, fluctuation=50, seed_text="default"):
    rnd = random.Random(str(seed_text))
    x_data = list(range(length))
    value = base
    y_data = []
    for _ in x_data:
        value += rnd.randint(-fluctuation, fluctuation)
        y_data.append(value)
    return x_data, y_data


@st.cache_data(ttl=3600)
def generate_period_series(period, start_dt=None, base=3000, fluctuation=50, seed_text="default"):
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

    _, y_data = generate_random_series(
        length=period_length,
        base=base,
        fluctuation=fluctuation,
        seed_text=f"{seed_text}|{period}|{start_dt}|{base}|{fluctuation}",
    )
    return x_data, y_data


def build_line_option(title, x_data=None, y_data=None, show_title=True):
    if x_data is None or y_data is None:
        x_data, y_data = generate_random_series(seed_text=title)
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


def set_active_tab(name):
    st.session_state["tab"] = name


def render_layout():
    st.set_page_config(page_title="指标监控", layout="wide")

    st.markdown(
        """
        <style>
          header[data-testid="stHeader"]{
            height: 0;
            visibility: hidden;
          }
          div.block-container{
            padding-top: 0.6rem;
          }
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

        ctx = {
            "INDEX_MIN_MAP": INDEX_MIN_MAP,
            "apply_index_date_preset": apply_index_date_preset,
            "build_line_option": build_line_option,
            "fetch_index_day_list": fetch_index_day_list,
            "fetch_index_min_list": fetch_index_min_list,
            "fetch_stock_list_by_date_and_fields": fetch_stock_list_by_date_and_fields,
            "generate_period_series": generate_period_series,
            "generate_random_series": generate_random_series,
            "get_refresh_token": get_refresh_token,
            "parse_indicator_day_series": parse_indicator_day_series,
            "parse_index_min_series": parse_index_min_series,
        }

        if current_subtab == "指数监控":
            render_index_monitor(ctx)
        else:
            render_index_compare(ctx)
    else:
        st.write("")
        subtitle = f"{tab} - {current_subtab}" if current_subtab else tab
        st.markdown(f"### {subtitle} 页面布局待定")


def main():
    render_layout()


if __name__ == "__main__":
    main()

