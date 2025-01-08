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

# 创建FastAPI应用实例
app = FastAPI()

# 配置模板目录，这里需确保路径指向正确的模板文件夹位置
templates = Jinja2Templates(directory="C:/Users/Administrator/PycharmProjects/lab4/weather/templates")

# 用于存储所有城市及其天气数据的全局变量，初始化为空列表
all_weather_data = []


# 异步函数，用于获取单个城市的天气数据
async def get_weather(session, city_name, latitude, longitude) -> Dict[str, str]:
    """
    根据给定的经纬度信息，向天气 API 发起请求获取城市的天气数据。

    参数:
    - session: aiohttp的会话对象，用于发起HTTP请求。
    - city_name: 城市名称，格式通常为 "城市名, 国家名"。
    - latitude: 城市的纬度信息。
    - longitude: 城市的经度信息。

    返回:
    - 包含城市名称和对应温度信息（若获取成功）或者错误提示（若获取失败）的字典。
    """
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
    """
    从给定的CSV文件路径中读取城市相关信息，包括城市名、国家、纬度和经度。

    参数:
    - file_path: CSV文件的完整路径。

    返回:
    - 包含城市各项信息的字典列表，每个字典对应一个城市的信息。
    """
    cities = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cities.append({
                'city': row['capital'],  # 提取CSV文件中 'capital' 列作为城市名
                'country': row['country'],  # 提取CSV文件中 'country' 列作为所属国家
                'latitude': float(row['latitude']),  # 提取CSV文件中 'latitude' 列并转换为浮点数作为纬度
                'longitude': float(row['longitude']),  # 提取CSV文件中 'longitude' 列并转换为浮点数作为经度
            })
    return cities


# 异步函数，为所有城市获取天气数据
async def fetch_weather_for_all(cities: List[Dict[str, str]]):
    """
    针对给定的城市列表，并发地调用 get_weather 函数获取每个城市的天气数据。

    参数:
    - cities: 包含城市相关信息的字典列表。

    返回:
    - 包含所有城市天气数据结果的列表。
    """
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
    global all_weather_data  # 使用全局变量存储城市天气数据
    cities = await load_city_coordinates('C:/Users/Administrator/PycharmProjects/lab4/europe.csv')  # 加载城市坐标信息
    all_weather_data = await fetch_weather_for_all(cities)
    return all_weather_data


# 删除城市的路由，从全局天气数据中移除指定城市
@app.delete("/remove_city/{city_name}")
async def remove_city(city_name: str):
    global all_weather_data  # 使用全局变量存储城市天气数据
    # 在已有的天气数据中查找要删除的城市
    city_to_remove = next((city for city in all_weather_data if city['capital'] == city_name), None)

    if city_to_remove is None:
        raise HTTPException(status_code=404, detail="City not found")

    # 从全局天气数据列表中移除该城市
    all_weather_data = [city for city in all_weather_data if city['capital']!= city_name]

    return JSONResponse(content={"status": "success", "message": f"City {city_name} removed successfully."})