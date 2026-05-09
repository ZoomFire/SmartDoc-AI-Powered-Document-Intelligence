from passlib.context import CryptContext
from models import User
from database import SessionLocal

pwd = CryptContext(schemes=["bcrypt"])

def hash_password(p):
    return pwd.hash(p)

def verify(p, h):
    try:
        return pwd.verify(p, h)
    except:
        return False

def register_user(username, password):
    db = SessionLocal()
    user = User(username=username, password=hash_password(password))
    db.add(user)
    db.commit()

def login_user(username, password):
    db = SessionLocal()
    user = db.query(User).filter(User.username==username).first()
    if user and verify(password, user.password):
        return True
    return False