#!/bin/bash

# SEED Services Management Script

case "$1" in
    start)
        echo "Starting Redis and RabbitMQ services..."
        docker compose up -d
        ;;
    stop)
        echo "Stopping services..."
        docker compose down
        ;;
    restart)
        echo "Restarting services..."
        docker compose restart
        ;;
    status)
        echo "Service status:"
        docker ps --filter "name=seed-"
        ;;
    logs)
        if [ -z "$2" ]; then
            docker compose logs -f
        else
            docker compose logs -f "$2"
        fi
        ;;
    redis-cli)
        docker exec -it seed-redis redis-cli
        ;;
    rabbit-mgmt)
        echo "RabbitMQ Management UI: http://localhost:15672"
        echo "Username: seed"
        echo "Password: seed_password"
        ;;
    health)
        echo "Checking Redis..."
        docker exec seed-redis redis-cli ping
        echo "Checking RabbitMQ..."
        docker exec seed-rabbitmq rabbitmq-diagnostics -q ping
        ;;
    clean)
        echo "Removing stopped containers and unused volumes..."
        docker compose down -v
        docker system prune -f
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]|redis-cli|rabbit-mgmt|health|clean}"
        echo ""
        echo "Commands:"
        echo "  start       - Start all services"
        echo "  stop        - Stop all services" 
        echo "  restart     - Restart all services"
        echo "  status      - Show container status"
        echo "  logs        - Show logs (optionally for specific service)"
        echo "  redis-cli   - Connect to Redis CLI"
        echo "  rabbit-mgmt - Show RabbitMQ management info"
        echo "  health      - Check service health"
        echo "  clean       - Clean up containers and volumes"
        exit 1
        ;;
esac