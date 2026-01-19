# Add bot queue methods to adapter.py
import re

with open('adapter.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if methods already exist
if 'queue_bot_action' in content:
    print("Methods already exist")
else:
    # Add methods before the closing of the class
    bot_methods = '''
    # ============================================
    # WEB-BOT ACTION QUEUE OPERATIONS
    # ============================================
    
    async def queue_bot_action(self, action_type: str, data: dict):
        """Queue an action for the bot to process"""
        from .models import WebBotAction
        import json
        
        def _queue():
            with self.session_scope() as session:
                action = WebBotAction(
                    action_type=action_type,
                    data=json.dumps(data)
                )
                session.add(action)
                session.commit()
                return action.id
        
        return await asyncio.to_thread(_queue)
    
    async def get_pending_web_actions(self, limit: int = 50):
        """Get pending actions for bot to process"""
        from .models import WebBotAction
        
        def _query():
            with self.session_scope() as session:
                actions = session.query(WebBotAction).filter(
                    WebBotAction.status == 'pending'
                ).order_by(
                    WebBotAction.created_at.asc()
                ).limit(limit).all()
                session.expunge_all()
                return actions
        
        return await asyncio.to_thread(_query)
    
    async def mark_action_processed(self, action_id: int):
        """Mark an action as successfully processed"""
        from .models import WebBotAction
        
        def _update():
            with self.session_scope() as session:
                action = session.query(WebBotAction).filter_by(id=action_id).first()
                if action:
                    action.status = 'processed'
                    action.processed_at = datetime.utcnow()
                    session.commit()
        
        return await asyncio.to_thread(_update)
    
    async def mark_action_failed(self, action_id: int, error_message: str):
        """Mark an action as failed"""
        from .models import WebBotAction
        
        def _update():
            with self.session_scope() as session:
                action = session.query(WebBotAction).filter_by(id=action_id).first()
                if action:
                    action.status = 'failed'
                    action.error_message = error_message
                    action.retry_count += 1
                    action.processed_at = datetime.utcnow()
                    session.commit()
        
        return await asyncio.to_thread(_update)
'''
    
    # Find the end of get_recent_activities method
    # Insert after it
    pattern = r'(async def get_recent_activities.*?return await asyncio\.to_thread\(_query\))'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + bot_methods + content[insert_pos:]
        
        with open('adapter.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Bot queue methods added successfully")
    else:
        print("Could not find insertion point")
