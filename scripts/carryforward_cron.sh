#!/bin/bash

# Carryforward Leave Management Cron Script
# This script provides cron job commands for automated leave management

# Configuration
PROJECT_DIR="/path/to/your/django/project"  # Change this to your actual project path
PYTHON_PATH="/path/to/your/venv/bin/python"  # Change this to your Python path
MANAGE_PY="$PROJECT_DIR/manage.py"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date '+%Y-%m-%d_%H-%M-%S')

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_DIR/carryforward.log"
}

# Function to grant carryforward leaves (December 31st)
grant_carryforward() {
    log_message "Starting carryforward grant process..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # Run the management command
    $PYTHON_PATH "$MANAGE_PY" process_carryforward_leaves --action=grant 2>&1 | tee -a "$LOG_DIR/carryforward_grant_$DATE.log"
    
    if [ $? -eq 0 ]; then
        log_message "Carryforward grant completed successfully"
    else
        log_message "ERROR: Carryforward grant failed"
        exit 1
    fi
}

# Function to cleanup carryforward leaves (March 31st)
cleanup_carryforward() {
    log_message "Starting carryforward cleanup process..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # Run the management command
    $PYTHON_PATH "$MANAGE_PY" process_carryforward_leaves --action=cleanup 2>&1 | tee -a "$LOG_DIR/carryforward_cleanup_$DATE.log"
    
    if [ $? -eq 0 ]; then
        log_message "Carryforward cleanup completed successfully"
    else
        log_message "ERROR: Carryforward cleanup failed"
        exit 1
    fi
}

# Function to test the system
test_carryforward() {
    log_message "Starting carryforward system test..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # Run the management command in test mode
    $PYTHON_PATH "$MANAGE_PY" process_carryforward_leaves --action=test --dry-run 2>&1 | tee -a "$LOG_DIR/carryforward_test_$DATE.log"
    
    if [ $? -eq 0 ]; then
        log_message "Carryforward system test completed successfully"
    else
        log_message "ERROR: Carryforward system test failed"
        exit 1
    fi
}

# Function to send health check email
health_check() {
    log_message "Running health check..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # You can add additional health checks here
    $PYTHON_PATH "$MANAGE_PY" check --deploy 2>&1 | tee -a "$LOG_DIR/health_check_$DATE.log"
    
    if [ $? -eq 0 ]; then
        log_message "Health check completed successfully"
    else
        log_message "WARNING: Health check found issues"
    fi
}

# Main script logic
case "$1" in
    grant)
        grant_carryforward
        ;;
    cleanup)
        cleanup_carryforward
        ;;
    test)
        test_carryforward
        ;;
    health)
        health_check
        ;;
    *)
        echo "Usage: $0 {grant|cleanup|test|health}"
        echo ""
        echo "Commands:"
        echo "  grant   - Grant carryforward leaves (run on Dec 31st)"
        echo "  cleanup - Cleanup carryforward leaves (run on Mar 31st)"
        echo "  test    - Test the carryforward system"
        echo "  health  - Run health check"
        echo ""
        echo "Example crontab entries:"
        echo "# Grant carryforward leaves on December 31st at midnight"
        echo "0 0 31 12 * $0 grant"
        echo ""
        echo "# Cleanup carryforward leaves on March 31st at midnight"
        echo "0 0 31 3 * $0 cleanup"
        echo ""
        echo "# Daily health check at 2 AM"
        echo "0 2 * * * $0 health"
        exit 1
        ;;
esac
