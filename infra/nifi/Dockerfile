FROM apache/nifi:2.11.0

USER root

ADD https://jdbc.postgresql.org/download/postgresql-42.7.13.jar \
    /opt/nifi/drivers/postgresql.jar

RUN chown nifi:nifi /opt/nifi/drivers/postgresql.jar

USER nifi
