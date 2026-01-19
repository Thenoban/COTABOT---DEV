# Script to add activity log endpoint to api.py
import re

with open('api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the position before "# SERVER STATUS ENDPOINT" or "@app.route('/api/server/status'"
activity_endpoint = '''
# ============================================
# ACTIVITY LOG ENDPOINTS
# ============================================

@app.route('/api/activity/recent', methods=['GET'])
@require_api_key
def get_recent_activity():
    """Get recent admin activities"""
    try:
        limit = int(request.args.get('limit', 20))
        activities = run_async(get_db().get_recent_activities(limit))
        
        result = []
        for activity in activities:
            result.append({
                'id': activity.id,
                'action_type': activity.action_type,
                'admin_user': activity.admin_user,
                'target': activity.target,
                'details': activity.details,
                'timestamp': activity.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

'''

# Insert before server status section
if '/api/activity/recent' not in content:
    # Find "# SERVER STATUS ENDPOINT" or "@app.route('/api/server/status'"
    pattern = r"(# ============================================\r?\n# SERVER STATUS ENDPOINT\r?\n# ============================================)"
    
    if re.search(pattern, content):
        content = re.sub(pattern, activity_endpoint + r'\1', content)
        with open('api.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Activity log endpoint added to api.py")
    else:
        print("❌ Could not find insertion point")
else:
    print("ℹ️ Activity endpoint already exists")
