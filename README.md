# 🅿️ AI 영상 인식 기반 스마트 파킹 시스템
### Real-Time Parking Occupancy Detection using YOLOv8 & Raspberry Pi

본 프로젝트는 **실시간 영상 인식 기반 주차 공간 점유 여부 파악 시스템**으로,  
주차장 내 카메라 영상에 대해 **YOLOv8 차량 객체 인식 모델**을 적용하여  
**각 주차구역의 빈 자리 / 주차 여부를 판별**하고 이를 **웹·모바일 대시보드로 전송**하는 IoT 시스템입니다.

---

## 📌 주요 기능 (Features)
- 🔍 **YOLOv8 기반 실시간 차량 감지**
- 🅿️ **ROI(Region of Interest) 기반 주차 구역 지정 기능**
- 🟢 **주차 상태(Occupied/Empty) 자동 판정**
- 📤 **MQTT 통신을 이용한 서버/웹 대시보드 데이터 전송**
- 🎛 **라즈베리파이 카메라 기반 실시간 영상 처리**
- 💻 **Node.js & Web 서버 연동 (차량 감지 결과 시각화)**
- 🖥 ** ROI 설정 프로그램 제공**

---

## 🛠 개발 환경 (Development Environment / Tools)

| 구분 | 상세 |
|------|------|
| **DL Model** | YOLOv8n (Ultralytics) |
| **Programming Language** | Python 3.10 |
| **Framework / Library** | OpenCV, NumPy, PyQt5, paho-mqtt, Ultralytics |
| **Hardware** | Raspberry Pi 5 / Pi Camera / USB Camera |
| **Communication** | MQTT (Mosquitto / HiveMQ Cloud) |
| **Server** | Node.js / Express |
| **Dataset** | Custom Parking Lot Images |
| **OS** | Raspberry Pi OS (Bookworm), Windows 10 |

---

## 📂 프로젝트 구조 (Project Structure)
<img width="1340" height="1121" alt="image" src="https://github.com/user-attachments/assets/f085e454-091e-49ca-9c1d-c6800e11238f" />

## 📂 프로젝트 결과 (Project Result)

<img width="224" height="177" alt="image" src="https://github.com/user-attachments/assets/a795f756-246f-498f-96f8-c59ba78c793f" />

<img width="185" height="182" alt="image" src="https://github.com/user-attachments/assets/ffe411fd-512c-412e-abc0-14ed374c3962" />

<img width="444" height="326" alt="image" src="https://github.com/user-attachments/assets/2bf3b7e1-daa0-43bd-b13b-fb917f29cf78" />


<img width="623" height="313" alt="image" src="https://github.com/user-attachments/assets/deeaf892-243f-4937-bd14-204350691193" />
