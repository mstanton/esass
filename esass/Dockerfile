FROM python:3.9-slim-buster

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY . .

# Sync dependencies and install the package
RUN uv sync --frozen

# Default command
CMD ["uv", "run", "esass"]
