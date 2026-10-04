# 3장 실습용 쇼핑몰 앱 (secbook-shop)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd -r -s /usr/sbin/nologin shop && mkdir -p /data && chown shop /data
USER shop
ENV SHOP_DB=/data/shop.db
EXPOSE 5000
CMD ["python", "app.py"]
