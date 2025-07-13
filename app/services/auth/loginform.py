# services/auth/loginform.py
from fastapi import Request, Form
from typing import List, Optional
import re

class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.msg: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")

    async def is_valid(self):
        if not self.username or not re.match(r"[^@]+@[^@]+\.[^@]+", self.username):
            self.errors.append("Valid email is required")
        if not self.password or len(self.password) < 3:
            self.errors.append("Password must be > 3 chars")
        return not self.errors

class RegisterForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.username: Optional[str] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.msg: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.username = form.get("username")
        self.email = form.get("email")
        self.password = form.get("password")

    async def is_valid(self):
        if not self.username or len(self.username) < 3:
            self.errors.append("Username must be > 3 chars")
        if not self.email or not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
            self.errors.append("Valid email is required")
        if not self.password or len(self.password) < 3:
            self.errors.append("Password must be > 3 chars")
        return not self.errors 