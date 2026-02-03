import os
import logging
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(title="Margiana Logistics API")

# Добавьте CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ключ для аутентификации
API_KEY = os.getenv('SYNC_API_KEY', 'margiana_sync_key_2024_secure_change_this')

# Pydantic модели
class OrderSyncData(BaseModel):
    order_number: str
    client_name: str
    container_count: Optional[int] = 0
    goods_type: Optional[str] = None
    route: Optional[str] = None
    transit_port: Optional[str] = None
    document_number: Optional[str] = None
    chinese_transport_company: Optional[str] = None
    iranian_transport_company: Optional[str] = None
    status: Optional[str] = "New"
    status_color: Optional[str] = "#FFFFFF"
    creation_date: Optional[datetime] = None
    loading_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    arrival_iran_date: Optional[datetime] = None
    truck_loading_date: Optional[datetime] = None
    arrival_turkmenistan_date: Optional[datetime] = None
    client_receiving_date: Optional[datetime] = None
    arrival_notice_date: Optional[datetime] = None
    tkm_date: Optional[datetime] = None
    eta_date: Optional[datetime] = None
    has_loading_photo: Optional[bool] = False
    has_local_charges: Optional[bool] = False
    has_tex: Optional[bool] = False
    notes: Optional[str] = None
    additional_info: Optional[str] = None
    sync_type: Optional[str] = "update"
    sync_timestamp: Optional[datetime] = None

# Функция для проверки API ключа
def verify_api_key(api_key: str = Header(None, alias="api-key")):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Эндпоинт для проверки связи
@app.get("/")
async def root():
    return {"status": "ok", "service": "Margiana Logistics API", "timestamp": datetime.now().isoformat()}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Margiana Logistics API", "timestamp": datetime.now().isoformat()}

# Эндпоинт для синхронизации заказа
@app.post("/api/sync/order")
async def sync_order(
    order_data: OrderSyncData,
    api_key: str = Depends(verify_api_key)
):
    try:
        logger.info(f"Syncing order: {order_data.order_number}")
        return {"status": "success", "message": "Order synced", "order_number": order_data.order_number}
    except Exception as e:
        logger.error(f"Error in sync_order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
