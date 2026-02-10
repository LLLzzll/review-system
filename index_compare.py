from datetime import date

import streamlit as st
from streamlit_echarts import st_echarts
from index_monitor import render_volume_tun_panel


def render_index_card(ctx, title, adjustable=False, height="320px"):
    index_min_map = ctx["INDEX_MIN_MAP"]
    build_line_option = ctx["build_line_option"]
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
                x_data, y_data = generate_period_series(
                    period,
                    start_dt=start_dt,
                    seed_text=f"{base_name}|{period}|{start_dt.isoformat()}|{end_dt.isoformat()}",
                )
    else:
        x_data, y_data = generate_random_series(seed_text=title)
    option = build_line_option(title, x_data, y_data, show_title=False)
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
