FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPSPILOT_RUNBOOKS=/app/runbooks/runbooks.yaml
COPY pyproject.toml README.md ./
COPY src ./src
COPY runbooks ./runbooks
RUN pip install --no-cache-dir . "uvicorn[standard]>=0.30"
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "opspilot.api:app", "--host", "0.0.0.0", "--port", "8000"]
