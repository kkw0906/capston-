# -*- coding: utf-8 -*-

###### [최종 마스터 코드 v5.2] ######
# 1. 추적 알고리즘 개선 (Best Match): 지나가는 차량에 의한 타이머 리셋 방지
# 2. [수정] 콘솔 실시간 로그 출력 기능 강화 (매 전송시 데이터 출력)
# 3. 감지 구역(ROI) 설정 기능 포함

import cv2
import json
import numpy as np
import math
from ultralytics import YOLO
import requests
import time

# ==================================================================
# [사용자 설정 영역]
# ==================================================================

# 1. 실행 모드 ("camera", "video", "image")
SOURCE_MODE = "camera"

# 2. 파일 경로 (PC 테스트용)
#VIDEO_PATH = "cctv_20251201_171846.avi"
VIDEO_PATH = "cctv_20251201_175218.avi"
IMAGE_PATH = "test_image.jpg"

# 3. 서버 전송 설정 (기본값 True)
SEND_TO_SERVER = True
SERVER_URL = "http://localhost:5001/yolo"

# 4. 모델 및 데이터 파일
MODEL_PATH = 'normal_gray.pt'      
JSON_PATH = 'parking_spots2.json'  

# 5. 불법 주정차 기준
ILLEGAL_TIME_LIMIT = 30     # 30초 이상 정차 시 불법
MOVEMENT_THRESHOLD = 30     # 30픽셀 이내 움직임은 '정차'로 간주

# 6. 감지 허용 구역 (ROI)
# [주의] 아까 따신 좌표로 꼭 교체해주세요! (아래는 임의값)
MONITOR_ZONE = [[14, 473], [126, 187], [265, 32], [457, 11], [634, 288], [639, 475], [12, 474]]

# ==================================================================
# [시스템 초기화]
# ==================================================================
try:
    print("[Init] 모델 및 주차면 좌표 로딩 중...")
    model = YOLO(MODEL_PATH)
    with open(JSON_PATH, 'r') as f:
        parking_spaces = json.load(f)
    print("[Init] 로딩 완료.")
except Exception as e:
    print(f"[Error] 초기화 실패: {e}")
    exit()

tracked_objects = []  # 추적 중인 차량 리스트
next_object_id = 0    # 차량 고유 ID

# ==================================================================
# [핵심 로직] 프레임 처리 함수
# ==================================================================
def process_frame(frame):
    global tracked_objects, next_object_id

    vis_frame = frame.copy()
   
    # --- 0. 감지 구역 시각화 ---
    monitor_poly = np.array(MONITOR_ZONE, np.int32)
    cv2.polylines(vis_frame, [monitor_poly], True, (255, 0, 0), 1)
   
    # --- 1. YOLO 객체 인식 ---
    results = model(frame, verbose=False)[0]

    # --- 2. 차량 필터링 (ROI 내부 차량만) ---
    detected_cars = []
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
       
        if cv2.pointPolygonTest(monitor_poly, (cx, cy), False) >= 0:
            detected_cars.append({'center': (cx, cy), 'box': [x1, y1, x2, y2]})

    # --- 3. 주차 vs 통로(불법후보) 구분 ---
    current_parking_status = [False] * len(parking_spaces)
    aisle_cars = []

    for car in detected_cars:
        cx, cy = car['center']
        is_parked = False
       
        for i, space in enumerate(parking_spaces):
            space_poly = np.array(space, np.int32)
            if cv2.pointPolygonTest(space_poly, (cx, cy), False) >= 0:
                current_parking_status[i] = True
                is_parked = True
                break
       
        if not is_parked:
            aisle_cars.append(car)

    # --- 4. [개선된 추적 로직] Best Match Algorithm ---
    # 거리 기반으로 가장 가까운 차량끼리 먼저 매칭하여 ID 스틸 방지
   
    # (1) 모든 가능한 매칭 쌍의 거리 계산
    possible_matches = []
    for t_idx, obj in enumerate(tracked_objects):
        for c_idx, car in enumerate(aisle_cars):
            prev_cx, prev_cy = obj['center']
            cur_cx, cur_cy = car['center']
            dist = math.sqrt((cur_cx - prev_cx)**2 + (cur_cy - prev_cy)**2)
           
            if dist < 100: # 매칭 가능한 거리 한계
                possible_matches.append({'dist': dist, 't_idx': t_idx, 'c_idx': c_idx})
   
    # (2) 거리가 짧은 순서대로 정렬 (핵심!)
    possible_matches.sort(key=lambda x: x['dist'])
   
    # (3) 매칭 수행
    used_tracks = set()
    used_cars = set()
    new_tracked_objects = []
   
    # 기존 객체 중 매칭된 것들 처리
    for match in possible_matches:
        t_idx = match['t_idx']
        c_idx = match['c_idx']
        dist = match['dist']
       
        if t_idx in used_tracks or c_idx in used_cars:
            continue # 이미 매칭된 객체는 패스
           
        obj = tracked_objects[t_idx]
        car = aisle_cars[c_idx]
       
        # 타이머 로직 적용
        if dist < MOVEMENT_THRESHOLD: # 정차 중
            obj['timer'] += 1
        else: # 이동 중
            obj['timer'] = 0
           
        # 정보 업데이트
        obj['center'] = car['center']
        obj['box'] = car['box']
       
        new_tracked_objects.append(obj)
        used_tracks.add(t_idx)
        used_cars.add(c_idx)
   
    # (4) 매칭 안 된 새로운 차량 추가
    for c_idx, car in enumerate(aisle_cars):
        if c_idx not in used_cars:
            new_tracked_objects.append({
                'id': next_object_id,
                'center': car['center'],
                'box': car['box'],
                'timer': 0,
                'alerted': False
            })
            next_object_id += 1
           
    tracked_objects = new_tracked_objects

    # --- 5. 서버 전송 데이터 생성 ---
    # 5-1. 주차면 상태 (slots)
    payload_slots = []
    for i, status in enumerate(current_parking_status):
        payload_slots.append({
            "slot": f"slot{i+1}",
            "status": "occupied" if status else "empty",
            "confidence": 0.95 if status else 0.0
        })

    # 5-2. 불법 차량 정보 (illegal_cars)
    illegal_payload = []
    for obj in tracked_objects:
        # [중요] 설정된 시간(30초) 이상 정차한 차량만 보냄
        if obj['timer'] >= ILLEGAL_TIME_LIMIT:
            illegal_payload.append({
                "id": obj['id'],
                "duration": obj['timer'],
                "x": int(obj['center'][0]),  # int로 변환하여 전송
                "y": int(obj['center'][1]),  # int로 변환하여 전송
                "msg": "Illegal Parking"
            })
            if not obj['alerted']:
                # 최초 감지 시 별도 경고 로그
                print(f"🚨 [경고] ID:{obj['id']} 위반 확정! 위치:{obj['center']}")
                obj['alerted'] = True

    final_payload = {
        "slots": payload_slots,
        "illegal_cars": illegal_payload,
        "illegal_count": len(illegal_payload)
    }

    # --- 6. 화면 그리기 ---
    # (1) 주차 구역
    for i, space in enumerate(parking_spaces):
        status = current_parking_status[i]
        color = (0, 0, 255) if status else (0, 255, 0)
        cv2.polylines(vis_frame, [np.array(space, np.int32)], True, color, 2)
        cv2.putText(vis_frame, f"{i+1}", (space[0][0], space[0][1]-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
   
    # (2) 불법 차량
    for obj in tracked_objects:
        x1, y1, x2, y2 = obj['box']
        timer = obj['timer']
       
        if timer < ILLEGAL_TIME_LIMIT:
            color = (0, 255, 255) # Yellow
            text = f"Wait: {timer}s"
            thickness = 2
        else:
            color = (255, 0, 0)   # Blue
            text = f"ILLEGAL! {timer}s"
            thickness = 4

        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, thickness)
        cv2.putText(vis_frame, text, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return vis_frame, final_payload

# ==================================================================
# [통신 함수] - 수정됨: 실시간 로그 출력
# ==================================================================
def send_data(payload):
    # 1. 콘솔에 전송 데이터 요약 출력 (실시간 확인용)
    occupied = len([s for s in payload['slots'] if s['status'] == 'occupied'])
    total = len(payload['slots'])
    illegal = payload['illegal_count']
   
    current_time = time.strftime("%H:%M:%S")
   
    # 한 줄 로그 출력
    print(f"[{current_time}] 주차면: {occupied}/{total} 점유 | 불법주차: {illegal}대 감지")
   
    # 불법차량이 있을 경우 상세 데이터도 출력
    if illegal > 0:
        print(f"   >> 불법차량 데이터: {json.dumps(payload['illegal_cars'], ensure_ascii=False)}")

    # 2. 실제 서버 전송
    if not SEND_TO_SERVER:
        return

    try:
        requests.post(SERVER_URL, json=payload, timeout=0.5)
    except Exception as e:
        print(f"[Network Error] {e}")

# ==================================================================
# [메인 실행 루프]
# ==================================================================
print(f"시스템 시작 - 모드: {SOURCE_MODE}, 서버전송: {SEND_TO_SERVER}")

cap = None
if SOURCE_MODE == "camera":
    # Arducam 호환성 옵션 적용
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
elif SOURCE_MODE == "video":
    cap = cv2.VideoCapture(VIDEO_PATH)
elif SOURCE_MODE == "image":
    frame = cv2.imread(IMAGE_PATH)
    if frame is not None:
        vis, payload = process_frame(frame)
        send_data(payload)
        cv2.imshow('Smart Parking (Image)', vis)
        cv2.waitKey(0)
    exit()

if not cap or not cap.isOpened():
    print("영상 소스를 열 수 없습니다.")
    exit()

frame_counter = 0

while True:
    ret, frame = cap.read()
    if not ret: break
   
    frame_counter += 1
   
    # 30프레임마다 실행
    if frame_counter % 30 == 0:
        vis_frame, payload = process_frame(frame)
        send_data(payload)
       
        # 화면 출력
        cv2.imshow('Smart Parking System', vis_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
