FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Copy policy files
COPY policy.py .
COPY kit.py .
COPY evaluate.py .
COPY src/ ./src/

# No external dependencies required - uses Python standard library only

# Set entrypoint for policy evaluation
ENTRYPOINT ["python", "policy.py"]
