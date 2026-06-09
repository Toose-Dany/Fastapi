from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import uvicorn
import json
import os
import hashlib

app = FastAPI(title="HealthSync API", version="1.0.0")

# CORS для WPF приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= МОДЕЛИ ДАННЫХ =================

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    height: float
    weight: float
    age: int  # ДОБАВЛЕНО
    gender: str = "male"
    activity_level: str = "moderate"


class UserLogin(BaseModel):
    username: str
    password: str


class StepsUpdate(BaseModel):
    user_id: int
    steps: int


class WaterUpdate(BaseModel):
    user_id: int
    water_ml: int


class SleepUpdate(BaseModel):
    user_id: int
    sleep_hours: float


class VitalsUpdate(BaseModel):
    user_id: int
    heart_rate: int
    systolic: int
    diastolic: int


class WeightUpdate(BaseModel):
    user_id: int
    weight: float


class HeightUpdate(BaseModel):
    user_id: int
    height: float


class GoalUpdate(BaseModel):
    user_id: int
    steps_goal: Optional[int] = None
    water_goal_ml: Optional[int] = None
    sleep_goal: Optional[float] = None
    calories_goal: Optional[int] = None


class SettingsUpdate(BaseModel):
    user_id: int
    city: Optional[str] = None
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    auto_sync: Optional[bool] = None
    daily_reminder: Optional[bool] = None
    reminder_time: Optional[str] = None


class ProfileUpdate(BaseModel):
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


# ================= БАЗА ДАННЫХ =================

class Database:
    def __init__(self):
        self.users: Dict[int, Dict] = {}
        self.next_user_id = 1
        self.load_from_file()

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def load_from_file(self):
        try:
            if os.path.exists("healthsync_data.json"):
                with open("healthsync_data.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.users = {int(k): v for k, v in data.get("users", {}).items()}
                    self.next_user_id = data.get("next_user_id", 1)
                print(f"📂 Загружено {len(self.users)} пользователей")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")

    def save_to_file(self):
        try:
            data = {
                "users": self.users,
                "next_user_id": self.next_user_id
            }
            with open("healthsync_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения: {e}")

    def get_user(self, user_id: int) -> Optional[Dict]:
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        for user in self.users.values():
            if user["username"].lower() == username.lower():
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        for user in self.users.values():
            if user["email"].lower() == email.lower():
                return user
        return None

    def create_user(self, username: str, email: str, password: str, height: float, weight: float, age: int = 25, gender: str = "male") -> Dict:
        user_id = self.next_user_id
        self.next_user_id += 1

        today = date.today().isoformat()

        user = {
            "id": user_id,
            "email": email,
            "username": username,
            "password": self.hash_password(password),
            "height": height,
            "weight": weight,
            "age": age,
            "gender": gender,
            "sync_coins": 100,
            "registration_date": datetime.now().isoformat(),
            "city": "Moscow",
            "theme": "Light",
            "notifications_enabled": True,
            "auto_sync": True,
            "daily_reminder": True,
            "reminder_time": "20:00",
            "steps_goal": 10000,
            "water_goal_ml": 2500,
            "sleep_goal": 8.0,
            "calories_goal": 2000,
            "last_heart_rate": 68,
            "last_systolic": 118,
            "last_diastolic": 75,
            "last_update_date": today
        }

        self.users[user_id] = user
        self.save_to_file()
        return user

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)
        if user and user["password"] == self.hash_password(password):
            return user
        return None


db = Database()


# ================= API ЭНДПОИНТЫ =================

@app.get("/")
async def root():
    return {"status": "ok", "message": "HealthSync API", "version": "1.0.0"}


@app.post("/users")
async def register_user(user_data: UserRegister):
    """Регистрация нового пользователя"""
    try:
        print(f"📝 Регистрация: {user_data.username}, {user_data.email}")
        print(f"   Возраст: {user_data.age}")
        print(f"   Пол: {user_data.gender}")
        
        existing = db.get_user_by_username(user_data.username)
        if existing:
            return JSONResponse(
                status_code=400,
                content={"detail": "Пользователь с таким именем уже существует"}
            )
        
        existing_email = db.get_user_by_email(user_data.email)
        if existing_email:
            return JSONResponse(
                status_code=400,
                content={"detail": "Пользователь с таким email уже существует"}
            )
        
        user = db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            height=user_data.height,
            weight=user_data.weight,
            age=user_data.age,
            gender=user_data.gender
        )
        
        db.save_to_file()
        
        print(f"✅ Пользователь создан: ID={user['id']}, возраст={user['age']}, пол={user['gender']}")
        
        return {
            "status": "success",
            "message": "Пользователь зарегистрирован",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "sync_coins": user["sync_coins"]
            }
        }
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Внутренняя ошибка сервера: {str(e)}"}
        )


@app.post("/login")
async def login(login_data: UserLogin):
    """Вход пользователя"""
    try:
        print(f"🔐 Вход: {login_data.username}")
        
        user = db.verify_user(login_data.username, login_data.password)
        
        if not user:
            print(f"❌ Ошибка входа: пользователь не найден или неверный пароль")
            return JSONResponse(
                status_code=401,
                content={"detail": "Неверный логин или пароль"}
            )
        
        # Берем возраст и пол из БД
        user_age = user.get("age", 25)
        user_gender = user.get("gender", "male")
        
        # Конвертируем пол для отображения
        gender_display = "Мужской" if user_gender == "male" else "Женский"
        
        print(f"✅ Успешный вход: {user['username']} (ID={user['id']})")
        print(f"   Возраст: {user_age}")
        print(f"   Пол: {user_gender} -> {gender_display}")
        
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "height": user["height"],
            "weight": user["weight"],
            "age": user_age,
            "sync_coins": user["sync_coins"],
            "steps": 0,
            "water": 0,
            "sleep": 0,
            "heart_rate": user["last_heart_rate"],
            "systolic": user["last_systolic"],
            "diastolic": user["last_diastolic"],
            "steps_goal": user["steps_goal"],
            "water_goal": user["water_goal_ml"] / 1000,
            "sleep_goal": user["sleep_goal"],
            "calories_goal": user["calories_goal"],
            "city": user["city"],
            "theme": user["theme"],
            "gender": gender_display,
            "notifications_enabled": user["notifications_enabled"],
            "auto_sync": user["auto_sync"],
            "daily_reminder": user["daily_reminder"],
            "reminder_time": user["reminder_time"]
        }
    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Внутренняя ошибка сервера: {str(e)}"}
        )


@app.get("/users/{user_id}")
async def get_user_data(user_id: int):
    """Получить данные пользователя"""
    user = db.get_user(user_id)
    if not user:
        return JSONResponse(
            status_code=404,
            content={"detail": "Пользователь не найден"}
        )
    
    user_gender = user.get("gender", "male")
    gender_display = "Мужской" if user_gender == "male" else "Женский"
    
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "height": user["height"],
        "weight": user["weight"],
        "age": user.get("age", 25),
        "sync_coins": user["sync_coins"],
        "steps": 0,
        "water": 0,
        "sleep": 0,
        "heart_rate": user["last_heart_rate"],
        "systolic": user["last_systolic"],
        "diastolic": user["last_diastolic"],
        "steps_goal": user["steps_goal"],
        "water_goal": user["water_goal_ml"] / 1000,
        "sleep_goal": user["sleep_goal"],
        "calories_goal": user["calories_goal"],
        "city": user["city"],
        "theme": user["theme"],
        "gender": gender_display,
        "notifications_enabled": user["notifications_enabled"],
        "auto_sync": user["auto_sync"],
        "daily_reminder": user["daily_reminder"],
        "reminder_time": user["reminder_time"]
    }


@app.post("/steps")
async def update_steps(data: StepsUpdate):
    """Обновление шагов"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    print(f"📊 Шаги: user={data.user_id}, steps={data.steps}")
    return {"status": "success", "steps": data.steps}


@app.post("/water")
async def update_water(data: WaterUpdate):
    """Обновление воды"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    print(f"💧 Вода: user={data.user_id}, water_ml={data.water_ml}")
    return {"status": "success", "water_ml": data.water_ml}


@app.post("/sleep")
async def update_sleep(data: SleepUpdate):
    """Обновление сна"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    print(f"😴 Сон: user={data.user_id}, sleep={data.sleep_hours}")
    return {"status": "success", "sleep_hours": data.sleep_hours}


@app.post("/vitals")
async def update_vitals(data: VitalsUpdate):
    """Обновление пульса и давления"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    user["last_heart_rate"] = data.heart_rate
    user["last_systolic"] = data.systolic
    user["last_diastolic"] = data.diastolic
    user["sync_coins"] = user.get("sync_coins", 0) + 5
    
    db.save_to_file()
    
    print(f"❤️ Витальные показатели: user={data.user_id}")
    
    return {
        "status": "success",
        "sync_coins": user["sync_coins"]
    }


@app.post("/weight")
async def update_weight(data: WeightUpdate):
    """Обновление веса"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    user["weight"] = data.weight
    db.save_to_file()
    
    print(f"⚖️ Вес: user={data.user_id}, weight={data.weight}")
    return {"status": "success", "weight": data.weight}


@app.post("/height")
async def update_height(data: HeightUpdate):
    """Обновление роста"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    user["height"] = data.height
    db.save_to_file()
    
    print(f"📏 Рост: user={data.user_id}, height={data.height}")
    return {"status": "success", "height": data.height}


@app.post("/goals")
async def update_goals(data: GoalUpdate):
    """Обновление целей"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    if data.steps_goal is not None:
        user["steps_goal"] = data.steps_goal
    if data.water_goal_ml is not None:
        user["water_goal_ml"] = data.water_goal_ml
    if data.sleep_goal is not None:
        user["sleep_goal"] = data.sleep_goal
    if data.calories_goal is not None:
        user["calories_goal"] = data.calories_goal
    
    db.save_to_file()
    
    return {"status": "success"}


@app.post("/settings")
async def update_settings(data: SettingsUpdate):
    """Обновление настроек"""
    user = db.get_user(data.user_id)
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    if data.city is not None:
        user["city"] = data.city
    if data.theme is not None:
        user["theme"] = data.theme
    if data.notifications_enabled is not None:
        user["notifications_enabled"] = data.notifications_enabled
    if data.auto_sync is not None:
        user["auto_sync"] = data.auto_sync
    if data.daily_reminder is not None:
        user["daily_reminder"] = data.daily_reminder
    if data.reminder_time is not None:
        user["reminder_time"] = data.reminder_time
    
    db.save_to_file()
    
    return {"status": "success"}


@app.post("/profile")
async def update_profile(data: ProfileUpdate):
    """Обновление профиля пользователя"""
    print("=" * 50)
    print(f"🔍 ОБНОВЛЕНИЕ ПРОФИЛЯ:")
    print(f"   user_id: {data.user_id}")
    print(f"   username: {data.username}")
    print(f"   email: {data.email}")
    print(f"   age: {data.age}")
    print(f"   gender: {data.gender}")
    print("=" * 50)
    
    user = db.get_user(data.user_id)
    if not user:
        print(f"❌ Пользователь не найден!")
        return JSONResponse(status_code=404, content={"detail": "Пользователь не найден"})
    
    if data.username is not None:
        user["username"] = data.username
    if data.email is not None:
        user["email"] = data.email
    if data.age is not None:
        user["age"] = data.age
    if data.gender is not None:
        user["gender"] = data.gender
    
    db.save_to_file()
    
    print(f"✅ Профиль обновлен: возраст={user.get('age')}, пол={user.get('gender')}")
    
    return {"status": "success"}


@app.get("/history/{user_id}")
async def get_history(user_id: int):
    """Получить историю (заглушка)"""
    return {
        "steps_history": [0, 0, 0, 0, 0, 0, 0],
        "water_history": [0, 0, 0, 0, 0, 0, 0],
        "sleep_history": [0, 0, 0, 0, 0, 0, 0],
        "calories_history": [0, 0, 0, 0, 0, 0, 0]
    }


@app.get("/weather/{city}")
async def get_weather(city: str):
    """Получить погоду"""
    try:
        import httpx
        
        coords = {
            "moscow": {"lat": 55.75, "lon": 37.62},
            "london": {"lat": 51.51, "lon": -0.13},
            "new york": {"lat": 40.71, "lon": -74.01},
        }
        
        city_lower = city.lower()
        if city_lower in coords:
            lat, lon = coords[city_lower]["lat"], coords[city_lower]["lon"]
        else:
            lat, lon = 55.75, 37.62
        
        async with httpx.AsyncClient() as client:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            response = await client.get(url, timeout=10.0)
            data = response.json()
            
            current = data.get("current_weather", {})
            temp = current.get("temperature", 20.0)
            weather_code = current.get("weathercode", 0)
            
            weather_codes = {
                0: "Ясно", 1: "В основном ясно", 2: "Переменная облачность",
                3: "Пасмурно", 45: "Туман", 51: "Легкая морось",
                61: "Дождь", 71: "Снег"
            }
            
            condition = weather_codes.get(weather_code, "Облачно")
            
            if temp < 10:
                recommendation = "🌬️ Прохладно, одевайтесь теплее"
            elif temp < 20:
                recommendation = "🌤️ Отличная погода для прогулки!"
            elif temp < 30:
                recommendation = "☀️ Тепло, не забывайте пить воду"
            else:
                recommendation = "🔥 Жарко, пейте больше воды"
            
            return {
                "temperature": temp,
                "condition": condition,
                "recommendation": recommendation
            }
    except Exception as e:
        print(f"⚠️ Ошибка погоды: {e}")
        return {
            "temperature": 20.0,
            "condition": "Облачно",
            "recommendation": "Данные временно недоступны"
        }


# ================= АДМИН ПАНЕЛЬ =================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>HealthSync - Админ панель</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #1A237E; margin-bottom: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; }
        .status-ok { color: green; }
        .refresh-btn { background: #2196F3; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 HealthSync - Админ панель</h1>
        
        <div class="card">
            <h3>📊 Статистика</h3>
            <p>Всего пользователей: <strong id="userCount">0</strong></p>
            <p>Сервер: <span class="status-ok">✅ Работает</span></p>
        </div>
        
        <div class="card">
            <h3>👥 Пользователи</h3>
            <button class="refresh-btn" onclick="loadUsers()">🔄 Обновить</button>
            <table>
                <thead>
                    <tr><th>ID</th><th>Имя</th><th>Email</th><th>Возраст</th><th>Пол</th><th>Вес</th><th>Рост</th><th>SyncCoins</th></tr>
                </thead>
                <tbody id="usersTable"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadUsers() {
            const res = await fetch('/admin/users');
            const users = await res.json();
            document.getElementById('userCount').innerText = users.length;
            document.getElementById('usersTable').innerHTML = users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.email}</td>
                    <td>${u.age}</td>
                    <td>${u.gender_display}</td>
                    <td>${u.weight} кг</td>
                    <td>${u.height} см</td>
                    <td>🪙 ${u.sync_coins}</td>
                </tr>
            `).join('');
        }
        
        loadUsers();
        setInterval(loadUsers, 5000);
    </script>
</body>
</html>
"""


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return ADMIN_HTML


@app.get("/admin/users")
async def admin_get_users():
    users_list = []
    for u in db.users.values():
        gender_display = "Мужской" if u.get("gender") == "male" else "Женский"
        users_list.append({
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "age": u.get("age", 25),
            "gender_display": gender_display,
            "weight": u["weight"],
            "height": u["height"],
            "sync_coins": u["sync_coins"]
        })
    return users_list


# ================= ЗАПУСК =================

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except:
        return '127.0.0.1'
    finally:
        s.close()


if __name__ == "__main__":
    ip = get_local_ip()
    print("\n" + "=" * 50)
    print("🏥 HealthSync API Server")
    print("=" * 50)
    print(f"🌐 Локальный адрес: http://{ip}:8000")
    print(f"📊 Админ панель: http://{ip}:8000/admin")
    print(f"📖 Документация: http://{ip}:8000/docs")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)