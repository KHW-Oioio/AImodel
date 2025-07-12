import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time

class VideoProcessor:
    def __init__(self):
        self.is_running = False
        
    def create_demo_frame(self, risk_score=0.0):
        """데모용 프레임 생성 (PIL 사용)"""
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
        
        # 중앙에 텍스트 표시
        text = f"위험도: {level} ({risk_score:.2f})"
        
        # 텍스트 크기 계산 (대략적)
        text_width = len(text) * 20
        text_height = 30
        
        # 텍스트 위치 계산 (중앙)
        text_x = (640 - text_width) // 2
        text_y = (480 - text_height) // 2
        
        # 텍스트 배경
        draw.rectangle(
            [(text_x - 10, text_y - 10), (text_x + text_width + 10, text_y + text_height + 10)],
            fill=(0, 0, 0)
        )
        
        # 텍스트 표시
        draw.text((text_x, text_y), text, fill=color)
        
        # 데모 정보 표시
        demo_text = "데모 모드 - 실제 카메라 연결 시 실시간 영상 표시"
        draw.text((10, 450), demo_text, fill=(255, 255, 255))
        
        return img
    
    def process_frame(self, frame):
        """프레임 전처리 (PIL 이미지 사용)"""
        if frame is None:
            return None
        
        # 프레임 크기 조정
        frame = frame.resize((640, 480))
        
        return frame
    
    def visualize_risk_on_frame(self, frame, risk_score, vehicle_info=None):
        """프레임에 위험도 정보 시각화 (PIL 사용)"""
        if frame is None:
            return None
        
        # PIL 이미지로 변환
        if not isinstance(frame, Image.Image):
            frame = Image.fromarray(frame)
        
        draw = ImageDraw.Draw(frame)
        
        # 위험도 레벨에 따른 색상 설정
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
        
        # 위험도 정보 표시
        text = f"위험도: {level} ({risk_score:.2f})"
        draw.text((10, 10), text, fill=color)
        
        # 차량 정보 표시
        if vehicle_info:
            y_offset = 40
            for info in vehicle_info:
                vehicle_text = f"차량 {info['id']}: 속도 {info['velocity']:.1f} m/s"
                draw.text((10, y_offset), vehicle_text, fill=(255, 255, 255))
                y_offset += 20
        
        # 긴급 경고 프레임 추가
        if risk_score > 0.8:
            # 빨간색 테두리 추가
            draw.rectangle([(0, 0), (frame.width, frame.height)], outline=(255, 0, 0), width=5)
            draw.text((10, 70), "긴급 경고!", fill=(255, 0, 0))
        
        return frame
    
    def frame_to_pil(self, frame):
        """프레임을 PIL Image로 변환"""
        if frame is None:
            return None
        
        # 이미 PIL 이미지인 경우
        if isinstance(frame, Image.Image):
            return frame
        
        # NumPy 배열인 경우
        if isinstance(frame, np.ndarray):
            return Image.fromarray(frame)
        
        return None
