FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings pyyaml cryptography httpx rich
COPY . .
EXPOSE 8080
CMD ["uvicorn","apps.gateway.main:app","--host","0.0.0.0","--port","8080"]

