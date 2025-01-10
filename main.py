# cd D:\pythonFile\Lab4\weather\my_project
# uvicorn main:app --reload
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import aiohttp
import asyncio
import csv
from typing import List, Dict
from starlette.responses import HTMLResponse
import os

# 创建FastAPI应用实例
app = FastAPI()

# 配置模板目录，使用相对路径
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "weather/templates"))

# 用于存储所有城市及其天气数据的全局变量，初始化为空列表
all_weather_data = []

# 异步函数，用于获取单个城市的天气数据
async def get_weather(session, city_name, latitude, longitude) -> Dict[str, str]:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            temperature = data['current_weather']['temperature']
            return {'capital': city_name, 'temperature': temperature}
        else:
            return {'capital': city_name, 'temperature': 'Error fetching data'}

# 异步函数，从指定的CSV文件中加载城市坐标等相关信息
async def load_city_coordinates(file_path: str) -> List[Dict[str, str]]:
    cities = []
    # 使用相对路径加载CSV文件
    with open(os.path.join(os.path.dirname(__file__), "weather/europe.csv"), mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cities.append({
                'city': row['capital'],
                'country': row['country'],
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
            })
    return cities

# 异步函数，为所有城市获取天气数据
async def fetch_weather_for_all(cities: List[Dict[str, str]]):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for city in cities:
            city_full_name = f"{city['city']}, {city['country']}"
            tasks.append(get_weather(session, city_full_name, city['latitude'], city['longitude']))
        weather_results = await asyncio.gather(*tasks)
        return weather_results

# 首页路由，返回渲染后的HTML页面
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 更新天气数据的路由，获取所有城市天气数据并更新全局变量
@app.get("/update")
async def fetch_weather():
    global all_weather_data
    cities = await load_city_coordinates(os.path.join(os.path.dirname(__file__), "weather/europe.csv"))  # 加载城市坐标信息
    all_weather_data = await fetch_weather_for_all(cities)
    return all_weather_data

# 删除城市的路由，从全局天气数据中移除指定城市
@app.delete("/remove_city/{city_name}")
async def remove_city(city_name: str):
    global all_weather_data
    city_to_remove = next((city for city in all_weather_data if city['capital'] == city_name), None)

    if city_to_remove is None:
        raise HTTPException(status_code=404, detail="City not found")

    all_weather_data = [city for city in all_weather_data if city['capital'] != city_name]

    return JSONResponse(content={"status": "success", "message": f"City {city_name} removed successfully."})
