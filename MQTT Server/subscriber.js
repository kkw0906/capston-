// subscriber.js
require('dotenv').config();
const mqtt = require('mqtt');
const { MongoClient } = require('mongodb');


// -------------------------
// 환경 변수 및 설정
// -------------------------
const host = process.env.BROKER_URL;                // 예: xxx.s1.eu.hivemq.cloud
const port = Number(process.env.BROKER_PORT || 8883);

const statusTopic  = process.env.TOPIC || 'parking/status';          // 슬롯 상태 토픽
const illegalTopic = process.env.ILLEGAL_TOPIC || 'parking/illegal'; // 불법 주차 토픽

const mongoUrl   = process.env.MONGO_URI;
const dbName     = process.env.DB_NAME || 'parkingdb';
const rawColName = process.env.COLLECTION_NAME || 'parking';        // 원본 로그 컬렉션 이름

(async () => {
  try {
    // 1) Mongo 연결 및 컬렉션 핸들 준비
    const mongoClient = new MongoClient(mongoUrl);
    await mongoClient.connect();
    const db = mongoClient.db(dbName);

    const rawCol          = db.collection(rawColName);     // 원본 로그: 각 슬롯 최초 1건만
    const latestCol       = db.collection('latest');       // 슬롯별 최신 상태
    const changesCol      = db.collection('changes');      // 상태 변경 히스토리
    const illegalLatestCol = db.collection('illegal_latest'); // 🔹 불법 주차 최신 스냅샷

    console.log('[MongoDB] Connected');

    // 인덱스 생성
    await Promise.all([
      latestCol.createIndex({ slot: 1 }, { unique: true }),
      changesCol.createIndex({ changedAt: -1 }),
      illegalLatestCol.createIndex({ _id: 1 }), // _id=latest 하나만 쓸 예정
    ]);

    // 2) MQTT 연결
    console.log('[MQTT] ENV:', { host, port, statusTopic, illegalTopic });

    const mqttClient = mqtt.connect({
      host,
      port,
      protocol: 'mqtts',             // HiveMQ Cloud
      username: process.env.MQTT_USER,
      password: process.env.MQTT_PASS,
      rejectUnauthorized: false,     // 필요 시
    });

    mqttClient.on('connect', () => {
      console.log('[MQTT] Connected');
      mqttClient.subscribe([statusTopic, illegalTopic], (err) => {
        if (err) console.error('[MQTT] Subscribe error:', err);
        else console.log('[MQTT] Subscribed:', statusTopic, illegalTopic);
      });
    });

    mqttClient.on('error', (e) => console.error('[MQTT] Error:', e));

    // 3) 메시지 수신
    mqttClient.on('message', async (_topic, message) => {
      const raw = message.toString();

      console.log('\n--------------------------------');
      console.log('[MQTT] topic  =', _topic);
      console.log('[MQTT] payload=', raw);

      try {
        const now = new Date(Date.now() + 9 * 60 * 60 * 1000); // KST
        const p = JSON.parse(raw);
        console.log('[MQTT] parsed =', p);

        // 3-1) 슬롯 상태 토픽 처리
        if (_topic === statusTopic) {
          // 기대 형태: { slot: "slot1", status: 0|1, confidence, timestamp }
          if (typeof p.slot !== 'string') {
            console.log('[STATUS] invalid slot type, skip:', p);
            return;
          }

          // "slot1" → 1, "slot 8" → 8 등 숫자만 추출
          const match = p.slot.match(/(\d+)/);
          const slotNum = match ? Number(match[1]) : NaN;

          const okSlot = Number.isInteger(slotNum) && slotNum > 0;

          let statusNum;
          if (p.status === 'occupied') statusNum = 1;
          else if (p.status === 'empty') statusNum = 0;
          else statusNum = Number(p.status); // "0","1",0,1 모두 처리

          const okStatus = statusNum === 0 || statusNum === 1;

          console.log('[STATUS] okSlot=', okSlot, 'okStatus=', okStatus, 'statusNum=', statusNum);

          if (!okSlot || !okStatus) {
            console.log('[STATUS] invalid data, skip:', p);
            return;
          }

          // 이전 상태 조회 (문자/숫자 혼재를 고려해서 둘 다 검색)
          const prev = await latestCol.findOne({
            $or: [{ slot: slotNum }, { slot: p.slot }],
          });
          console.log('[STATUS] prev =', prev);

          // 상태가 동일하면 로그 찍고 반환
          if (prev && Number(prev.status) === statusNum) {
            await latestCol.updateOne(
              { _id: prev.id },
              { $set: { updateAt: now } },
            );
            console.log(`[STATUS] same status, ignore (slot=${slotNum}, status=${statusNum})`);
            return;
          }

          // 1) raw 로그: 각 슬롯 최초 1건만 저장
          if (!prev) {
            await rawCol.insertOne({
              ...p,
              slot: slotNum,                // 숫자 슬롯
              originalSlot: p.slot,         // 원래 문자열 슬롯 (참고용)
              status: statusNum,
              topic: _topic,
              firstSeenAt: now,
            });
            console.log(`[RAW] first log stored for slot=${slotNum}`);
          }

          // 2) latest: 항상 숫자 슬롯으로 upsert
          await latestCol.updateOne(
            { $or: [{ slot: slotNum }, { slot: p.slot }] },   // 기존 string 슬롯도 함께 매칭
            {
              $set: {
                slot: slotNum,             // 숫자로 통일
                status: statusNum,
                confidence: p.confidence,
                updatedAt: now,
              },
            },
            { upsert: true },
          );

          // 3) changes: 상태 변경 히스토리 기록
          await changesCol.insertOne({
            slot: slotNum,
            status: statusNum,
            confidence: p.confidence,
            changedAt: now,
          });

          console.log(`[CHANGE] slot=${slotNum} → status=${statusNum}`);
        }

        // 3-2) 불법 주차 토픽 처리 (로그 + DB 저장)
        else if (_topic === illegalTopic) {
          // 기대 형태: { timestamp, count, cars: [ {id, duration, x, y, msg}, ... ] }
          const { count, cars } = p;
          const carsArr = Array.isArray(cars) ? cars : [];

          // 콘솔 로그
          console.log('\n[ILLEGAL] 불법 주차 정보 수신');
          console.log(`   count = ${count}`);
          if (carsArr.length > 0) {
            carsArr.forEach((car) => {
              console.log(
                `   - id=${car.id}, duration=${car.duration}s, pos=(${car.x}, ${car.y}), msg=${car.msg}`,
              );
            });
          } else {
            console.log('   불법 차량 목록 비어 있음');
          }

          // DB에 "최근 1건"만 저장 (덮어쓰기 방식)
          await illegalLatestCol.updateOne(
            { _id: 'latest' }, // 항상 이 문서 한 개만 사용
            {
              $set: {
                _id: 'latest',
                count: count,
                cars: carsArr,
                timestamp: now,
                receivedAt: now,
                topic: _topic,
              },
            },
            { upsert: true },
          );
        }

        console.log('--------------------------------');
      } catch (e) {
        console.error('메시지 처리 오류:', e);
      }
    });
  } catch (e) {
    console.error('Subscriber Error:', e);
  }
})();


