from pydantic import BaseModel
from typing import Optional, Dict, List, Any

class User(BaseModel):
    id: Optional[str] = None
    username: str
    groups: List[str] = []
    customAttributes: Dict[str, Any] = {}
    error: Optional[str] = None