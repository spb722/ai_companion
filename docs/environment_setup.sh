#!/bin/bash

# AI Companion Development Environment Setup Script
# This script sets up the complete development environment for testing

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_NAME="ai_companion"
DB_USER="aiuser"
DB_PASSWORD="aipassword"
DB_ROOT_PASSWORD="rootpassword"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_error "$1 is not installed"
        return 1
    fi
}

install_python_deps() {
    log_info "Installing Python dependencies..."
    cd "$PROJECT_ROOT"
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi
}

setup_database() {
    log_info "Setting up MySQL database..."
    
    # Check if MySQL container is running
    if docker ps | grep -q mysql-ai-companion; then
        log_info "MySQL container already running"
    else
        log_info "Starting MySQL container..."
        docker run -d \
            --name mysql-ai-companion \
            -e MYSQL_ROOT_PASSWORD="$DB_ROOT_PASSWORD" \
            -e MYSQL_DATABASE="$DB_NAME" \
            -e MYSQL_USER="$DB_USER" \
            -e MYSQL_PASSWORD="$DB_PASSWORD" \
            -p 3306:3306 \
            mysql:8.0
        
        log_info "Waiting for MySQL to start..."
        sleep 30
    fi
    
    # Test connection
    if docker exec mysql-ai-companion mysql -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" &> /dev/null; then
        log_success "MySQL database is ready"
    else
        log_error "Failed to connect to MySQL"
        exit 1
    fi
}

setup_redis() {
    log_info "Setting up Redis..."
    
    # Check if Redis container is running
    if docker ps | grep -q redis-ai-companion; then
        log_info "Redis container already running"
    else
        log_info "Starting Redis container..."
        docker run -d \
            --name redis-ai-companion \
            -p 6379:6379 \
            redis:7-alpine
        
        sleep 5
    fi
    
    # Test connection
    if docker exec redis-ai-companion redis-cli ping | grep -q PONG; then
        log_success "Redis is ready"
    else
        log_error "Failed to connect to Redis"
        exit 1
    fi
}

setup_environment_file() {
    log_info "Setting up environment file..."
    
    ENV_FILE="$PROJECT_ROOT/.env"
    
    if [ -f "$ENV_FILE" ]; then
        log_warning ".env file already exists, backing up..."
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%s)"
    fi
    
    cat > "$ENV_FILE" << EOF
# Database Configuration
DATABASE_URL=mysql+aiomysql://$DB_USER:$DB_PASSWORD@localhost:3306/$DB_NAME

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Supabase Configuration (REQUIRED - Update with your values)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# LLM Provider Configuration (At least one required)
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Development Configuration
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# Optional LLM Providers
GOOGLE_API_KEY=your_google_api_key_here
XAI_API_KEY=your_xai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
EOF

    log_success "Environment file created at $ENV_FILE"
    log_warning "IMPORTANT: Update the API keys in $ENV_FILE before running the application"
}

run_database_migrations() {
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT"
    
    # Wait a bit more for MySQL to be fully ready
    sleep 10
    
    # Run Alembic migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        log_success "Database migrations completed"
    else
        log_error "Alembic not found. Install with: pip install alembic"
        exit 1
    fi
}

seed_database() {
    log_info "Seeding database with initial data..."
    cd "$PROJECT_ROOT"
    
    # Run character seeding
    if [ -f "app/db/seed_characters.py" ]; then
        python -m app.db.seed_characters
        log_success "Database seeded with characters"
    else
        log_warning "Character seed script not found"
    fi
}

test_application() {
    log_info "Testing application startup..."
    cd "$PROJECT_ROOT"
    
    # Start application in background
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
    APP_PID=$!
    
    # Wait for startup
    sleep 10
    
    # Test health endpoint
    if curl -s http://localhost:8000/health > /dev/null; then
        log_success "Application is running and responding"
        
        # Test health check details
        HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
        echo "Health check response:"
        echo "$HEALTH_RESPONSE" | python -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        log_error "Application health check failed"
    fi
    
    # Stop application
    kill $APP_PID 2>/dev/null || true
    sleep 2
}

create_test_aliases() {
    log_info "Creating test script aliases..."
    
    cat > "$PROJECT_ROOT/run_tests.sh" << 'EOF'
#!/bin/bash
# Test runner script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== AI Companion Test Suite ==="
echo ""

echo "1. Running API Tests..."
bash "$SCRIPT_DIR/docs/test_chat_api.sh"

echo ""
echo "2. Running SSE Tests..."
python "$SCRIPT_DIR/docs/test_sse_streaming.py"

echo ""
echo "=== All Tests Completed ==="
EOF

    chmod +x "$PROJECT_ROOT/run_tests.sh"
    chmod +x "$PROJECT_ROOT/docs/test_chat_api.sh"
    chmod +x "$PROJECT_ROOT/docs/test_sse_streaming.py"
    
    log_success "Test scripts made executable"
    log_info "Run all tests with: ./run_tests.sh"
}

display_summary() {
    log_success "Environment setup completed!"
    echo ""
    echo "=== NEXT STEPS ==="
    echo ""
    echo "1. Update API keys in .env file:"
    echo "   - SUPABASE_URL and SUPABASE_KEY (required)"
    echo "   - At least one LLM provider key (GROQ_API_KEY or OPENAI_API_KEY)"
    echo ""
    echo "2. Start the application:"
    echo "   cd $PROJECT_ROOT"
    echo "   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "3. Run tests:"
    echo "   ./run_tests.sh                    # Run all tests"
    echo "   ./docs/test_chat_api.sh          # API tests only"
    echo "   python ./docs/test_sse_streaming.py # SSE tests only"
    echo ""
    echo "4. Access the application:"
    echo "   - API: http://localhost:8000"
    echo "   - Health: http://localhost:8000/health"
    echo "   - Docs: http://localhost:8000/docs"
    echo ""
    echo "=== TROUBLESHOOTING ==="
    echo ""
    echo "- Check logs: docker logs mysql-ai-companion"
    echo "- Check logs: docker logs redis-ai-companion"
    echo "- Restart services: docker restart mysql-ai-companion redis-ai-companion"
    echo "- Clean setup: docker rm -f mysql-ai-companion redis-ai-companion && $0"
    echo ""
}

main() {
    log_info "AI Companion Development Environment Setup"
    log_info "Project root: $PROJECT_ROOT"
    echo ""
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    check_command "docker" || { log_error "Docker is required. Install from https://docs.docker.com/get-docker/"; exit 1; }
    check_command "python" || { log_error "Python 3.11+ is required"; exit 1; }
    check_command "pip" || { log_error "pip is required"; exit 1; }
    check_command "curl" || { log_error "curl is required"; exit 1; }
    
    # Optional but recommended
    check_command "jq" || log_warning "jq recommended for JSON formatting (install with: brew install jq)"
    
    echo ""
    
    # Setup steps
    setup_database
    setup_redis
    setup_environment_file
    install_python_deps
    run_database_migrations
    seed_database
    create_test_aliases
    test_application
    
    echo ""
    display_summary
}

# Cleanup function
cleanup() {
    if [ -n "$APP_PID" ]; then
        kill $APP_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Run main function
main "$@"