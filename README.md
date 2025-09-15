# Rexus 🛡️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Rexus is a full-featured API Gateway built to provide essential tools for managing and monitoring web services. It acts as a universal proxy to intercept requests and apply features like authentication, caching, rate limiting, and real-time monitoring through a live analytics dashboard.

The project is built with a focus on a scalable architecture, utilizing a modern technology stack including FastAPI, PostgreSQL, Redis, and WebSockets. The entire environment is containerized with Docker for straightforward setup and deployment.

### Video Demo

https://youtu.be/Q2JqmPYL_RE

### Features

* **API Key Authentication**: Secure endpoints with a robust API key generation and validation system.
* **High-Speed Caching**: Reduces latency and upstream API load by caching `GET` request responses in Redis.
* **Sliding Window Rate Limiting**: Protects APIs from abuse with an efficient, Redis-based sliding window algorithm.
* **Asynchronous Logging**: Request logs are buffered in Redis and written to the database by a separate background worker to ensure the gateway remains fast.
* **Real-time Analytics Dashboard**: A React frontend connects via WebSockets to display live metrics, request logs, and errors as they happen.
* **Fully Containerized**: The entire application stack is containerized with Docker and Docker Compose for easy setup and deployment.

### Tech Stack & Architecture

Rexus is designed as a full-stack monorepo with multiple services handled by Docker Compose.

* **Backend (Proxy & API)**:
    * **Framework**: FastAPI
    * **Server**: Uvicorn
    * **Key Feature**: Asynchronous background worker for non-blocking database logging.

* **Database & Cache**:
    * **Database**: PostgreSQL (for persistent storage of API keys and logs).
    * **In-Memory Store**: Redis (used for caching, rate limiting, and as a log buffer).

* **Frontend (Dashboard)**:
    * **Framework**: React 19 (with Vite)
    * **Real-time**: Native WebSocket API for live data streaming.
    * **Charts**: Recharts

* **DevOps**:
    * **Containerization**: Docker & Docker Compose
    * **Database Migrations**: Alembic

### Getting Started

To get a local copy up and running, follow these simple steps.

#### Prerequisites

* Docker and Docker Compose must be installed on your machine.

#### Installation & Setup

1.  **Clone the repository**
    ```sh
    git clone https://github.com/BhaveshKukreja29/rexus
    cd rexus
    ```

2.  **Create an environment file**
    Create a `.env` file in the root directory. This will hold all the environment variables for the Docker containers. You can copy the example below.

    ```env
    # .env

    POSTGRES_DB=rexus_db
    POSTGRES_USER=admin
    POSTGRES_PASSWORD=your_secure_password
    ```

3.  **Build and Run with Docker Compose**
    From the root directory, run the following command. This will build the images and start all the services (`proxy`, `db`, `redis`, `mock_server`).

    ```sh
    docker compose up --build
    ```

4.  **Access the Application**
    * The **Rexus Gateway** is accessible at `http://localhost:8000`.
    * The **React Frontend** will be running at `http://localhost:5173`.
    * The **Mock API Server** for testing is at `http://localhost:8001`.

### Running Tests

The project includes several test scripts to validate core functionality. To run them, execute the following commands from the root directory in separate terminals while the Docker containers are running.

```sh
# Test Authentication and API Key Generation
python3 -m tests.test_auth

# Test Caching Logic (Miss, Hit, Bypass)
python3 -m tests.test_cache

# Test Rate Limiting and Window Reset
python3 -m tests.test_load

# Test Log Generation
python3 -m tests.test_logs
```

### Acknowledgements 🙏

This project stands on the shoulders of giants in the open-source community. A special thank you to the developers and maintainers of:

* **FastAPI**: For the incredible web framework that powers Rexus.

* **React**: For providing the foundational library for the interactive and real-time dashboard.

* **Redis**: For the versatile and fast in-memory data store.

* **PostgreSQL**: For the robust and reliable relational database.

* **Docker**: For making containerization and deployment simple and repeatable.

* And many others, including Alembic, httpx, and Uvicorn.

### License

This project is distributed under the MIT License. See LICENSE for more information.