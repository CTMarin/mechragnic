FROM apache/airflow:3.3.2-python3.13

COPY --chown=airflow:0 pyproject.toml README.md LICENSE /opt/mechragnic/
COPY --chown=airflow:0 src /opt/mechragnic/src

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" /opt/mechragnic