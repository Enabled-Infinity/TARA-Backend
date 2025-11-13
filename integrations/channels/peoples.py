from pydantic import BaseModel, EmailStr
from datetime import datetime
from toon import encode, decode

class People(BaseModel):
    name: str 
    email: EmailStr
    phone_number: str| None = '-'
    created_at: datetime = datetime.now()

def people_data():
    with open("peoples.txt", "r") as file:
        data = file.read()
        return data

def add_people(name: str, email: EmailStr, phone_number: str| None = None):
    with open("peoples.txt", "a") as file:
        file.write(f"{name},{email},{phone_number}\n")
    return People(name=name, email=email, phone_number=phone_number)