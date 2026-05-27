import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import os
import time
from datetime import datetime

# ===================== 页面配置 =====================
st.set_page_config(page_title="无人机智能化应用系统", layout="wide")
st.title("无人机智能化应用系统")
st.caption("分组作业4 - 项目Demo")

# ===================== 障碍物持久化（记忆功能） =====================
CONFIG_FILE = "obstacle_config.json"

def save_obstacles(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_obstacles():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ===================== 初始化 =====================
if "obstacles" not in st.session_state:
    st.session_state.obstacles = load_obstacles()

if "deployed_count" not in st.session_state:
    st.session_state.deployed_count = len(st.session_state.obstacles)

# ✅ 南京科技职业学院 校内正确坐标（GCJ-02）
if "a_lat" not in st.session_state:
    st.session_state.a_lat = 32.2323
    st.session_state.a_lon = 118.7490

if "b_lat" not in st.session_state:
    st.session_state.b_lat = 32.2344
    st.session_state.b_lon = 118.7490

# 点击地图获取坐标
if "click_lat" not in st.session_state:
    st.session_state.click_lat = None
    st.session_state.click_lon = None

# ===================== 侧边栏 =====================
with st.sidebar:
    st.subheader("🧭 功能导航")
    page = st.radio("", ["地图与障碍物管理", "飞行监控"])

# ===================== 页面1：地图与障碍物管理 =====================
if page == "地图与障碍物管理":
    st.subheader("地图显示（OpenStreet / 卫星）")
    st.caption("使用左侧工具栏的【多边形】按钮在地图上圈选障碍物 | 坐标系：GCJ-02")

    col_map, col_ctrl = st.columns([3, 1])

    with col_ctrl:
        st.markdown("### 控制面板")

        # 起点 A
        st.markdown("#### 起点A（GCJ-02）")
        a_lat = st.number_input("A纬度", value=st.session_state.a_lat, format="%.6f")
        a_lon = st.number_input("A经度", value=st.session_state.a_lon, format="%.6f")
        if st.button("设置A点"):
            st.session_state.a_lat = a_lat
            st.session_state.a_lon = a_lon
            st.success("A点已设置")

        # 终点 B
        st.markdown("#### 终点B（GCJ-02）")
        b_lat = st.number_input("B纬度", value=st.session_state.b_lat, format="%.6f")
        b_lon = st.number_input("B经度", value=st.session_state.b_lon, format="%.6f")
        if st.button("设置B点"):
            st.session_state.b_lat = b_lat
            st.session_state.b_lon = b_lon
            st.success("B点已设置")

        # 手动点击地图选点
        st.markdown("#### 🎯 点击地图获取坐标")
        if st.session_state.click_lat:
            st.info(f"纬度：{st.session_state.click_lat:.6f}\n经度：{st.session_state.click_lon:.6f}")
            if st.button("设为起点A"):
                st.session_state.a_lat = st.session_state.click_lat
                st.session_state.a_lon = st.session_state.click_lon
                st.rerun()
            if st.button("设为终点B"):
                st.session_state.b_lat = st.session_state.click_lat
                st.session_state.b_lon = st.session_state.click_lon
                st.rerun()

        # 飞行参数
        st.markdown("### 飞行参数")
        height = st.slider("设定飞行高度(m)", 0, 200, 10)
        st.button("更新参数")

        # 障碍物管理（和PPT完全一样）
        st.markdown("### 障碍物管理")
        st.info(f"共 {len(st.session_state.obstacles)} 个障碍物")
        for i, obs in enumerate(st.session_state.obstacles):
            st.write(f"障碍物{i+1}：{len(obs['coords'])}个顶点")

        # 按钮样式完全按PPT
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("保存到文件"):
                save_obstacles(st.session_state.obstacles)
                st.success("已保存")
        with c2:
            if st.button("从文件加载"):
                st.session_state.obstacles = load_obstacles()
                st.rerun()
        with c3:
            if st.button("清除全部"):
                st.session_state.obstacles = []
                save_obstacles([])
                st.rerun()
        with c4:
            if st.button("一键部署"):
                st.session_state.deployed_count = len(st.session_state.obstacles)
                st.success(f"已部署 {st.session_state.deployed_count} 个")

        st.caption(f"配置文件：obstacle_config.json")
        st.caption(f"已绘制：{len(st.session_state.obstacles)} | 已部署：{st.session_state.deployed_count}")

    with col_map:
        # 地图中心（学校正中心）
        m = folium.Map(location=[32.2333, 118.7490], zoom_start=18)

        # 卫星地图 + OpenStreetMap
        folium.TileLayer(
            tiles="https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
            attr="高德卫星", name="卫星实况地图"
        ).add_to(m)

        folium.TileLayer(
            tiles="OpenStreetMap", name="OpenStreetMap"
        ).add_to(m)

        folium.LayerControl().add_to(m)

        # 多边形绘制工具
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

        # 显示已保存的障碍物
        for obs in st.session_state.obstacles:
            folium.Polygon(
                locations=obs["coords"],
                color="red", fill=True, fill_color="red", fill_opacity=0.4
            ).add_to(m)

        # A、B点 + 航线
        folium.Marker([st.session_state.a_lat, st.session_state.a_lon], popup="A", icon=folium.Icon(color="red")).add_to(m)
        folium.Marker([st.session_state.b_lat, st.session_state.b_lon], popup="B", icon=folium.Icon(color="green")).add_to(m)
        folium.PolyLine(
            [[st.session_state.a_lat, st.session_state.a_lon], [st.session_state.b_lat, st.session_state.b_lon]],
            color="blue", weight=3
        ).add_to(m)

        # 显示地图
        map_data = st_folium(m, width=900, height=700)

        # 获取点击坐标
        if map_data and map_data.get("last_clicked"):
            st.session_state.click_lat = map_data["last_clicked"]["lat"]
            st.session_state.click_lon = map_data["last_clicked"]["lng"]

        # 获取圈选的障碍物
        if map_data and map_data.get("last_active_drawing"):
            geo = map_data["last_active_drawing"]
            if geo["geometry"]["type"] == "Polygon":
                coords = [[p[1], p[0]] for p in geo["geometry"]["coordinates"][0]]
                st.session_state.obstacles.append({"coords": coords})
                st.rerun()

# ===================== 页面2：飞行监控（心跳包） =====================
elif page == "飞行监控":
    st.subheader("📡 飞行监控")

    if "heartbeat" not in st.session_state:
        st.session_state.heartbeat = []
        st.session_state.seq = 1
        st.session_state.running = True

    status = "✅ 在线" if st.session_state.running else "❌ 已停止"
    now = datetime.now().strftime("%H:%M:%S")

    st.metric("心跳状态", status)
    st.metric("最后心跳", now)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("开始心跳"):
            st.session_state.running = True
    with col2:
        if st.button("停止心跳"):
            st.session_state.running = False

    if st.session_state.running:
        st.session_state.heartbeat.append({
            "序号": st.session_state.seq,
            "时间": now,
            "电量": "85%",
            "信号": "77%"
        })
        st.session_state.seq += 1
        if len(st.session_state.heartbeat) > 20:
            st.session_state.heartbeat.pop(0)
        time.sleep(1)
        st.rerun()

    st.subheader("心跳数据")
    st.dataframe(st.session_state.heartbeat, use_container_width=True)