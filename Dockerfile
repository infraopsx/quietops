FROM python:3.12-alpine
WORKDIR /app
COPY quietops/ /app/quietops/
COPY examples/ /app/examples/
USER 65534:65534
ENTRYPOINT ["python", "-m", "quietops"]
