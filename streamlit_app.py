import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import threading
import queue
from PIL import Image
import io

# 위험도 계산 모듈 import
from risk_assessment import RealTimeRiskMonitor, IntegratedAnalysisSystem
from alert_system import AlertSystem
from data_logger import RiskDataLogger

class StreamlitCCTVMonitor:
    def __init__(self):
        self.risk_monitor = RealTimeRiskMonitor(risk_threshold=0.7)
        self.alert_system = AlertSystem()
        self.data_logger = RiskDataLogger("output")
        self.frame_queue = queue.Queue(maxsize=10)
        self.analysis_queue = queue.Queue(maxsize=10)
        
    def setup_streamlit_app(self):
        st.set_page_config(
            page_title="CCTV 비정상주행 감지 시스템",
            page_icon="🚗",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 사이드바 설정
        self.setup_sidebar()
        
        # 메인 대시보드
        self.setup_main_dashboard()
        
    def setup_sidebar(self):
        st.sidebar.title("🚗 CCTV 모니터링 설정")
        
        # 카메라 선택
        camera_options = {
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
            'stop': stop_monitoring
        }
    
    def setup_main_dashboard(self):
        # 헤더
        st.title("🚗 CCTV 비정상주행 감지 시스템")
        st.markdown("---")
        
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
                value="정상",
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
    
    def update_video_feed(self, frame, analysis_result):
        """실시간 비디오 피드 업데이트"""
        if frame is not None:
            # 위험도 시각화
            risk_score = analysis_result.get('overall_risk_score', 0.0)
            frame = self.visualize_risk_on_frame(frame, risk_score)
            
            # OpenCV BGR을 RGB로 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # PIL Image로 변환
            pil_image = Image.fromarray(frame_rgb)
            
            return pil_image
    
    def visualize_risk_on_frame(self, frame, risk_score):
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
        
        # 경고 프레임 추가
        if risk_score > 0.8:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 5)
            cv2.putText(frame, "긴급 경고!", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        
        return frame
    
    def update_alert_panel(self, alerts):
        """알림 패널 업데이트"""
        if not alerts:
            st.info("현재 위험 이벤트가 없습니다.")
            return
        
        for alert in alerts:
            if alert['priority'] == 'HIGH':
                st.error(f"🚨 {alert['message']}")
            elif alert['priority'] == 'MEDIUM':
                st.warning(f"⚠️ {alert['message']}")
            else:
                st.info(f"ℹ️ {alert['message']}")
    
    def update_risk_chart(self, risk_history):
        """위험도 차트 업데이트"""
        if not risk_history:
            return
        
        df = pd.DataFrame(risk_history)
        
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
        
        return fig
    
    def update_event_log(self, events):
        """이벤트 로그 업데이트"""
        if not events:
            st.info("최근 위험 이벤트가 없습니다.")
            return
        
        event_df = pd.DataFrame(events)
        st.dataframe(
            event_df[['timestamp', 'type', 'message', 'risk_score']],
            use_container_width=True
        )
    
    def run_monitoring(self, config):
        """실시간 모니터링 실행"""
        cap = cv2.VideoCapture(config['camera'])
        
        if not cap.isOpened():
            st.error("카메라를 열 수 없습니다!")
            return
        
        # 모니터링 루프
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 프레임 분석
            analysis_result = self.analyze_frame(frame, config)
            
            # 결과를 큐에 추가
            self.frame_queue.put(frame)
            self.analysis_queue.put(analysis_result)
            
            # 알림 체크
            alerts = self.alert_system.check_alerts(analysis_result)
            if alerts:
                for alert in alerts:
                    self.alert_system.send_alert(alert)
            
            # 데이터 로깅
            self.data_logger.log_risk_event(
                datetime.now(),
                analysis_result.get('risk_events', []),
                analysis_result
            )
        
        cap.release()
    
    def analyze_frame(self, frame, config):
        """프레임 분석"""
        analysis_result = {
            'overall_risk_score': 0.0,
            'risk_events': [],
            'lane_violation': False,
            'abnormal_behavior': False,
            'vehicle_count': 0
        }
        
        if config['analysis']['risk']:
            # 위험도 분석
            risk_events = self.risk_monitor.process_frame(frame, [])
            analysis_result['risk_events'] = risk_events
            
            if risk_events:
                max_risk = max(event['risk_score'] for event in risk_events)
                analysis_result['overall_risk_score'] = max_risk
        
        return analysis_result

def main():
    # Streamlit 앱 초기화
    monitor = StreamlitCCTVMonitor()
    
    # 설정 가져오기
    config = monitor.setup_streamlit_app()
    
    # 대시보드 플레이스홀더 가져오기
    placeholders = monitor.setup_main_dashboard()
    
    # 모니터링 상태
    if 'monitoring_active' not in st.session_state:
        st.session_state.monitoring_active = False
    
    # 모니터링 시작/정지
    if config['start'] and not st.session_state.monitoring_active:
        st.session_state.monitoring_active = True
        st.success("모니터링이 시작되었습니다!")
        
        # 백그라운드에서 모니터링 실행
        monitoring_thread = threading.Thread(
            target=monitor.run_monitoring,
            args=(config,)
        )
        monitoring_thread.start()
    
    elif config['stop'] and st.session_state.monitoring_active:
        st.session_state.monitoring_active = False
        st.warning("모니터링이 정지되었습니다!")
    
    # 실시간 업데이트
    if st.session_state.monitoring_active:
        # 비디오 피드 업데이트
        if not monitor.frame_queue.empty():
            frame = monitor.frame_queue.get()
            analysis_result = monitor.analysis_queue.get()
            
            # 비디오 표시
            pil_image = monitor.update_video_feed(frame, analysis_result)
            placeholders['video'].image(pil_image, channels="RGB", use_column_width=True)
            
            # 알림 업데이트
            alerts = monitor.alert_system.check_alerts(analysis_result)
            monitor.update_alert_panel(alerts)
            
            # 차트 업데이트
            # (실제 구현에서는 위험도 히스토리를 사용)
            risk_history = [{'timestamp': datetime.now(), 'risk_score': analysis_result['overall_risk_score']}]
            chart_fig = monitor.update_risk_chart(risk_history)
            if chart_fig:
                placeholders['chart'].plotly_chart(chart_fig, use_container_width=True)

if __name__ == "__main__":
    main() 
