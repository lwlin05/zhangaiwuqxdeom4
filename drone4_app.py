import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import os
import math
import time
from datetime import datetime
import pandas as pd

# ===================== 1. 页面基础配置 =====================
st.set_page_config(page_title="无人机智能化应用", layout="wide")

# ===================== 2. GCJ-02 坐标系转换函数 =====================
def wgs84_to_gcj02(lon, lat):
    a = 6378245.0
    ee = 0.0066934216229659433
    dLat = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
    dLon = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * math.pi / 180.0)
    dLon = (dLon * 180.0) / (a / sqrtMagic * math.cos(radLat) * math.pi / 180.0)
    return lon + dLon, lat + dLat

def gcj02_to_wgs84(lon, lat):
    lon -= 0.0065
    lat -= 0.006
    return lon, lat

# ===================== 3. 障碍物持久化（记忆功能，与PPT一致） =====================
CONFIG_FILE = "obstacle_config.json"

def save_obstacles(obstacles):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(obstacles, f, ensure_ascii=False, indent=2)

def load_obstacles():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ===================== 4. 全局状态初始化 =====================
if "obstacles" not in st.session_state:
    st.session_state.obstacles = load_obstacles()
if "deployed_obstacles" not in st.session_state:
    st.session_state.deployed_obstacles = len(st.session_state.obstacles)

# 南京科技职业学院 校内 GCJ-02 精准坐标（与PPT截图一致）
if "a_lat" not in st.session_state:
    st.session_state.a_lat = 32.2323
    st.session_state.a_lon = 118.7490
    st.session_state.b_lat = 32.2344
    st.session_state.b_lon = 118.7490

# 地图点击拾取的临时坐标
if "click_lat" not in st.session_state:
    st.session_state.click_lat = None
    st.session_state.click_lon = None

# 心跳包状态
if "heartbeat" not in st.session_state:
    st.session_state.heartbeat = []
    st.session_state.seq = 0
    st.session_state.running = True
    st.session_state.last_recv = time.time()

# ===================== 5. 侧边导航栏 =====================
with st.sidebar:
    st.title("🧭 导航")
    page = st.radio("功能页面", ["🗺️ 航线规划", "📡 飞行监控"], index=0)

# ===================== 6. 航线规划页面（与PPT界面一致） =====================
if page == "🗺️ 航线规划":
    st.title("分组作业4-项目Demo")
    st.subheader("🗺️ 卫星地图 + 障碍物圈选 + 手动选坐标")

    col_map, col_ctrl = st.columns([3, 1])

    # -------- 右侧控制面板（完全还原PPT） --------
    with col_ctrl:
        st.markdown("### ⚙️ 控制面板")
        st.markdown("**输入坐标系: GCJ-02**")

        # 起点A（与PPT样式一致）
        st.markdown("##### 📍 起点A")
        a_lat_in = st.number_input("纬度", value=st.session_state.a_lat, format="%.6f", key="a_lat_in")
        a_lon_in = st.number_input("经度", value=st.session_state.a_lon, format="%.6f", key="a_lon_in")
        if st.button("设置A点", key="set_a"):
            st.session_state.a_lat = a_lat_in
            st.session_state.a_lon = a_lon_in
            st.success("✅ A点已设")

        # 终点B（与PPT样式一致）
        st.markdown("##### 📍 终点B")
        b_lat_in = st.number_input("纬度", value=st.session_state.b_lat, format="%.6f", key="b_lat_in")
        b_lon_in = st.number_input("经度", value=st.session_state.b_lon, format="%.6f", key="b_lon_in")
        if st.button("设置B点", key="set_b"):
            st.session_state.b_lat = b_lat_in
            st.session_state.b_lon = b_lon_in
            st.success("✅ B点已设")

        st.divider()

        # 地图点击拾取坐标（手动选坐标功能）
        st.markdown("##### 🎯 地图点击拾取坐标")
        if st.session_state.click_lat and st.session_state.click_lon:
            st.info(f"当前拾取坐标：\n纬度 {st.session_state.click_lat:.6f}\n经度 {st.session_state.click_lon:.6f}")
            if st.button("设为 A点", key="click_to_a"):
                st.session_state.a_lat = st.session_state.click_lat
                st.session_state.a_lon = st.session_state.click_lon
                st.success("✅ 已将点击位置设为 A点")
                st.rerun()
            if st.button("设为 B点", key="click_to_b"):
                st.session_state.b_lat = st.session_state.click_lat
                st.session_state.b_lon = st.session_state.click_lon
                st.success("✅ 已将点击位置设为 B点")
                st.rerun()
        else:
            st.warning("请在左侧地图上点击任意位置获取坐标")

        st.divider()

        # 飞行参数（与PPT一致）
        st.markdown("##### ✈️ 飞行参数")
        st.slider("设定飞行高度(m)", 0, 200, 10, key="fly_height")

        st.divider()

        # --------------------------
        # 障碍物配置持久化（与PPT按钮样式完全一致）
        # --------------------------
        st.markdown("### 🚀 障碍物配置持久化")
        # 按钮行，与PPT对齐
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("💾 保存到文件", use_container_width=True):
                save_obstacles(st.session_state.obstacles)
                st.success("✅ 已保存到 obstacle_config.json")
        with col2:
            if st.button("📂 从文件加载", use_container_width=True):
                st.session_state.obstacles = load_obstacles()
                st.success("✅ 已加载障碍物配置")
        with col3:
            if st.button("🗑️ 清除全部", use_container_width=True):
                st.session_state.obstacles = []
                save_obstacles([])
                st.success("✅ 已清空所有障碍物")
        with col4:
            if st.button("🚀 一键部署", use_container_width=True):
                st.session_state.deployed_obstacles = len(st.session_state.obstacles)
                st.success("✅ 已部署所有障碍物")

        # 文件状态显示（与PPT一致）
        st.markdown("### 📁 文件状态")
        st.info(f"已绘制: {len(st.session_state.obstacles)} 个 | 已部署: {st.session_state.deployed_obstacles} 个")
        st.code("obstacle_config.json", language="text")

    # -------- 左侧地图区域（与PPT一致） --------
    with col_map:
        # 地图中心：南京科技职业学院
        school_center = [32.2334, 118.7490]
        m = folium.Map(location=school_center, zoom_start=17, tiles=None)

        # 图层1：高德卫星实况地图（PPT要求）
        folium.TileLayer(
            tiles="https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
            name="卫星实况地图",
            attr="高德地图 | OpenStreetMap"
        ).add_to(m)

        # 图层2：OpenStreetMap（PPT要求）
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="OpenStreetMap"
        ).add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)

        # 多边形圈选工具（PPT要求）
        draw = Draw(
            draw_options={
                "polygon": True,
                "polyline": False,
                "rectangle": False,
                "circle": False,
                "marker": False
            }
        )
        draw.add_to(m)

        # 绘制已保存的障碍物（记忆功能）
        for obs in st.session_state.obstacles:
            folium.Polygon(
                locations=obs["coords"],
                color="red", fill=True, fill_color="red", fill_opacity=0.5
            ).add_to(m)

        # 绘制起点A、终点B + 飞行航线（与PPT一致）
        folium.Marker(
            [st.session_state.a_lat, st.session_state.a_lon],
            popup="起点A", icon=folium.Icon(color="red")
        ).add_to(m)
        folium.Marker(
            [st.session_state.b_lat, st.session_state.b_lon],
            popup="终点B", icon=folium.Icon(color="green")
        ).add_to(m)
        folium.PolyLine(
            [[st.session_state.a_lat, st.session_state.a_lon],
             [st.session_state.b_lat, st.session_state.b_lon]],
            color="blue", weight=3, dash_array="5,5"
        ).add_to(m)

        # 渲染地图，并获取点击坐标和圈选结果
        map_result = st_folium(m, width=900, height=700)

        # 捕获地图点击坐标（手动选坐标）
        if map_result and map_result.get("last_clicked"):
            click_pos = map_result["last_clicked"]
            st.session_state.click_lat = click_pos["lat"]
            st.session_state.click_lon = click_pos["lng"]

        # 捕获新绘制的多边形障碍物
        if map_result and map_result.get("last_active_drawing"):
            geo_data = map_result["last_active_drawing"]
            if geo_data["geometry"]["type"] == "Polygon":
                coords = [[p[1], p[0]] for p in geo_data["geometry"]["coordinates"][0]]
                exist = any(item["coords"] == coords for item in st.session_state.obstacles)
                if not exist:
                    st.session_state.obstacles.append({"coords": coords, "name": f"障碍物{len(st.session_state.obstacles)+1}"})
                    st.rerun()

    st.divider()
    st.caption("操作说明：1. 右侧输入坐标设置点位  2. 点击地图拾取坐标  3. 左上角多边形工具圈选障碍物")

# ===================== 7. 飞行监控页面（心跳包，与PPT一致） =====================
elif page == "📡 飞行监控":
    st.title("📡 飞行监控 - 无人机心跳包")
    INTERVAL = 1
    TIMEOUT = 3

    # 生成心跳数据
    if st.session_state.running:
        st.session_state.seq += 1
        now = time.time()
        st.session_state.last_recv = now
        st.session_state.heartbeat.append({
            "序号": st.session_state.seq,
            "时间": datetime.fromtimestamp(now).strftime("%H:%M:%S")
        })
        if len(st.session_state.heartbeat) > 50:
            st.session_state.heartbeat.pop(0)

    # 心跳超时判断
    gap = time.time() - st.session_state.last_recv
    if gap > TIMEOUT:
        st.error(f"⚠️ 连接超时！已 {gap:.1f} 秒未收到心跳")
    else:
        st.success(f"✅ 心跳正常 | 上次心跳 {gap:.1f} 秒前")

    # 数据表格 + 趋势图
    st.subheader("📋 心跳包数据")
    df_heart = pd.DataFrame(st.session_state.heartbeat)
    st.dataframe(df_heart, use_container_width=True)

    st.subheader("📈 心跳趋势图")
    if not df_heart.empty:
        st.line_chart(df_heart, x="时间", y="序号")

    # 心跳启停按钮
    c1, c2 = st.columns(2)
    with c1:
        if st.button("开始心跳", key="heart_start"):
            st.session_state.running = True
    with c2:
        if st.button("停止心跳", key="heart_stop"):
            st.session_state.running = False

    if st.session_state.running:
        time.sleep(INTERVAL)
        st.rerun()