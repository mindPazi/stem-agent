FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

RUN git clone https://github.com/soarsmu/BugsInPy.git /opt/BugsInPy

ENV BUGSINPY_ROOT=/opt/BugsInPy
ENV BUGSINPY_CACHE=/tmp/bugsinpy-project-cache
ENV BUGSINPY_WORKSPACE=/tmp/bugsinpy-eval-workspace

COPY . .
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "pytest", "-q"]
