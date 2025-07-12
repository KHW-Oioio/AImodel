import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from PIL import Image, ImageDraw
import io
import base64
import requests
import urllib3
import tempfile

# SSL 경고 억제
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="CCTV 비정상주행 감지 시스템",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

CCTV_STREAM_URL = "https://www.utic.go.kr/jsp/map/cctvStream.jsp?cctvid=E970102&cctvname=%25EB%25B0%2598%25ED%258F%25AC%25EB%258C%2580%25EA%25B5%2590~%25ED%2595%259C%25EB%2582%25A83&kind=EC&cctvip=undefined&cctvch=53&id=460&cctvpasswd=undefined&cctvport=undefined&minX=126.94439014863138&minY=37.48157205124353&maxX=127.16458223998221&maxY=37.56413189592257"
ALTERNATIVE_CCTV_URLS = []


def main():
    st.title("🚗 CCTV 비정상주행 감지 시스템")
    st.markdown("---")
    st.info("ℹ️ 영상 업로드 후 바로 재생 (Cloud 환경 호환)")
    config = setup_sidebar()
    placeholders = setup_main_dashboard()
    run_monitoring(config, placeholders)

def setup_sidebar():
    st.sidebar.title("🚗 모니터링 설정")
    st.sidebar.info("ℹ️ 영상 업로드 후 바로 재생 모드")
    camera_options = {
        "실제 CCTV 스트림": "cctv_stream",
        "영상 파일 업로드": "video_upload",
        "웹캠 연결": "webcam",
        "데모 모드": "demo",
        "카메라 1": 0,
        "카메라 2": 1,
        "카메라 3": 2,
        "테스트 비디오": "test_video.mp4"
    }
    selected_camera = st.sidebar.selectbox(
        "모니터링 카메라 선택",
        list(camera_options.keys())
    )
    uploaded_video = None
    if selected_camera == "영상 파일 업로드":
        uploaded_video = st.sidebar.file_uploader(
            "분석할 CCTV 영상 파일을 업로드하세요 (mp4, avi, mov, mkv)",
            type=["mp4", "avi", "mov", "mkv"]
        )
    risk_threshold = st.sidebar.slider(
        "위험도 임계값",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="이 값 이상일 때 위험 알림을 표시합니다"
    )
    st.sidebar.subheader("🔔 알림 설정")
    enable_email_alert = st.sidebar.checkbox("이메일 알림", value=True)
    enable_sms_alert = st.sidebar.checkbox("SMS 알림", value=False)
    enable_sound_alert = st.sidebar.checkbox("소리 알림", value=True)
    st.sidebar.subheader("📊 분석 설정")
    enable_lane_detection = st.sidebar.checkbox("차선 검출", value=True)
    enable_object_detection = st.sidebar.checkbox("객체 검출", value=True)
    enable_risk_assessment = st.sidebar.checkbox("위험도 분석", value=True)
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_monitoring = st.button("▶️ 모니터링 시작", type="primary")
    with col2:
        stop_monitoring = st.button("⏹️ 모니터링 정지")
    return {
        'camera': camera_options[selected_camera],
        'risk_threshold': risk_threshold,
        'alerts': {
            'email': enable_email_alert,
            'sms': enable_sms_alert,
            'sound': enable_sound_alert
        },
        'analysis': {
            'lane': enable_lane_detection,
            'object': enable_object_detection,
            'risk': enable_risk_assessment
        },
        'start': start_monitoring,
        'stop': stop_monitoring,
        'demo_mode': selected_camera == "데모 모드",
        'webcam_mode': selected_camera == "웹캠 연결",
        'cctv_mode': selected_camera == "실제 CCTV 스트림",
        'video_upload_mode': selected_camera == "영상 파일 업로드",
        'uploaded_video': uploaded_video
    }

def setup_main_dashboard():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="현재 위험도", value="0.0", delta="0.0")
    with col2:
        st.metric(label="감지된 차량", value="0", delta="0")
    with col3:
        st.metric(label="위험 이벤트", value="0", delta="0")
    with col4:
        st.metric(label="시스템 상태", value="업로드/재생 모드", delta="")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📹 실시간 CCTV 영상")
        video_placeholder = st.empty()
    with col2:
        st.subheader("⚠️ 실시간 위험도 알림")
        alert_placeholder = st.empty()
        st.subheader("📊 위험도 통계")
        chart_placeholder = st.empty()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚨 최근 위험 이벤트")
        event_placeholder = st.empty()
    with col2:
        st.subheader("📈 위험도 트렌드")
        trend_placeholder = st.empty()
    return {
        'video': video_placeholder,
        'alert': alert_placeholder,
        'chart': chart_placeholder,
        'event': event_placeholder,
        'trend': trend_placeholder
    }

def run_monitoring(config, placeholders):
    if 'monitoring_active' not in st.session_state:
        st.session_state.monitoring_active = False
    if config['start'] and not st.session_state.monitoring_active:
        st.session_state.monitoring_active = True
        st.success("모니터링이 시작되었습니다!")
        if config.get('video_upload_mode'):
            run_uploaded_video_mode(placeholders, config)
        elif config['cctv_mode']:
            run_cctv_stream_mode(placeholders, config)
        elif config['webcam_mode']:
            run_webcam_mode(placeholders, config)
        else:
            run_demo_mode(placeholders, config)
    elif config['stop'] and st.session_state.monitoring_active:
        st.session_state.monitoring_active = False
        st.warning("모니터링이 정지되었습니다!")

def run_uploaded_video_mode(placeholders, config):
    uploaded_video = config.get('uploaded_video')
    if uploaded_video is None:
        st.warning("분석할 영상을 업로드해주세요.")
        return
    # '실시간 CCTV 영상' 영역에 업로드한 영상 재생
    placeholders['video'].video(uploaded_video)
    st.info("업로드한 영상을 '실시간 CCTV 영상' 영역에서 바로 재생합니다.")

def run_cctv_stream_mode(placeholders, config):
    st.info("🔄 CCTV 스트림에 연결 중...")
    st.warning("CCTV 스트림은 현재 데모/이미지 모드만 지원합니다.")
    run_demo_mode(placeholders, config)

def run_webcam_mode(placeholders, config):
    st.error("웹캠은 Streamlit Cloud 환경에서 사용할 수 없습니다. 데모 모드로 전환합니다.")
    run_demo_mode(placeholders, config)

def calculate_simple_risk_score_pil(image):
    import random
    return random.uniform(0.0, 1.0)

def visualize_risk_on_frame_pil(image, risk_score):
    if image is None:
        return create_demo_frame_pil(risk_score)
    img = image.copy()
    draw = ImageDraw.Draw(img)
    if risk_score < 0.3:
        color = (0, 255, 0)
        level = "안전"
    elif risk_score < 0.6:
        color = (255, 255, 0)
        level = "주의"
    elif risk_score < 0.8:
        color = (255, 165, 0)
        level = "위험"
    else:
        color = (255, 0, 0)
        level = "매우 위험"
    text = f"위험도: {level} ({risk_score:.2f})"
    draw.text((10, 10), text, fill=color)
    draw.text((10, 40), "실시간 CCTV 스트림", fill=(255, 255, 255))
    if risk_score > 0.8:
        draw.rectangle([(0, 0), (img.width, img.height)], outline=(255, 0, 0), width=5)
        draw.text((10, 70), "긴급 경고!", fill=(255, 0, 0))
    return img

def update_alerts(placeholders, risk_score):
    if risk_score > 0.8:
        placeholders['alert'].error("🚨 긴급 위험 상황 감지!")
    elif risk_score > 0.6:
        placeholders['alert'].warning("⚠️ 위험 상황 감지")
    elif risk_score > 0.3:
        placeholders['alert'].info("ℹ️ 주의 상황 감지")
    else:
        placeholders['alert'].success("✅ 안전 상황")

def update_charts(placeholders, risk_score):
    if 'risk_history' not in st.session_state:
        st.session_state.risk_history = []
    st.session_state.risk_history.append({
        'timestamp': datetime.now(),
        'risk_score': risk_score
    })
    if len(st.session_state.risk_history) > 50:
        st.session_state.risk_history = st.session_state.risk_history[-50:]
    if len(st.session_state.risk_history) > 1:
        df = pd.DataFrame(st.session_state.risk_history)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['risk_score'],
            mode='lines+markers',
            name='위험도',
            line=dict(color='red', width=2)
        ))
        fig.update_layout(
            title="실시간 위험도 변화",
            xaxis_title="시간",
            yaxis_title="위험도",
            height=300
        )
        placeholders['chart'].plotly_chart(fig, use_container_width=True)

def run_demo_mode(placeholders, config):
    import random
    risk_scores = []
    timestamps = []
    for i in range(50):
        risk_score = random.uniform(0.0, 1.0)
        timestamp = datetime.now() - timedelta(seconds=50-i)
        risk_scores.append(risk_score)
        timestamps.append(timestamp)
    df = pd.DataFrame({
        'timestamp': timestamps,
        'risk_score': risk_scores
    })
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['risk_score'],
        mode='lines+markers',
        name='위험도',
        line=dict(color='red', width=2)
    ))
    fig.update_layout(
        title="실시간 위험도 변화",
        xaxis_title="시간",
        yaxis_title="위험도",
        height=300
    )
    placeholders['chart'].plotly_chart(fig, use_container_width=True)
    current_risk = risk_scores[-1]
    if current_risk > 0.8:
        placeholders['alert'].error("🚨 긴급 위험 상황 감지!")
    elif current_risk > 0.6:
        placeholders['alert'].warning("⚠️ 위험 상황 감지")
    elif current_risk > 0.3:
        placeholders['alert'].info("ℹ️ 주의 상황 감지")
    else:
        placeholders['alert'].success("✅ 안전 상황")
    demo_frame = create_demo_frame_pil(current_risk)
    placeholders['video'].image(demo_frame, use_column_width=True)
    events = [
        {
            'timestamp': datetime.now() - timedelta(minutes=5),
            'type': '차선 이탈',
            'message': '차선 이탈 감지',
            'risk_score': 0.75
        },
        {
            'timestamp': datetime.now() - timedelta(minutes=3),
            'type': '급정지',
            'message': '급정지 감지',
            'risk_score': 0.85
        },
        {
            'timestamp': datetime.now() - timedelta(minutes=1),
            'type': '과속',
            'message': '과속 감지',
            'risk_score': 0.65
        }
    ]
    event_df = pd.DataFrame(events)
    placeholders['event'].dataframe(
        event_df[['timestamp', 'type', 'message', 'risk_score']],
        use_container_width=True
    )

def create_demo_frame_pil(risk_score):
    img = Image.new('RGB', (640, 480), color='gray')
    draw = ImageDraw.Draw(img)
    if risk_score < 0.3:
        color = (0, 255, 0)
        level = "안전"
    elif risk_score < 0.6:
        color = (255, 255, 0)
        level = "주의"
    elif risk_score < 0.8:
        color = (255, 165, 0)
        level = "위험"
    else:
        color = (255, 0, 0)
        level = "매우 위험"
    text = f"위험도: {level} ({risk_score:.2f})"
    draw.text((320, 240), text, fill=color, anchor="mm")
    demo_text = "데모 모드 - OpenCV 없이 실행"
    draw.text((10, 450), demo_text, fill=(255, 255, 255))
    return img

if __name__ == "__main__":
    main() 
