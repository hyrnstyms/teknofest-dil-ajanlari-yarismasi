import sys
from backend.app.agents.chat_agent import handle_draft_edit

message = "Taslağın konusuna 'ek bilgi' ekle"
current_draft = {
    'draft_type': 'cevap_yazisi',
    'draft': {'subject': 'Ornek Konu', 'body': 'Ornek Metin'}
}
result = handle_draft_edit(message, current_draft, {})
print(result)
