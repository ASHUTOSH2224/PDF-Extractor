```
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant

docker run -p 6379:6379 redis
```

```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 211125439175.dkr.ecr.us-east-1.amazonaws.com
docker compose -f docker-compose.yml build backend
docker tag 590b2ea41ca0 211125439175.dkr.ecr.us-east-1.amazonaws.com/financial-extractor:latest
docker push 211125439175.dkr.ecr.us-east-1.amazonaws.com/financial-extractor:latest
```

```
gunicorn main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000
```