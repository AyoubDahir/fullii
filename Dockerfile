# Use official Frappe/ERPNext image as base
FROM frappe/erpnext:v14

USER root

# Copy custom apps from repository
COPY --chown=frappe:frappe healthcare /home/frappe/frappe-bench/apps/healthcare
COPY --chown=frappe:frappe his /home/frappe/frappe-bench/apps/his
COPY --chown=frappe:frappe hrms /home/frappe/frappe-bench/apps/hrms
COPY --chown=frappe:frappe insights /home/frappe/frappe-bench/apps/insights
COPY --chown=frappe:frappe rasiin_design /home/frappe/frappe-bench/apps/rasiin_design
COPY --chown=frappe:frappe rasiin_hr /home/frappe/frappe-bench/apps/rasiin_hr
COPY --chown=frappe:frappe frappe_whatsapp /home/frappe/frappe-bench/apps/frappe_whatsapp

USER frappe

WORKDIR /home/frappe/frappe-bench

# Install Python dependencies for custom apps
RUN for app in healthcare his hrms insights rasiin_design rasiin_hr frappe_whatsapp; do \
    if [ -f "apps/$app/requirements.txt" ]; then \
    /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir -r "apps/$app/requirements.txt"; \
    fi; \
    done

# Note: Apps will be installed and assets built when site is created
# Use: bench new-site <site-name> --install-app healthcare --install-app his ...
# Or configure via Helm values for automatic installation

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/ping || exit 1
