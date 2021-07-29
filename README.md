# Applifting entry task - Offers microservice

## How to run

### Using docker-compose
Following snippet will build Docker image and launch it using docker-compose.
Result will be at 127.0.0.1:8000.

```
git clone https://github.com/tomascapek/AppliftingEntryTask.git
cd AppliftingEntryTask
sudo docker build . -t applifting
sudo docker-compose up
```

If you need to change API url, add environment to docker-compose.yml to both containers and in
both of them, set APPLIFTING_API_URL to your liking.

### Manually

I am using uvicorn, so create Python virtual environment (I am using pipenv) and launch it like
this from `app` directory:

```python -m uvicorn api:api```

For updating the prices, launch `app/updater.py`. 

Both ways utilize environment variable named APPLIFTING_API_URL to get the url of your API. 
