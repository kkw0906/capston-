// app.js
require('dotenv').config();
const express = require('express');
const { MongoClient } = require('mongodb');

const mongoUrl = process.env.MONGO_URI;
const dbName   = process.env.DB_NAME || 'parkingdb';
const PORT     = Number(process.env.PORT) || 4000;

(async () => {
  try {
    const mongoClient = new MongoClient(mongoUrl);
    await mongoClient.connect();
    const db = mongoClient.db(dbName);

    const latestCol        = db.collection('latest');
    const illegalLatestCol = db.collection('illegal_latest');

    console.log('[MongoDB] API Connected');

    const app = express();
    app.use(express.json());

    // 1) 슬롯 상태 API
    // 응답: { items: [ { id, status, confidence, updatedAt }, ... ] }
    app.get('/api/updates', async (req, res) => {
  try {
    const docs = await latestCol
      .find({})
      .sort({ slot: 1 })
      .toArray();

    // slot -> id 로 이름 바꾸고, items 배열 안에 넣어서 응답
    const items = docs.map((doc) => ({
      id: doc.slot,                // 👈 Flutter: itemData['id']
      status: doc.status,          // 👈 Flutter: itemData['status']
      confidence: doc.confidence,
      updatedAt: doc.updatedAt,
    }));

    res.json({ items });           // 👈 Flutter: responseData['items']
  } catch (err) {
    console.error('/api/updates error:', err);
    res.status(500).json({ error: 'Server Error' });
  }
});
    // 2) 불법 주차 차량 API
    // 응답: { vehicles: [ { id, x, y, duration, msg }, ... ] }
    app.get('/api/vehicles', async (req, res) => {
      try {
        const latest = await illegalLatestCol.findOne({ _id: 'latest' });

        if (!latest || !Array.isArray(latest.cars)) {
          return res.json({ vehicles: [] });
        }

        const vehicles = latest.cars.map((car, idx) => ({
          id: car.id ?? idx,        // YOLO id 없으면 인덱스라도 넣어줌
          x: car.x,
          y: car.y,
          duration: car.duration,
          msg: car.msg,
        }));

        res.json({ vehicles });
      } catch (err) {
        console.error('/api/vehicles error:', err);
        res.status(500).json({ error: 'Server Error' });
      }
    });

    app.listen(PORT, () => {
      console.log(`🚀 [API] listening on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error('[API] Startup Error:', err);
  }
})();
