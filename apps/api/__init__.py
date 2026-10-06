# The FastAPI app lives in apps.api.main (``uvicorn apps.api.main:app``). It is deliberately
# not imported here: workers import apps.api.config, and loading the app would pull in the
# routers, which import the workers again (circular import).
