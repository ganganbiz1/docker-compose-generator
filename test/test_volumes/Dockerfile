FROM postgres:14-alpine

# Create directories
RUN mkdir -p /var/lib/postgresql/data /var/log/postgresql

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=postgres

# Define volumes
VOLUME ["/var/lib/postgresql/data", "/var/log/postgresql"]

EXPOSE 5432

CMD ["postgres"] 