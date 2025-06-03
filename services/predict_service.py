# services/predict_service.py
import aiohttp
import os

class PredictService:
    def __init__(self):
        self.api_url = os.getenv("PREDICT_API_URL", "http://127.0.0.1:5000/api/predict")

    async def predict(self, message: str):
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(self.api_url, json={"message": message})
                if response.status != 200:
                    print(f"❌ API Error: {response.status}")
                    return []

                data = await response.json()
                print("✅ API Response:", data)
                return data.get("results", [])
        except Exception as e:
            print(f"❌ Exception calling API: {e}")
            return []
