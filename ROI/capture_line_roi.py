# -*- coding: utf-8 -*-
import cv2
import json
import numpy as np

# --- 전역 변수 ---
points = []
parking_spaces = []
captured_frame = None  # 캡처된(일시정지된) 프레임을 저장할 변수
is_frame_captured = False # 현재 프레임이 캡처(일시정지)된 상태인지 확인하는 플래그

# --- 마우스 클릭 이벤트를 처리하는 함수 ---
def mouse_callback(event, x, y, flags, param):
    global points, captured_frame

    # 프레임이 캡처된 상태에서만 마우스 클릭이 동작하도록 함
    if is_frame_captured and event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"좌표 추가: ({x}, {y})")
        # 클릭한 위치에 초록색 원을 그려서 보여줌
        cv2.circle(captured_frame, (x, y), 5, (0, 255, 0), -1)

# --- 메인 코드 ---
# USB 카메라 연결 (보통 0번 장치)
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("오류: 카메라를 열 수 없습니다. 연결 상태를 확인하세요.")
    exit()

cv2.namedWindow('Parking Space Selector', cv2.WINDOW_NORMAL)
cv2.setMouseCallback('Parking Space Selector', mouse_callback)

print("--- 실시간 주차 공간 좌표 설정 ---")
print("1. 카메라를 원하는 위치에 고정시키세요.")
print("2. '스페이스바'를 눌러 현재 화면을 캡처(일시정지)하세요.")

clone = None # 캡처된 프레임의 원본을 저장할 변수

while True:
    if not is_frame_captured:
        # --- 실시간 영상 출력 모드 ---
        ret, frame = cap.read()
        if not ret:
            print("오류: 카메라에서 프레임을 읽을 수 없습니다.")
            break
       
        # 화면에 안내 텍스트 표시
        cv2.putText(frame, "Press 'SPACE' to capture", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        display_frame = frame
    else:
        # --- 좌표 설정 모드 (일시정지된 화면) ---
        display_frame = captured_frame
   
    cv2.imshow('Parking Space Selector', display_frame)
    key = cv2.waitKey(1) & 0xFF

    # '스페이스바' 키: 화면 캡처 및 좌표 설정 모드 진입
    if key == ord(' '):
        if not is_frame_captured:
            is_frame_captured = True
            captured_frame = frame.copy()
            clone = frame.copy()
            print("\n--- 화면 캡처 완료! 좌표 설정을 시작하세요. ---")
            print(" - 주차 공간의 꼭짓점 4개를 클릭하고 'n'을 누르세요.")
            print(" - 모든 작업이 끝나면 's'를 눌러 저장합니다.")
            print(" - 다시 캡처하려면 'r'을 눌러 리셋하세요.")

    # 'n' 키: 현재 그린 다각형을 하나의 주차 공간으로 확정
    elif is_frame_captured and key == ord('n'):
        if len(points) == 4:
            space_id = len(parking_spaces) + 1
            parking_spaces.append(points)
            print(f"✅ 주차 공간 {space_id}번 추가 완료: {points}")
           
            # 확정된 공간을 이미지에 빨간색 다각형으로 그려줌
            cv2.polylines(clone, [np.array(points, np.int32)], True, (0, 0, 255), 2)
            captured_frame = clone.copy()
            points = []
        else:
            print("⚠️ 오류: 꼭짓점은 반드시 4개여야 합니다. 다시 시도하세요.")
            points = []
            captured_frame = clone.copy()

    # 's' 키: 현재까지의 모든 좌표를 파일로 저장
    elif is_frame_captured and key == ord('s'):
        with open('parking_spots2.json', 'w') as f:
            json.dump(parking_spaces, f, indent=4)
        print(f"🎉 저장 완료! {len(parking_spaces)}개의 공간이 'parking_spots2.json'에 저장되었습니다.")
       
    # 'r' 키: 리셋하고 다시 실시간 영상 모드로
    elif is_frame_captured and key == ord('r'):
        is_frame_captured = False
        points = []
        parking_spaces = []
        captured_frame = None
        clone = None
        print("\n--- 리셋 완료! 다시 '스페이스바'를 눌러 캡처하세요. ---")

    # 'q' 키: 프로그램 종료
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
