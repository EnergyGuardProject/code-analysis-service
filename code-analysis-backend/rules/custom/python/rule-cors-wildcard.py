from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = ["*"]
# ruleid: custom_python_cors-wildcard-credentials
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"])
# ruleid: custom_python_cors-wildcard-credentials
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)
# ruleid: custom_python_cors-wildcard
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
# ok: custom_python_cors-wildcard
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example.org"], allow_credentials=True)
