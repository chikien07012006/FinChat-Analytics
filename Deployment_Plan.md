# AWS Deployment Plan for Product

## 1. Goal

Deploy the product as a scalable web application on AWS with a containerized backend, managed SQL database, file storage, and clean deployment flow.

## 2. Core AWS Services

| Service | Role in the Product |
|---|---|
| **ECS** | Runs the backend application as Docker containers. |
| **ECR** | Stores Docker images before ECS deploys them. |
| **RDS** | Hosts the SQL database, preferably PostgreSQL or MySQL. |
| **S3** | Stores uploaded files, static assets, logs, exports, or backups. |
| **EC2** | Optional raw server if custom server control is needed. Otherwise, use ECS Fargate. |
| **CloudFront** | CDN for serving frontend/static files quickly. |
| **Route 53** | Domain and DNS management. |
| **Secrets Manager / SSM Parameter Store** | Stores environment variables, database passwords, API keys, and other secrets. |
| **CloudWatch** | Stores logs and metrics from ECS containers and other AWS services. |

## 3. Recommended Architecture

```text
User
→ CloudFront / Domain
→ Frontend hosted on S3, Vercel, or another frontend host
→ Backend API running on ECS Fargate
→ SQL database on RDS
→ File uploads stored in S3
→ Docker images stored in ECR
```

## 4. Backend Deployment Flow

```text
Write backend code
→ Prepare Dockerfile and related Docker config
→ Build Docker image locally or in CI/CD
→ Push Docker image to ECR
→ ECS pulls image from ECR
→ ECS runs the backend container
→ Backend connects to RDS and S3
→ Logs are sent to CloudWatch
```

## 5. Docker Preparation Plan

The backend should be prepared as a Dockerized application so it can run consistently across local development, testing, and AWS ECS.

Recommended backend repository structure:

```text
backend/
├── src/
├── package.json / pyproject.toml / requirements.txt
├── Dockerfile
├── .dockerignore
├── docker-compose.yml              # local development only
├── .env.example                    # example environment variables, no real secrets
└── README.md
```

For a full-stack monorepo, a common structure is:

```text
product-root/
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── src/
├── frontend/
├── docker-compose.yml              # local development only
└── README.md
```

## 6. Required Docker-Related Files

### `Dockerfile`

The `Dockerfile` defines how to package the backend into a Docker image.

It should usually:

```text
Start from a lightweight base image
Install dependencies
Copy application code
Build the application if needed
Expose the backend port
Start the production server
```

Example for a Node.js backend:

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

Example for a Python FastAPI backend:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.dockerignore`

The `.dockerignore` file prevents unnecessary files from being copied into the Docker image.

Example:

```text
node_modules
.git
.env
.env.*
__pycache__
.pytest_cache
.DS_Store
coverage
dist
build
*.log
```

Important: real `.env` files should not be copied into the Docker image.

### `docker-compose.yml`

Use `docker-compose.yml` for local development, not production AWS deployment.

It can run the backend together with a local database:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "3000:3000"
    env_file:
      - ./backend/.env
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: password
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

In AWS production, the database should be RDS, not the local `db` container.

### `.env.example`

This file documents required environment variables without exposing real secrets.

Example:

```text
NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://USER:PASSWORD@RDS_ENDPOINT:5432/DB_NAME
S3_BUCKET_NAME=your-product-bucket
AWS_REGION=ap-southeast-1
JWT_SECRET=replace-me
```

Real production values should be stored in AWS Secrets Manager or SSM Parameter Store.

## 7. ECR Image Preparation

After the backend has a working `Dockerfile`, create an ECR repository for the backend image.

Typical image flow:

```text
Backend source code
→ Docker build
→ Docker image tag
→ Push to ECR
→ ECS task definition references the ECR image URI
```

Example commands:

```bash
# Build image
docker build -t product-backend ./backend

# Tag image for ECR
docker tag product-backend:latest <aws-account-id>.dkr.ecr.<region>.amazonaws.com/product-backend:latest

# Push image to ECR
docker push <aws-account-id>.dkr.ecr.<region>.amazonaws.com/product-backend:latest
```

In real deployment, these commands should usually be handled by a CI/CD pipeline such as GitHub Actions.

## 8. ECS Configuration Plan

ECS uses a **task definition** to know how to run the Docker image.

The ECS task definition should include:

```text
ECR image URI
Container port
CPU and memory limits
Environment variables
Secrets from Secrets Manager or SSM
CloudWatch log configuration
IAM task role permissions
```

Example container setup:

```text
Container name: product-backend
Image: <aws-account-id>.dkr.ecr.<region>.amazonaws.com/product-backend:latest
Port: 3000
Runtime: ECS Fargate
Logs: CloudWatch
```

The ECS service keeps the backend running and can restart containers if they crash.

## 9. Database Plan

Use **RDS** for the main SQL database.

Recommended option:

```text
RDS PostgreSQL
```

Use RDS because it provides managed backups, monitoring, security updates, scaling options, and easier recovery compared to manually running SQL on EC2.

The backend should connect to RDS through an environment variable such as:

```text
DATABASE_URL=postgresql://USER:PASSWORD@RDS_ENDPOINT:5432/DB_NAME
```

Do not hardcode the database URL in source code.

## 10. File Storage Plan

Use **S3** for:

```text
User uploads
Images/videos
CSV exports
Generated reports
Backups
Static frontend assets
```

Do not store large user files directly inside the SQL database.

The backend should upload files to S3 using AWS SDK and store only the file metadata or S3 object key in RDS.

Example:

```text
RDS stores: user_id, file_name, s3_key, created_at
S3 stores: the actual file
```

## 11. Compute Plan

Preferred option:

```text
ECS Fargate
```

Reason: it runs containers without requiring direct EC2 server management.

Use EC2 only if the product needs:

```text
Full server control
Custom networking setup
Long-running special workloads
Lower-level infrastructure customization
```

## 12. Environment Variables and Secrets

Store sensitive values such as database passwords, API keys, and JWT secrets using:

```text
AWS Secrets Manager
or
AWS Systems Manager Parameter Store
```

Do not hardcode secrets in code, Dockerfiles, Docker images, or GitHub repositories.

Recommended split:

```text
Non-sensitive config → ECS environment variables
Sensitive config → Secrets Manager / SSM Parameter Store
```

## 13. Basic Production Setup

Minimum production setup:

```text
ECS Fargate: backend API
ECR: Docker image registry
RDS PostgreSQL: SQL database
S3: file storage
CloudFront: CDN
Route 53: domain
Secrets Manager: environment secrets
CloudWatch: logs and monitoring
```

## 14. Local Development vs AWS Production

| Area | Local Development | AWS Production |
|---|---|---|
| Backend runtime | Docker / Docker Compose | ECS Fargate |
| Image storage | Local Docker image | ECR |
| SQL database | Local Postgres container | RDS PostgreSQL |
| File storage | Local folder or test S3 bucket | S3 production bucket |
| Secrets | Local `.env` file | Secrets Manager / SSM |
| Logs | Terminal logs | CloudWatch |

## 15. Simple Summary

```text
Dockerfile packages the backend app.
.dockerignore keeps the image clean and avoids copying secrets.
docker-compose.yml is for local development.
ECR stores the built Docker image.
ECS pulls the image from ECR and runs it.
RDS hosts the SQL database.
S3 stores files and static assets.
CloudFront speeds up delivery.
Route 53 connects the domain.
CloudWatch tracks logs and errors.
Secrets Manager stores sensitive production values.
```
