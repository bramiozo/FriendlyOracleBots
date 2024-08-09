% first get the credentials from your cloud console
gcloud init
gcloud config set project [PROJECT_ID]
gcloud builds submit --tag gcr.io/[PROJECT-ID]/[IMAGE-NAME]
gcloud run deploy [SERVICE-NAME] --image gcr.io/[PROJECT-ID]/[IMAGE-NAME] --platform managed
gcloud run services update [SERVICE-NAME] --update-env-vars KEY=VALUE,KEY2=VALUE2

# Security
https://github.com/b0g3r/fastapi-security-telegram-webhook/blob/master/README.md

https://github.com/eternnoir/pyTelegramBotAPI


Notes:
We run 
```
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
```

instead of 

```
gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT main:app
```

Due to [this](https://stackoverflow.com/questions/70272414/lots-of-uncaught-signal-6-errors-in-cloud-run) issue.