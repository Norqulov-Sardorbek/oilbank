FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create user and directory structure with proper permissions
RUN mkdir -p /home/user/web/staticfiles /home/user/web/media && \
    useradd -u 1000 -d /home/user user && \
    chown -R user:user /home/user

WORKDIR /home/user/web

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev gcc python3-dev libjpeg-dev zlib1g-dev gettext bash && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY --chown=user:user requirements*.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (ensure proper permissions)
COPY --chown=user:user . .

# Set permissions for Django files
USER root
RUN chown -R user:user /home/user/web && \
    find /home/user/web -type d -exec chmod 755 {} \; && \
    find /home/user/web -type f -exec chmod 644 {} \;

# Set permissions for static and media files
USER user
RUN chmod -R 755 /home/user/web/staticfiles /home/user/web/media


# Prepare entrypoint scripts
USER root
COPY wait-for-it.sh /wait-for-it.sh
COPY entrypoint.sh /home/user/web/entrypoint.sh
RUN chmod +x /wait-for-it.sh /home/user/web/entrypoint.sh
USER user

EXPOSE 8005
ENTRYPOINT ["/wait-for-it.sh", "db:5432", "--", "sh", "/home/user/web/entrypoint.sh"]