FROM python:3.12-slim
RUN pip install fastapi
# ruleid: custom_dockerfile_missing-user
CMD ["uvicorn", "app:app"]
