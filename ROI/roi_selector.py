# -*- coding: utf-8 -*-
import cv2
import json
import numpy as np # numpy 라이브러리 추가

# --- 전역 변수 ---
points = []            # 현재 그리고 있는 주차 공간의 꼭짓점
parking_spaces = []    # 완성된 모든 주차 공간의 좌표 리스트
image_file = '1124_testimage/test1.jpg' # 기준 이미지 파일명

# --- 마우스 클릭 이벤트를 처리하는 함수 ---
def mouse_callback(event, x, y, flags, param):
    global points, image

    # 마우스 왼쪽 버튼을 클릭했을 때
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"좌표 추가: ({x}, {y})")
        # 클릭한 위치에 초록색 원을 그려서 보여줌
        cv2.circle(image, (x, y), 5, (0, 255, 0), -1)

# --- 메인 코드 ---
try:
    image = cv2.imread(image_file)
    if image is None:
        raise FileNotFoundError
    clone = image.copy()
except FileNotFoundError:
    print(f"오류: '{image_file}' 파일을 찾을 수 없습니다. 1단계를 확인하세요.")
    exit()

cv2.namedWindow('Parking Space Selector', cv2.WINDOW_NORMAL)
cv2.setMouseCallback('Parking Space Selector', mouse_callback)

print("--- 주차 공간 좌표 설정 시작 ---")
print("1. '1번' 주차 공간의 꼭짓점 4개를 마우스로 클릭하세요.")
print("2. 4개를 모두 클릭했으면 키보드에서 'n' 키를 누르세요.")
print("3. 모든 주차 공간을 설정할 때까지 1, 2번을 반복하세요.")
print("4. 모든 작업이 끝났으면 's' 키를 눌러 저장하세요.")
print("5. 프로그램을 강제 종료하려면 'q' 키를 누르세요.")

while True:
    cv2.imshow('Parking Space Selector', image)
    key = cv2.waitKey(1) & 0xFF

    # 'n' 키: 현재 그린 다각형을 하나의 주차 공간으로 확정
    if key == ord('n'):
        if len(points) == 4:
            space_id = len(parking_spaces) + 1
            parking_spaces.append(points)
            print(f"✅ 주차 공간 {space_id}번 추가 완료: {points}")
            
            # 확정된 공간을 이미지에 빨간색 다각형으로 그려줌
            cv2.polylines(clone, [np.array(points, np.int32)], True, (0, 0, 255), 2)
            image = clone.copy()
            points = [] # 다음 공간을 위해 초기화
        else:
            print("⚠️ 오류: 꼭짓점은 반드시 4개여야 합니다. 다시 시도하세요.")
            points = []
            image = clone.copy() # 이미지 원상 복구

    # 's' 키: 현재까지의 모든 좌표를 파일로 저장
    elif key == ord('s'):
        with open('parking_spots.json', 'w') as f:
            json.dump(parking_spaces, f, indent=4)
        print(f"🎉 저장 완료! {len(parking_spaces)}개의 공간이 'parking_spots.json'에 저장되었습니다.")
        
    # 'q' 키: 프로그램 종료
    elif key == ord('q'):
        break

cv2.destroyAllWindows()