# Provedor de SMS fake — APOIO ao desafio. Só biblioteca padrão.
FROM python:3.12-slim
WORKDIR /srv
COPY server.py .
ENV PYTHONUNBUFFERED=1 DELIVERED_LOG=/data/delivered.jsonl
EXPOSE 9000
CMD ["python", "server.py"]
