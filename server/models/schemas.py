
from pydantic import BaseModel

class BotSendRequest(BaseModel):
    on_behalf_of: str   
    to: str             
    mode: str = "generate"   
    text: str | None = None  
    system_hint: str | None = None 
