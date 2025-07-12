import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertSystem:
    def __init__(self):
        self.alert_history = []
        self.alert_cooldown = 5.0  # 5초 쿨다운
        self.last_alert_time = {}
        
    def check_alerts(self, analysis_result):
        """분석 결과에서 알림 체크"""
        alerts = []
        current_time = time.time()
        
        # 긴급 위험 알림 (위험도 > 0.8)
        if analysis_result.get('overall_risk_score', 0) > 0.8:
            alert_key = 'emergency_risk'
            if self._can_send_alert(alert_key, current_time):
                alerts.append({
                    'type': 'EMERGENCY',
                    'message': '긴급 위험 상황 감지!',
                    'priority': 'HIGH',
                    'timestamp': datetime.now(),
                    'risk_score': analysis_result['overall_risk_score']
                })
                self._update_alert_time(alert_key, current_time)
        
        # 차선 이탈 알림
        if analysis_result.get('lane_violation', False):
            alert_key = 'lane_violation'
            if self._can_send_alert(alert_key, current_time):
                alerts.append({
                    'type': 'LANE_VIOLATION',
                    'message': '차선 이탈 감지',
                    'priority': 'MEDIUM',
                    'timestamp': datetime.now()
                })
                self._update_alert_time(alert_key, current_time)
        
        # 비정상 주행 알림
        if analysis_result.get('abnormal_behavior', False):
            alert_key = 'abnormal_behavior'
            if self._can_send_alert(alert_key, current_time):
                alerts.append({
                    'type': 'ABNORMAL_BEHAVIOR',
                    'message': '비정상 주행 감지',
                    'priority': 'MEDIUM',
                    'timestamp': datetime.now()
                })
                self._update_alert_time(alert_key, current_time)
        
        # 위험 이벤트 알림
        risk_events = analysis_result.get('risk_events', [])
        for event in risk_events:
            if event['risk_score'] > 0.7:
                alert_key = f"risk_event_{event['vehicle1_id']}_{event['vehicle2_id']}"
                if self._can_send_alert(alert_key, current_time):
                    alerts.append({
                        'type': 'RISK_EVENT',
                        'message': f"차량 간 위험 상황 감지 (위험도: {event['risk_score']:.2f})",
                        'priority': 'HIGH' if event['risk_score'] > 0.8 else 'MEDIUM',
                        'timestamp': datetime.now(),
                        'risk_score': event['risk_score']
                    })
                    self._update_alert_time(alert_key, current_time)
        
        # 알림 히스토리 업데이트
        self.alert_history.extend(alerts)
        if len(self.alert_history) > 100:  # 최근 100개만 유지
            self.alert_history = self.alert_history[-100:]
        
        return alerts
    
    def _can_send_alert(self, alert_key, current_time):
        """알림 전송 가능 여부 확인"""
        if alert_key not in self.last_alert_time:
            return True
        
        time_since_last = current_time - self.last_alert_time[alert_key]
        return time_since_last >= self.alert_cooldown
    
    def _update_alert_time(self, alert_key, current_time):
        """알림 시간 업데이트"""
        self.last_alert_time[alert_key] = current_time
    
    def send_alert(self, alert):
        """알림 전송"""
        if alert['priority'] == 'HIGH':
            self.send_emergency_alert(alert)
        else:
            self.send_normal_alert(alert)
    
    def send_emergency_alert(self, alert):
        """긴급 알림 전송"""
        print(f"🚨 긴급 알림: {alert['message']}")
        # 실제 구현에서는 이메일, SMS, 웹훅 등으로 전송
        self._send_email_alert(alert, is_emergency=True)
    
    def send_normal_alert(self, alert):
        """일반 알림 전송"""
        print(f"⚠️ 알림: {alert['message']}")
        # 실제 구현에서는 이메일, SMS, 웹훅 등으로 전송
        self._send_email_alert(alert, is_emergency=False)
    
    def _send_email_alert(self, alert, is_emergency=False):
        """이메일 알림 전송 (예시)"""
        # 실제 구현에서는 SMTP 설정 필요
        try:
            # 이메일 설정 (실제 사용 시 환경변수로 관리)
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = "your_email@gmail.com"
            sender_password = "your_password"
            receiver_email = "admin@company.com"
            
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            
            if is_emergency:
                msg['Subject'] = "🚨 긴급 알림 - CCTV 비정상주행 감지"
            else:
                msg['Subject'] = "⚠️ 알림 - CCTV 비정상주행 감지"
            
            # 이메일 본문
            body = f"""
            CCTV 비정상주행 감지 시스템에서 알림이 발생했습니다.
            
            알림 유형: {alert['type']}
            메시지: {alert['message']}
            우선순위: {alert['priority']}
            발생 시간: {alert['timestamp']}
            
            위험도 점수: {alert.get('risk_score', 'N/A')}
            
            즉시 확인하시기 바랍니다.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # 이메일 전송 (실제 구현 시 활성화)
            # server = smtplib.SMTP(smtp_server, smtp_port)
            # server.starttls()
            # server.login(sender_email, sender_password)
            # text = msg.as_string()
            # server.sendmail(sender_email, receiver_email, text)
            # server.quit()
            
        except Exception as e:
            print(f"이메일 전송 실패: {e}")
    
    def get_recent_alerts(self, hours=24):
        """최근 알림 조회"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_alerts = [
            alert for alert in self.alert_history
            if alert['timestamp'].timestamp() > cutoff_time
        ]
        return recent_alerts
    
    def get_alert_statistics(self):
        """알림 통계 조회"""
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'emergency_alerts': 0,
                'medium_alerts': 0,
                'alert_types': {}
            }
        
        total_alerts = len(self.alert_history)
        emergency_alerts = len([a for a in self.alert_history if a['priority'] == 'HIGH'])
        medium_alerts = len([a for a in self.alert_history if a['priority'] == 'MEDIUM'])
        
        alert_types = {}
        for alert in self.alert_history:
            alert_type = alert['type']
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'emergency_alerts': emergency_alerts,
            'medium_alerts': medium_alerts,
            'alert_types': alert_types
        }
