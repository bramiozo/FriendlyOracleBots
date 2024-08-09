import subprocess
import os
from os.path import join, dirname
import dotenv

dotenv_path = join(dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)


def get_service_url(service_name, region):
    command = [
        "gcloud",
        "run",
        "services",
        "describe",
        service_name,
        "--region",
        region,
        "--platform",
        "managed",
        "--format=value(status.url)"
    ]
    completed_process = subprocess.run(command, text=True, capture_output=True)

    if completed_process.returncode != 0:
        raise Exception(
            f"Command failed with error: {completed_process.stderr}")

    return completed_process.stdout.strip()


PROJECT_ID = os.environ.get('PROJECT_ID')
IMAGE_NAME = os.environ.get('IMAGE_NAME')
SERVICE_NAME = os.environ.get('SERVICE_NAME')
REGION = os.environ.get('REGION')

BOT_KEY = os.environ.get('BOT_KEY')
BOT_NAME = os.environ.get('BOT_NAME')
OPENAI_KEY = os.environ.get('OPENAI_KEY')
OPENAI_ORG_KEY = os.environ.get('OPENAI_ORG_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL')

google_set_project_string = f"gcloud config set project {PROJECT_ID}"
google_set_project_region = f"gcloud config set run/region {REGION}"

google_submit_string = f"gcloud builds submit --tag gcr.io/{PROJECT_ID}/{IMAGE_NAME}"
google_run_deploy_string = f"gcloud run deploy {SERVICE_NAME} --image gcr.io/{PROJECT_ID}/{IMAGE_NAME} --platform managed --region {REGION} --allow-unauthenticated"


if __name__ == "__main__":
    print("Set project")
    os.system(google_set_project_string)

    print("Set region")
    os.system(google_set_project_region)

    print("Builds docker image")
    os.system(google_submit_string)

    print("Deploys docker image")
    os.system(google_run_deploy_string)

    # extract URL
    url = get_service_url(SERVICE_NAME, REGION)+"/"+BOT_KEY
    print(f"The service URL is: {url}")

    print(f"Setting webhook for BOT {BOT_KEY} to {url}")
    completed_process = subprocess.run(
        ["curl", "-F", f"url={url}", f"https://api.telegram.org/bot{BOT_KEY}/setWebhook"], text=True, capture_output=True)

    if completed_process.returncode != 0:
        raise Exception(
            f"Setting webhook command failed with error: {completed_process.stderr}")

    print(completed_process.stdout)

    google_run_update_string = f"gcloud run services update {SERVICE_NAME} --update-env-vars BOT_KEY={BOT_KEY},BOT_NAME={BOT_NAME},OPENAI_KEY={OPENAI_KEY},OPENAI_ORG_KEY={OPENAI_ORG_KEY},OPENAI_MODEL={OPENAI_MODEL},CLOUD_URL={url} --region {REGION}"

    print("Updates docker image with env vars")
    os.system(google_run_update_string)

    print("Done")
