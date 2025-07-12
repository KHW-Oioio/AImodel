import numpy as np
from datetime import datetime
import time

class RealTimeRiskMonitor:
    def __init__(self, risk_threshold=0.7):
        self.risk_threshold = risk_threshold
        self.vehicle_trackers = {}
        self.risk_history = []
        
    def process_frame(self, frame, detections):
        """프레임에서 위험도 분석"""
        risk_events = []
        
        # 차량 추적 업데이트
        self.update_vehicle_tracks(detections)
        
        # 차량 간 위험도 계산
        vehicles = list(self.vehicle_trackers.values())
        for i, v1 in enumerate(vehicles):
            for j, v2 in enumerate(vehicles[i+1:], i+1):
                risk_event = self.calculate_risk_between_vehicles(v1, v2)
                if risk_event:
                    risk_events.append(risk_event)
        
        return risk_events
    
    def update_vehicle_tracks(self, detections):
        """차량 추적 업데이트"""
        for detection in detections:
            vehicle_id = detection.get('id', len(self.vehicle_trackers))
            if vehicle_id not in self.vehicle_trackers:
                self.vehicle_trackers[vehicle_id] = VehicleTrack(vehicle_id)
            
            self.vehicle_trackers[vehicle_id].update_position(detection['bbox'])
    
    def calculate_risk_between_vehicles(self, vehicle1, vehicle2):
        """두 차량 간 위험도 계산"""
        # 거리 계산
        distance = self.calculate_distance(vehicle1.position, vehicle2.position)
        
        # 상대 속도 계산
        relative_velocity = abs(vehicle1.velocity - vehicle2.velocity)
        
        # 안전 거리 계산
        safe_distance = self.calculate_safe_distance(relative_velocity)
        
        # 충돌까지의 시간 계산
        time_to_collision = self.calculate_time_to_collision(distance, relative_velocity)
        
        # 위험도 점수 계산
        risk_score = self.calculate_risk_score(distance, safe_distance, relative_velocity, time_to_collision)
        
        if risk_score > self.risk_threshold:
            return {
                'vehicle1_id': vehicle1.id,
                'vehicle2_id': vehicle2.id,
                'risk_score': risk_score,
                'distance': distance,
                'relative_velocity': relative_velocity,
                'time_to_collision': time_to_collision,
                'timestamp': datetime.now()
            }
        
        return None
    
    def calculate_distance(self, pos1, pos2):
        """두 위치 간 거리 계산"""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def calculate_safe_distance(self, velocity):
        """안전 거리 계산"""
        reaction_time = 1.5  # 반응 시간 (초)
        deceleration = 7.0   # 감속도 (m/s²)
        minimum_distance = 2.0  # 최소 안전 거리 (미터)
        
        reaction_distance = velocity * reaction_time
        braking_distance = (velocity ** 2) / (2 * deceleration)
        safe_distance = reaction_distance + braking_distance
        
        return max(safe_distance, minimum_distance)
    
    def calculate_time_to_collision(self, distance, relative_velocity):
        """충돌까지의 시간 계산"""
        if relative_velocity <= 0:
            return float('inf')
        return distance / relative_velocity
    
    def calculate_risk_score(self, current_distance, safe_distance, relative_velocity, time_to_collision):
        """위험도 점수 계산"""
        # 거리 위험도 (0-1)
        distance_risk = max(0, 1 - (current_distance / safe_distance))
        
        # 속도 위험도 (0-1)
        max_velocity = 30.0  # m/s (약 108km/h)
        velocity_risk = min(relative_velocity / max_velocity, 1.0)
        
        # 충돌 시간 위험도 (0-1)
        if time_to_collision == float('inf'):
            collision_risk = 0.0
        else:
            # 3초 이내면 위험
            collision_risk = max(0, 1 - (time_to_collision / 3.0))
        
        # 종합 위험도 계산
        risk_weights = {
            'distance': 0.4,
            'velocity': 0.3,
            'time_to_collision': 0.3
        }
        
        total_risk = (
            distance_risk * risk_weights['distance'] +
            velocity_risk * risk_weights['velocity'] +
            collision_risk * risk_weights['time_to_collision']
        )
        
        return min(total_risk, 1.0)
    
    def get_risk_level(self, risk_score):
        """위험도 레벨 반환"""
        if risk_score < 0.3:
            return "안전", (0, 255, 0)
        elif risk_score < 0.6:
            return "주의", (0, 255, 255)
        elif risk_score < 0.8:
            return "위험", (0, 165, 255)
        else:
            return "매우 위험", (0, 0, 255)

class VehicleTrack:
    def __init__(self, vehicle_id):
        self.id = vehicle_id
        self.position = (0, 0)
        self.velocity = 0.0
        self.position_history = []
        self.velocity_history = []
        
    def update_position(self, bbox):
        """차량 위치 업데이트"""
        # bbox에서 중심점 계산
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        old_position = self.position
        self.position = (center_x, center_y)
        
        # 위치 히스토리 업데이트
        self.position_history.append(self.position)
        if len(self.position_history) > 10:
            self.position_history.pop(0)
        
        # 속도 계산
        if len(self.position_history) >= 2:
            distance = np.sqrt(
                (self.position[0] - old_position[0])**2 + 
                (self.position[1] - old_position[1])**2
            )
            # 픽셀을 미터로 변환 (실제 구현에서는 카메라 캘리브레이션 필요)
            pixel_to_meter_ratio = 0.1  # 예시 값
            real_distance = distance * pixel_to_meter_ratio
            
            # 속도 계산 (m/s)
            fps = 30  # 프레임 레이트
            velocity = real_distance * fps
            
            self.velocity_history.append(velocity)
            if len(self.velocity_history) > 5:
                self.velocity_history.pop(0)
            
            # 평균 속도 계산
            self.velocity = np.mean(self.velocity_history)
