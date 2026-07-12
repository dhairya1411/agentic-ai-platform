FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY pyproject.toml README.md ./
RUN python -m pip install --no-cache-dir .
COPY src ./src
RUN chown -R app:app /app
USER app
CMD ["python", "-m", "agentic_ai_worker"]
