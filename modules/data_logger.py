import csv
import pandas as pd
from datetime import datetime, timedelta
import os
import json

class RiskDataLogger:
    def __init__(self, output_path="output"):
        self.output_path = output_path
        self.log_file = f"{output_path}/risk_analysis_log.csv"
        self.event_file = f"{output_path}/events.json"
        
        # 출력 디렉토리 생성
        os.makedirs(output_path, exist_ok=True)
        
        # CSV 파일 헤더 초기화
        self._initialize_csv()
    
    def _initialize_csv(self):
        """CSV 파일 헤더 초기화"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'vehicle1_id',
                    'vehicle2_id',
                    'risk_score',
                    'distance',
                    'relative_velocity',
                    'time_to_collision',
                    'overall_risk_score',
                    'lane_violation',
                    'abnormal_behavior'
                ])
    
    def log_risk_event(self, timestamp, risk_events, analysis_result):
        """위험도 이벤트 로그 저장"""
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                for event in risk_events:
                    writer.writerow([
                        timestamp,
                        event.get('vehicle1_id', ''),
                        event.get('vehicle2_id', ''),
                        event.get('risk_score', 0.0),
                        event.get('distance', 0.0),
                        event.get('relative_velocity', 0.0),
                        event.get('time_to_collision', 0.0),
                        analysis_result.get('overall_risk_score', 0.0),
                        analysis_result.get('lane_violation', False),
                        analysis_result.get('abnormal_behavior', False)
                    ])
        except Exception as e:
            print(f"로그 저장 실패: {e}")
    
    def log_alert_event(self, alert):
        """알림 이벤트 로그 저장"""
        try:
            with open(self.event_file, 'a', encoding='utf-8') as f:
                event_data = {
                    'timestamp': alert['timestamp'].isoformat(),
                    'type': alert['type'],
                    'message': alert['message'],
                    'priority': alert['priority'],
                    'risk_score': alert.get('risk_score', 0.0)
                }
                f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"알림 로그 저장 실패: {e}")
    
    def generate_risk_report(self, start_time=None, end_time=None):
        """위험도 분석 리포트 생성"""
        try:
            if not os.path.exists(self.log_file):
                return self._empty_report()
            
            df = pd.read_csv(self.log_file)
            
            # 시간 필터링
            if start_time and end_time:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                filtered_df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
            else:
                filtered_df = df
            
            if filtered_df.empty:
                return self._empty_report()
            
            # 통계 계산
            total_events = len(filtered_df)
            high_risk_events = len(filtered_df[filtered_df['risk_score'] > 0.8])
            medium_risk_events = len(filtered_df[(filtered_df['risk_score'] > 0.5) & (filtered_df['risk_score'] <= 0.8)])
            low_risk_events = len(filtered_df[filtered_df['risk_score'] <= 0.5])
            
            avg_risk_score = filtered_df['risk_score'].mean()
            max_risk_score = filtered_df['risk_score'].max()
            min_risk_score = filtered_df['risk_score'].min()
            
            # 차선 이탈 및 비정상 주행 통계
            lane_violations = len(filtered_df[filtered_df['lane_violation'] == True])
            abnormal_behaviors = len(filtered_df[filtered_df['abnormal_behavior'] == True])
            
            # 시간대별 위험도 분석
            filtered_df['hour'] = pd.to_datetime(filtered_df['timestamp']).dt.hour
            hourly_risk = filtered_df.groupby('hour')['risk_score'].mean()
            
            report = {
                'period': {
                    'start': start_time.isoformat() if start_time else None,
                    'end': end_time.isoformat() if end_time else None
                },
                'summary': {
                    'total_events': total_events,
                    'high_risk_events': high_risk_events,
                    'medium_risk_events': medium_risk_events,
                    'low_risk_events': low_risk_events,
                    'lane_violations': lane_violations,
                    'abnormal_behaviors': abnormal_behaviors
                },
                'risk_statistics': {
                    'average_risk_score': avg_risk_score,
                    'max_risk_score': max_risk_score,
                    'min_risk_score': min_risk_score,
                    'risk_std': filtered_df['risk_score'].std()
                },
                'hourly_analysis': hourly_risk.to_dict(),
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            print(f"리포트 생성 실패: {e}")
            return self._empty_report()
    
    def _empty_report(self):
        """빈 리포트 반환"""
        return {
            'period': {'start': None, 'end': None},
            'summary': {
                'total_events': 0,
                'high_risk_events': 0,
                'medium_risk_events': 0,
                'low_risk_events': 0,
                'lane_violations': 0,
                'abnormal_behaviors': 0
            },
            'risk_statistics': {
                'average_risk_score': 0.0,
                'max_risk_score': 0.0,
                'min_risk_score': 0.0,
                'risk_std': 0.0
            },
            'hourly_analysis': {},
            'generated_at': datetime.now().isoformat()
        }
    
    def get_recent_events(self, hours=24):
        """최근 이벤트 조회"""
        try:
            if not os.path.exists(self.log_file):
                return []
            
            df = pd.read_csv(self.log_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_df = df[df['timestamp'] >= cutoff_time]
            
            return recent_df.to_dict('records')
            
        except Exception as e:
            print(f"최근 이벤트 조회 실패: {e}")
            return []
    
    def export_data(self, start_time=None, end_time=None, format='csv'):
        """데이터 내보내기"""
        try:
            if not os.path.exists(self.log_file):
                return None
            
            df = pd.read_csv(self.log_file)
            
            # 시간 필터링
            if start_time and end_time:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                filtered_df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
            else:
                filtered_df = df
            
            if format == 'csv':
                export_file = f"{self.output_path}/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filtered_df.to_csv(export_file, index=False, encoding='utf-8-sig')
                return export_file
            elif format == 'excel':
                export_file = f"{self.output_path}/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                filtered_df.to_excel(export_file, index=False)
                return export_file
            else:
                return None
                
        except Exception as e:
            print(f"데이터 내보내기 실패: {e}")
            return None
    
    def get_statistics_summary(self):
        """통계 요약 조회"""
        try:
            if not os.path.exists(self.log_file):
                return self._empty_report()['summary']
            
            df = pd.read_csv(self.log_file)
            
            # 오늘 데이터만 필터링
            today = datetime.now().date()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            today_df = df[df['timestamp'].dt.date == today]
            
            if today_df.empty:
                return {
                    'today_events': 0,
                    'today_high_risk': 0,
                    'today_lane_violations': 0,
                    'today_abnormal_behaviors': 0,
                    'avg_risk_today': 0.0
                }
            
            return {
                'today_events': len(today_df),
                'today_high_risk': len(today_df[today_df['risk_score'] > 0.8]),
                'today_lane_violations': len(today_df[today_df['lane_violation'] == True]),
                'today_abnormal_behaviors': len(today_df[today_df['abnormal_behavior'] == True]),
                'avg_risk_today': today_df['risk_score'].mean()
            }
            
        except Exception as e:
            print(f"통계 요약 조회 실패: {e}")
            return {
                'today_events': 0,
                'today_high_risk': 0,
                'today_lane_violations': 0,
                'today_abnormal_behaviors': 0,
                'avg_risk_today': 0.0
            }
