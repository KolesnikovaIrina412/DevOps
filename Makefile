.PHONY: help deploy backup restore

help:
	@echo "Available commands:"
	@echo ""
	@echo "app-server (application):"
	@echo "  make deploy    - deploy the application on the server"
	@echo ""
	@echo "db-server (database):"
	@echo "  make backup    - create a database backup"
	@echo "  make restore   - restore the database from a backup"
	@echo ""
	@echo "Common:"
	@echo "  make help      - this help"

deploy:
	@bash scripts/deploy.sh

backup:
	@bash scripts/backup.sh

restore:
	@bash scripts/restore.sh