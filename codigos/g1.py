from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simulando um banco de dados
fake_users_db = {
    "user@example.com": {
        "email": "user@example.com",
        "hashed_password": pwd_context.hash("password123"),
    }
}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/login")
def login(data: LoginRequest):
    user = fake_users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário ou senha inválidos")
    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Usuário ou senha inválidos")
    return {"message": "Login realizado com sucesso"}