require("dotenv").config();

const mqtt = require("mqtt");

const express = require("express");



// -----------------------------------------------------------

// [MQTT 설정]

// -----------------------------------------------------------

const options = {

  host: process.env.BROKER_URL || "test.mosquitto.org",

  port: Number(process.env.BROKER_PORT) || 8883,

  protocol: "mqtts",

  username: process.env.MQTT_USER,

  password: process.env.MQTT_PASS,

  // rejectUnauthorized: false, // 필요시 주석 해제

};



const client = mqtt.connect(options);

const app = express();



app.use(express.json());



// -----------------------------------------------------------

// [MQTT 연결 이벤트]

// -----------------------------------------------------------

client.on("connect", () => {

  console.log("✅ [MQTT] 브로커에 연결되었습니다.");

});



client.on("error", (err) => {

  console.error("❌ [MQTT] 연결 오류:", err);

});



// -----------------------------------------------------------

// [핵심] 파이썬(YOLO) 데이터를 받는 라우터

// -----------------------------------------------------------

app.post("/yolo", (req, res) => {

  try {

    // 1. 파이썬이 보낸 모든 데이터 받기 (slots, illegal_cars, illegal_count)

    const { slots, illegal_cars, illegal_count } = req.body;

    const now = new Date().toLocaleTimeString();



    // 데이터 유효성 검사

    if (!Array.isArray(slots)) {

      return res.status(400).json({ error: "slots 데이터 형식이 잘못되었습니다." });

    }



    // 2. 콘솔 출력 현재 상태를 터미널에 보여줌

    const occupiedCount = slots.filter(s => s.status === "occupied").length;

    console.log(`\n[${now}] 데이터 수신됨 -----------------------------`);

    console.log(`   🅿️  주차 상태: ${occupiedCount} / ${slots.length} 대 주차 중`);



    if (illegal_count > 0) {

      console.log(`   🚨 [경고] 불법 차량 ${illegal_count}대 감지!`);

      // 불법 차량 상세 정보 출력 (좌표 포함)

      if (Array.isArray(illegal_cars)) {

        illegal_cars.forEach(car => {

          console.log(`      👉 ID:${car.id} | 시간:${car.duration}초 | 위치:(${car.x}, ${car.y})`);

        });

      }

    } else {

      console.log(`   ✅ 불법 주차 차량 없음`);

    }



    // 3. [MQTT 전송 1] 기존 슬롯 정보 전송 (parking/status)

    //    기존 코드와의 호환성을 위해 유지

    slots.forEach((s) => {

      const statusNum = s.status === "occupied" ? 1 : 0;

      const data = {

        slot: s.slot,

        status: statusNum,

        confidence: s.confidence,

        timestamp: new Date()

      };

      // 슬롯별 상태 전송

      client.publish(process.env.TOPIC || "parking/status", JSON.stringify(data));

    });



    // 4. [MQTT 전송 2] 불법 차량 정보 전송 (parking/illegal) - **신규 추가됨**

    //    불법 차량 정보는 별도 토픽으로 보내서 관리하는 것이 깔끔함

    if (illegal_count > 0) {

        const illegalData = {

            timestamp: new Date(),

            count: illegal_count,

            cars: illegal_cars // 여기에 좌표(x,y)가 들어있음

        };

        client.publish("parking/illegal", JSON.stringify(illegalData));

        console.log("   📡 [MQTT] 불법 차량 정보 전송 완료 (Topic: parking/illegal)");

    }



    // 파이썬에게 잘 받았다고 응답

    res.json({ ok: true, count: slots.length, illegal: illegal_count });



  } catch (err) {

    console.error("❌ 처리 중 오류 발생:", err);

    res.status(500).json({ error: "Server Error" });

  }

});



// -----------------------------------------------------------

// [서버 시작]

// -----------------------------------------------------------

const HTTP_PORT = process.env.YOLO_HTTP_PORT || 5001;

app.listen(HTTP_PORT, () => {

  console.log(`🚀 [Server] Node.js 서버 대기 중: http://localhost:${HTTP_PORT}/yolo`);


});

