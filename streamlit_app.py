import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import threading
import queue
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import requests
import cv2

# OpenCV import 오류 처리
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    st.warning("⚠️ OpenCV를 사용할 수 없습니다. 데모 모드로 실행됩니다.")
    OPENCV_AVAILABLE = False

# 커스텀 모듈 import (조건부)
if OPENCV_AVAILABLE:
    try:
        from modules.risk_assessment import RealTimeRiskMonitor
        from modules.alert_system import AlertSystem
        from modules.data_logger import RiskDataLogger
        from modules.video_processor import VideoProcessor
        MODULES_AVAILABLE = True
    except ImportError:
        st.warning("⚠️ 일부 모듈을 불러올 수 없습니다. 데모 모드로 실행됩니다.")
        MODULES_AVAILABLE = False
else:
    MODULES_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="CCTV 비정상주행 감지 시스템",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CCTV 스트림 URL
CCTV_STREAM_URL = "https://www.utic.go.kr/jsp/map/cctvStream.jsp?cctvid=E970104&cctvname=%25EB%25B0%2598%25ED%258F%25AC%25EB%258C%2580%25EA%25B5%2590%25EB%25B6%2581%25EB%258B%25A81&kind=EC&cctvip=undefined&cctvch=53&id=428&cctvpasswd=undefined&cctvport=undefined&minX=126.94439014863138&minY=37.48157205124353&maxX=127.16458223998221&maxY=37.56413189592257"

def main():
    st.title("🚗 CCTV 비정상주행 감지 시스템")
    st.markdown("---")
    
    # 시스템 상태 표시
    if not OPENCV_AVAILABLE:
        st.error("❌ OpenCV가 설치되지 않았습니다. 데모 모드로 실행됩니다.")
    elif not MODULES_AVAILABLE:
        st.warning("⚠️ 일부 모듈을 불러올 수 없습니다. 데모 모드로 실행됩니다.")
    else:
        st.success("✅ 모든 모듈이 정상적으로 로드되었습니다.")
    
    # 사이드바 설정
    config = setup_sidebar()
    
    # 메인 대시보드
    placeholders = setup_main_dashboard()
    
    # 모니터링 실행
    run_monitoring(config, placeholders)

def setup_sidebar():
    """사이드바 설정"""
    st.sidebar.title("🚗 모니터링 설정")
    
    # 시스템 상태 표시
    if not OPENCV_AVAILABLE:
        st.sidebar.error("⚠️ 데모 모드")
    else:
        st.sidebar.success("✅ 정상 모드")
    
    # 카메라 선택
    camera_options = {
        "실제 CCTV 스트림": "cctv_stream",
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
    
    # 위험도 임계값 설정
    risk_threshold = st.sidebar.slider(
        "위험도 임계값",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="이 값 이상일 때 위험 알림을 표시합니다"
    )
    
    # 알림 설정
    st.sidebar.subheader("🔔 알림 설정")
    enable_email_alert = st.sidebar.checkbox("이메일 알림", value=True)
    enable_sms_alert = st.sidebar.checkbox("SMS 알림", value=False)
    enable_sound_alert = st.sidebar.checkbox("소리 알림", value=True)
    
    # 분석 설정
    st.sidebar.subheader("📊 분석 설정")
    enable_lane_detection = st.sidebar.checkbox("차선 검출", value=True)
    enable_object_detection = st.sidebar.checkbox("객체 검출", value=True)
    enable_risk_assessment = st.sidebar.checkbox("위험도 분석", value=True)
    
    # 시작/정지 버튼
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
        'demo_mode': not OPENCV_AVAILABLE or selected_camera == "데모 모드",
        'webcam_mode': selected_camera == "웹캠 연결",
        'cctv_mode': selected_camera == "실제 CCTV 스트림"
    }

def setup_main_dashboard():
    """메인 대시보드 설정"""
    # 실시간 상태 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="현재 위험도",
            value="0.0",
            delta="0.0"
        )
    
    with col2:
        st.metric(
            label="감지된 차량",
            value="0",
            delta="0"
        )
    
    with col3:
        st.metric(
            label="위험 이벤트",
            value="0",
            delta="0"
        )
    
    with col4:
        st.metric(
            label="시스템 상태",
            value="정상" if OPENCV_AVAILABLE else "데모",
            delta=""
        )
    
    # 메인 콘텐츠 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📹 실시간 CCTV 영상")
        video_placeholder = st.empty()
        
    with col2:
        st.subheader("⚠️ 실시간 위험도 알림")
        alert_placeholder = st.empty()
        
        st.subheader("📊 위험도 통계")
        chart_placeholder = st.empty()
    
    # 하단 대시보드
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
    """모니터링 실행"""
    # 모니터링 상태
    if 'monitoring_active' not in st.session_state:
        st.session_state.monitoring_active = False
    
    # 모니터링 시작/정지
    if config['start'] and not st.session_state.monitoring_active:
        st.session_state.monitoring_active = True
        st.success("모니터링이 시작되었습니다!")
        
        # CCTV 스트림 모드 실행
        if config['cctv_mode'] and OPENCV_AVAILABLE:
            run_cctv_stream_mode(placeholders, config)
        elif config['webcam_mode'] and OPENCV_AVAILABLE:
            run_webcam_mode(placeholders, config)
        else:
            run_demo_mode(placeholders, config)
    
    elif config['stop'] and st.session_state.monitoring_active:
        st.session_state.monitoring_active = False
        st.warning("모니터링이 정지되었습니다!")

def run_cctv_stream_mode(placeholders, config):
    """CCTV 스트림 모드 실행"""
    if not OPENCV_AVAILABLE:
        st.error("OpenCV가 설치되지 않아 CCTV 스트림을 사용할 수 없습니다.")
        return
    
    st.info("🔄 CCTV 스트림에 연결 중...")
    
    try:
        # CCTV 스트림 연결 시도
        cap = cv2.VideoCapture(CCTV_STREAM_URL)
        
        if not cap.isOpened():
            st.error("CCTV 스트림에 연결할 수 없습니다. 데모 모드로 전환합니다.")
            run_demo_mode(placeholders, config)
            return
        
        st.success("✅ CCTV 스트림에 연결되었습니다!")
        
        # 실시간 스트리밍
        video_placeholder = placeholders['video']
        
        # 위험도 계산을 위한 변수
        risk_score = 0.0
        frame_count = 0
        
        while st.session_state.monitoring_active:
            ret, frame = cap.read()
            
            if not ret:
                st.warning("CCTV 스트림에서 프레임을 읽을 수 없습니다. 재연결 시도 중...")
                time.sleep(2)
                continue
            
            # 프레임 처리
            frame = cv2.resize(frame, (640, 480))
            
            # 위험도 계산 (실제 구현에서는 AI 모델 사용)
            risk_score = calculate_simple_risk_score(frame)
            
            # 위험도 시각화
            frame_with_risk = visualize_risk_on_frame(frame, risk_score)
            
            # BGR을 RGB로 변환
            frame_rgb = cv2.cvtColor(frame_with_risk, cv2.COLOR_BGR2RGB)
            
            # Streamlit에 표시
            video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
            
            # 알림 업데이트
            update_alerts(placeholders, risk_score)
            
            # 차트 업데이트 (프레임마다 업데이트하지 않고 주기적으로)
            frame_count += 1
            if frame_count % 30 == 0:  # 30프레임마다 차트 업데이트
                update_charts(placeholders, risk_score)
            
            # 잠시 대기 (프레임 레이트 조절)
            time.sleep(0.1)
        
        # 스트림 해제
        cap.release()
        
    except Exception as e:
        st.error(f"CCTV 스트림 연결 중 오류가 발생했습니다: {e}")
        st.info("데모 모드로 전환합니다.")
        run_demo_mode(placeholders, config)

def run_webcam_mode(placeholders, config):
    """웹캠 모드 실행"""
    if not OPENCV_AVAILABLE:
        st.error("OpenCV가 설치되지 않아 웹캠을 사용할 수 없습니다.")
        return
    
    # 웹캠 연결
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("웹캠을 열 수 없습니다. 데모 모드로 전환합니다.")
        run_demo_mode(placeholders, config)
        return
    
    # 웹캠 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 실시간 스트리밍
    video_placeholder = placeholders['video']
    
    # 위험도 계산을 위한 변수
    risk_score = 0.0
    
    while st.session_state.monitoring_active:
        ret, frame = cap.read()
        
        if not ret:
            st.error("프레임을 읽을 수 없습니다.")
            break
        
        # 프레임 처리
        frame = cv2.resize(frame, (640, 480))
        
        # 위험도 계산 (실제 구현에서는 AI 모델 사용)
        risk_score = calculate_simple_risk_score(frame)
        
        # 위험도 시각화
        frame_with_risk = visualize_risk_on_frame(frame, risk_score)
        
        # BGR을 RGB로 변환
        frame_rgb = cv2.cvtColor(frame_with_risk, cv2.COLOR_BGR2RGB)
        
        # Streamlit에 표시
        video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        
        # 알림 업데이트
        update_alerts(placeholders, risk_score)
        
        # 차트 업데이트
        update_charts(placeholders, risk_score)
        
        # 잠시 대기 (프레임 레이트 조절)
        time.sleep(0.1)
    
    # 웹캠 해제
    cap.release()

def calculate_simple_risk_score(frame):
    """간단한 위험도 계산 (실제로는 AI 모델 사용)"""
    import random
    # 실제 구현에서는 프레임 분석을 통한 위험도 계산
    # 여기서는 데모용으로 랜덤 값 사용
    return random.uniform(0.0, 1.0)

def visualize_risk_on_frame(frame, risk_score):
    """프레임에 위험도 정보 시각화"""
    if risk_score < 0.3:
        color = (0, 255, 0)  # 녹색
        level = "안전"
    elif risk_score < 0.6:
        color = (0, 255, 255)  # 노란색
        level = "주의"
    elif risk_score < 0.8:
        color = (0, 165, 255)  # 주황색
        level = "위험"
    else:
        color = (0, 0, 255)  # 빨간색
        level = "매우 위험"
    
    # 위험도 정보 표시
    cv2.putText(frame, f"위험도: {level} ({risk_score:.2f})", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    # CCTV 스트림 정보 표시
    cv2.putText(frame, "실시간 CCTV 스트림", 
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 긴급 경고 프레임 추가
    if risk_score > 0.8:
        cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 5)
        cv2.putText(frame, "긴급 경고!", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    
    return frame

def update_alerts(placeholders, risk_score):
    """알림 업데이트"""
    if risk_score > 0.8:
        placeholders['alert'].error("🚨 긴급 위험 상황 감지!")
    elif risk_score > 0.6:
        placeholders['alert'].warning("⚠️ 위험 상황 감지")
    elif risk_score > 0.3:
        placeholders['alert'].info("ℹ️ 주의 상황 감지")
    else:
        placeholders['alert'].success("✅ 안전 상황")

def update_charts(placeholders, risk_score):
    """차트 업데이트"""
    # 위험도 히스토리 저장
    if 'risk_history' not in st.session_state:
        st.session_state.risk_history = []
    
    st.session_state.risk_history.append({
        'timestamp': datetime.now(),
        'risk_score': risk_score
    })
    
    # 최근 50개 데이터만 유지
    if len(st.session_state.risk_history) > 50:
        st.session_state.risk_history = st.session_state.risk_history[-50:]
    
    # 차트 생성
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
    """데모 모드 실행 (실제 카메라 없이 샘플 데이터 사용)"""
    import random
    
    # 샘플 위험도 데이터 생성
    risk_scores = []
    timestamps = []
    
    for i in range(50):
        risk_score = random.uniform(0.0, 1.0)
        timestamp = datetime.now() - timedelta(seconds=50-i)
        risk_scores.append(risk_score)
        timestamps.append(timestamp)
    
    # 위험도 차트 생성
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
    
    # 차트 표시
    placeholders['chart'].plotly_chart(fig, use_container_width=True)
    
    # 샘플 알림
    current_risk = risk_scores[-1]
    if current_risk > 0.8:
        placeholders['alert'].error("🚨 긴급 위험 상황 감지!")
    elif current_risk > 0.6:
        placeholders['alert'].warning("⚠️ 위험 상황 감지")
    elif current_risk > 0.3:
        placeholders['alert'].info("ℹ️ 주의 상황 감지")
    else:
        placeholders['alert'].success("✅ 안전 상황")
    
    # 데모 비디오 프레임 생성
    if OPENCV_AVAILABLE:
        # OpenCV를 사용한 데모 프레임
        demo_frame = create_demo_frame_opencv(current_risk)
        placeholders['video'].image(demo_frame, channels="RGB", use_column_width=True)
    else:
        # PIL을 사용한 데모 프레임
        demo_frame = create_demo_frame_pil(current_risk)
        placeholders['video'].image(demo_frame, use_column_width=True)
    
    # 샘플 이벤트 로그
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

def create_demo_frame_opencv(risk_score):
    """OpenCV를 사용한 데모 프레임 생성"""
    # 빈 프레임 생성
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 배경 그라데이션
    for i in range(480):
        color = int(255 * (1 - i/480))
        frame[i, :] = [color, color, color]
    
    # 위험도 정보 표시
    if risk_score < 0.3:
        color = (0, 255, 0)  # 녹색
        level = "안전"
    elif risk_score < 0.6:
        color = (0, 255, 255)  # 노란색
        level = "주의"
    elif risk_score < 0.8:
        color = (0, 165, 255)  # 주황색
        level = "위험"
    else:
        color = (0, 0, 255)  # 빨간색
        level = "매우 위험"
    
    # 중앙에 텍스트 표시
    text = f"위험도: {level} ({risk_score:.2f})"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    thickness = 3
    
    # 텍스트 크기 계산
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # 텍스트 위치 계산 (중앙)
    text_x = (640 - text_width) // 2
    text_y = (480 + text_height) // 2
    
    # 텍스트 배경
    cv2.rectangle(frame, 
                 (text_x - 10, text_y - text_height - 10),
                 (text_x + text_width + 10, text_y + 10),
                 (0, 0, 0), -1)
    
    # 텍스트 표시
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)
    
    # 데모 정보 표시
    demo_text = "데모 모드 - 실제 카메라 연결 시 실시간 영상 표시"
    cv2.putText(frame, demo_text, (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # BGR을 RGB로 변환
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    return frame_rgb

def create_demo_frame_pil(risk_score):
    """PIL을 사용한 데모 프레임 생성"""
    # 빈 이미지 생성
    img = Image.new('RGB', (640, 480), color='gray')
    
    # 텍스트 추가
    draw = ImageDraw.Draw(img)
    
    # 위험도 정보 표시
    if risk_score < 0.3:
        color = (0, 255, 0)  # 녹색
        level = "안전"
    elif risk_score < 0.6:
        color = (255, 255, 0)  # 노란색
        level = "주의"
    elif risk_score < 0.8:
        color = (255, 165, 0)  # 주황색
        level = "위험"
    else:
        color = (255, 0, 0)  # 빨간색
        level = "매우 위험"
    
    # 텍스트 표시
    text = f"위험도: {level} ({risk_score:.2f})"
    draw.text((320, 240), text, fill=color, anchor="mm")
    
    # 데모 정보 표시
    demo_text = "데모 모드 - OpenCV 없이 실행"
    draw.text((10, 450), demo_text, fill=(255, 255, 255))
    
    return img

if __name__ == "__main__":
    main()
