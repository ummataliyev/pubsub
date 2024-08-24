"""
Message table
"""
import pydantic


class Message(pydantic.BaseModel):
    message: str
