#!/usr/bin/env bash

set -euo pipefail

# ─── CONFIG ──────────────────────────────────────────────────────────────────
PROJECT_ID="emission-impossible-510123"
REGION="us-west1"                       # keep the same region everywhere

API_SERVICE="api-server"                # Cloud Run service name for the API

API_DIR="./api"                         # folder holding the API Dockerfile

API_PORT=8000                           # must match EXPOSE/CMD in api/Dockerfile

# The key goes to Secret Manager and is mounted at runtime, and .env is read by gcloud at deploy time.
ENV_FILE="/Users/junghoona/Class/usfca-msdsai/projects/emission-impossible/.env"
LOCAL_KEY_FILE="/Users/junghoona/emission-impossible-510123-a81afa6403a0.json"

# The code reads GCP_SERVICE_ACCOUNT_KEY as a file path and mount it
GCP_KEY_SECRET="group-hw3-gcp-key"
SECRET_MOUNT_PATH="/run/secrets/gcp_key"

# EIA CO2 collector (api/collectors/eia.py)
EIA_SCHEDULER_JOB="collect-eia"
EIA_COLLECT_PATH="/ingest/eia"  # must match the route in api/main.py

# BEA real GDP collector (api/collectors/bea.py)
BEA_SCHEDULER_JOB="collect-bea"
BEA_COLLECT_PATH="/ingest/bea"  # must match the route in api/main.py

# Cloud Scheduler job: name, schedule, and the request body.
# For more info, access Documentation: https://docs.cloud.google.com/scheduler/docs/configuring/cron-job-schedules
# cron job schedule collects every day
SCHEDULE="0 0 * * *"
SCHEDULER_TZ="America/Los_Angeles"

# How long Scheduler will wait for the API to respond
ATTEMPT_DEADLINE="320s"

# The /ingest endpoints don't read a body
MESSAGE_BODY='{}'
# ─────────────────────────────────────────────────────────────────────────────

# ─── validation ──────────────────────────────────────────────────────────────
for _var in PROJECT_ID REGION API_SERVICE API_DIR \
            API_PORT ENV_FILE LOCAL_KEY_FILE GCP_KEY_SECRET \
            SECRET_MOUNT_PATH EIA_SCHEDULER_JOB EIA_COLLECT_PATH \
            BEA_SCHEDULER_JOB BEA_COLLECT_PATH SCHEDULE ATTEMPT_DEADLINE; do
  if [ -z "${!_var}" ]; then
    echo "ERROR: $_var is empty -- fill in the CONFIG block at the top of" \
         "this script before running it." >&2
    exit 1
  fi
done
unset _var

if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
  echo "ERROR: PROJECT_ID is still the placeholder. Edit the CONFIG block." >&2
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: ENV_FILE '$ENV_FILE' does not exist." \
       "Copy .env_template to .env and fill it in." >&2
  exit 1
fi
if [ ! -f "$LOCAL_KEY_FILE" ]; then
  echo "ERROR: LOCAL_KEY_FILE '$LOCAL_KEY_FILE' does not exist." >&2
  exit 1
fi
if [ ! -f "$API_DIR/Dockerfile" ]; then
    echo "ERROR: no Dockerfile in '$API_DIR'." >&2
    exit 1
fi

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

# ─── one-time project setup ──────────────────────────────────────────────────
bootstrap() {
  gcloud config set project "$PROJECT_ID"
  gcloud config set run/region "$REGION"
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com

  log "Storing the service account key in Secret Manager as '${GCP_KEY_SECRET}'"
  if ! gcloud secrets describe "$GCP_KEY_SECRET" >/dev/null 2>&1; then
    gcloud secrets create "$GCP_KEY_SECRET" --replication-policy=automatic
  fi
  gcloud secrets versions add "$GCP_KEY_SECRET" --data-file="$LOCAL_KEY_FILE"

  log "Letting the Cloud Run runtime service account read that secret"
  local project_number
  project_number=$(gcloud projects describe "$PROJECT_ID" \
    --format="value(projectNumber)")
  gcloud secrets add-iam-policy-binding "$GCP_KEY_SECRET" \
    --member="serviceAccount:${project_number}-compute@developer.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
}

# ─── API service ─────────────────────────────────────────────────────────────
deploy_api() {
  log "Deploying ${API_SERVICE} from ${API_DIR} (Cloud Build builds the image)"
  gcloud run deploy "$API_SERVICE" \
    --source "$API_DIR" \
    --region "$REGION" \
    --port="$API_PORT" \
    --allow-unauthenticated \
    --timeout=300 \
    --max-instances=1 \
    --env-vars-file="$ENV_FILE" \
    --set-secrets="$SECRET_MOUNT_PATH=$GCP_KEY_SECRET:latest"

  # .env points GCP_SERVICE_ACCOUNT_KEY at a path on your laptop.
  gcloud run services update "$API_SERVICE" \
    --region "$REGION" \
    --update-env-vars=GCP_SERVICE_ACCOUNT_KEY="$SECRET_MOUNT_PATH"
}

api_url() {
  local url
  url=$(gcloud run services describe "$API_SERVICE" \
    --region "$REGION" --format="value(urls[0])")
  if [ -z "$url" ]; then
    url=$(gcloud run services describe "$API_SERVICE" \
      --region "$REGION" --format="value(status.url)")
  fi
  if [ -z "$url" ]; then
    echo "ERROR: could not resolve the URL for Cloud Run service" \
         "'$API_SERVICE' in $REGION. Deploy it first." >&2
    exit 1
  fi
  echo "$url"
}

# ─── Cloud Scheduler ─────────────────────────────────────────────────────────
# EIA CO2 -> gs://<bucket>/raw/eia_co2/<YYYY-MM>/
deploy_scheduler_eia() {
    local url; url="$(api_url)"

    # create first time, update on every run after that
    local action=create
    if gcloud scheduler jobs describe "$EIA_SCHEDULER_JOB" \
        --location="$REGION" >/dev/null 2>&1; then
        action=update
    fi

    log "Running '${action}' on scheduler job '${EIA_SCHEDULER_JOB}' -> ${EIA_COLLECT_PATH} (${SCHEDULE} ${SCHEDULER_TZ})"
    gcloud scheduler jobs "$action" http "$EIA_SCHEDULER_JOB" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --time-zone="$SCHEDULER_TZ" \
        --uri="${url}${EIA_COLLECT_PATH}" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body="$MESSAGE_BODY" \
        --attempt-deadline="$ATTEMPT_DEADLINE"

    log "Triggering '${EIA_SCHEDULER_JOB}' once so you can confirm it works"
    gcloud scheduler jobs run "$EIA_SCHEDULER_JOB" --location="$REGION"
    echo "Check the result with:"
    echo "  gcloud run services logs read ${API_SERVICE} --region=${REGION} --limit=50"
}

# BEA real GDP by state -> gs://<bucket>/raw/bea_gdp/downloaded_<YYYY-MM>/
deploy_scheduler_bea() {
    local url; url="$(api_url)"

    # create first time, update on every run after that
    local action=create
    if gcloud scheduler jobs describe "$BEA_SCHEDULER_JOB" \
        --location="$REGION" >/dev/null 2>&1; then
        action=update
    fi

    log "Running '${action}' on scheduler job '${BEA_SCHEDULER_JOB}' -> ${BEA_COLLECT_PATH} (${SCHEDULE} ${SCHEDULER_TZ})"
    gcloud scheduler jobs "$action" http "$BEA_SCHEDULER_JOB" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --time-zone="$SCHEDULER_TZ" \
        --uri="${url}${BEA_COLLECT_PATH}" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body="$MESSAGE_BODY" \
        --attempt-deadline="$ATTEMPT_DEADLINE"

    log "Triggering '${BEA_SCHEDULER_JOB}' once so you can confirm it works"
    gcloud scheduler jobs run "$BEA_SCHEDULER_JOB" --location="$REGION"
    echo "Check the result with:"
    echo "  gcloud run services logs read ${API_SERVICE} --region=${REGION} --limit=50"
}

show_urls() {
  echo "API     : $(api_url)"
  echo "Web app : $(gcloud run services describe "$WEB_SERVICE" \
    --region "$REGION" --format='value(status.url)')"
}

# ─── entry point ─────────────────────────────────────────────────────────────
case "${1:-all}" in
  all)           bootstrap; deploy_api;
                 deploy_scheduler_eia; deploy_scheduler_bea; show_urls ;;
  bootstrap)     bootstrap ;;
  api)           deploy_api ;;
  scheduler)     deploy_scheduler_eia; deploy_scheduler_bea ;;
  scheduler-eia) deploy_scheduler_eia ;;
  scheduler-bea) deploy_scheduler_bea ;;
  urls)          show_urls ;;
  *) echo "usage: $0 {all|bootstrap|api|web|scheduler|urls}" >&2; exit 1 ;;
esac

log "Done."
