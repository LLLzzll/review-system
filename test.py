import random

import streamlit as st
from streamlit_echarts import st_echarts


def generate_random_series(length=30, base=3000, fluctuation=50):
    x_data = list(range(length))
    value = base
    y_data = []
    for _ in x_data:
        value += random.randint(-fluctuation, fluctuation)
        y_data.append(value)
    return x_data, y_data


def generate_period_series(period, base=3000, fluctuation=50):
    period_length = {
        "1分钟": 60,
        "5分钟": 48,
        "15分钟": 32,
        "60分钟": 24,
        "日线": 30,
    }.get(period, 30)
    return generate_random_series(length=period_length, base=base, fluctuation=fluctuation)


def build_line_option(title, x_data=None, y_data=None, show_title=True):
    if x_data is None or y_data is None:
        x_data, y_data = generate_random_series()
    option = {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
        "yAxis": {"type": "value", "scale": True},
        "grid": {"left": 40, "right": 10, "top": 40, "bottom": 30},
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


def render_card(title, height="260px"):
    x_data, y_data = generate_random_series()
    option = build_line_option(title, x_data, y_data, show_title=True)
    st_echarts(option, height=height, key=title)


def render_index_card(title, adjustable=False, height="260px"):
    option_key = f"{title}_option" if adjustable else title
    period_key = f"{title}_period"
    header_left, header_right = st.columns([3, 1])
    period = None
    if adjustable:
        with header_right:
            period = st.selectbox(
                "周期",
                ["1分钟", "5分钟", "15分钟", "60分钟", "日线"],
                index=0,
                key=period_key,
                label_visibility="collapsed",
            )
    with header_left:
        st.markdown(f"**{title}**")
    if adjustable and period is not None:
        x_data, y_data = generate_period_series(period)
    else:
        x_data, y_data = generate_random_series()
    option = build_line_option(title, x_data, y_data, show_title=False)
    st_echarts(option, height=height, key=option_key)


def render_adjustable_card(title, height="260px"):
    option_key = f"{title}_option"
    period_key = f"{title}_period"
    left, right = st.columns([2, 1])
    with right:
        period = st.selectbox(
            "",
            ["1分钟", "5分钟", "15分钟", "60分钟", "日线"],
            index=0,
            key=period_key,
        )
    with left:
        st.markdown(f"**{title} - {period}**")
    x_data, y_data = generate_period_series(period)
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
            "指数": ["全部指数", "大盘指数", "行业指数", "行业指数1", "行业指数2"],
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
                    current_sub = st.session_state[subtab_key]
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
        desc_text = "展示的是指数数据" if not current_subtab else f"展示的是指数 - {current_subtab}"
        st.markdown(
            f"""
            <div style="padding: 10px 24px; border-bottom: 1px solid #e5e5e5; background-color: #ffffff;">
                <div style="font-size: 24px; font-weight: 1000;">指数监控</div>
                <div style="font-size: 14px; color: #888888; margin-top: 6px;">
                    {desc_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        top_container = st.container()
        with top_container:
            row1 = st.columns(3)
            titles_row1 = ["上证指数分时", "深证成指分时", "沪深300分时"]
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

