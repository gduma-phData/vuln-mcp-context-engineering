FROM python:3.11-slim

WORKDIR /app

COPY environment.yml .
RUN pip install fastapi uvicorn httpx python-dotenv pyjwt cryptography snowflake-connector-python snowflake-core

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
