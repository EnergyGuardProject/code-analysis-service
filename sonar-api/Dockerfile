FROM python:3.11

RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip curl openjdk-21-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Install sonar-scanner
RUN curl -sSLo scanner.zip \
    https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip && \
    unzip scanner.zip && mv sonar-scanner-* /opt/sonar && rm scanner.zip

ENV PATH="/opt/sonar/bin:${PATH}"

WORKDIR /app
COPY python_requirements.txt /app/
RUN pip install -r python_requirements.txt

COPY . /app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
