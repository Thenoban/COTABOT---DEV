# Quick helper script to add POST endpoint for events
import sys

# Read the file
with open('api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with @app.route('/api/events', methods=['GET'])
target_line = -1
for i, line in enumerate(lines):
    if "@app.route('/api/events', methods=['GET'])" in line:
        target_line = i
        break

if target_line == -1:
    print("Could not find target line")
    sys.exit(1)

# Replace methods=['GET'] with methods=['GET', 'POST']
lines[target_line] = lines[target_line].replace("methods=['GET']", "methods=['GET', 'POST']")

# Find the next line after @require_api_key and function definition
func_start = target_line + 2  # Skip decorator and function def

# Insert POST handler after function def
post_handler = '''    """Handle events - GET to list, POST to create"""
    if request.method == 'POST':
        # CREATE EVENT
        try:
            data = request.get_json()
            
            # Validate
            title = data.get('title', '').strip()
            if not title:
                return jsonify({'success': False, 'error': 'Title required'}), 400
            
            timestamp_str = data.get('timestamp')
            if not timestamp_str:
                return jsonify({'success': False, 'error': 'Timestamp required'}), 400
            
            channel_id_str = data.get('channel_id', '').strip()
            if not channel_id_str:
                return jsonify({'success': False, 'error': 'Channel ID required'}), 400
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                channel_id = int(channel_id_str)
            except ValueError as e:
                return jsonify({'success': False, 'error': f'Invalid format: {str(e)}'}), 400
            
            description = data.get('description', '').strip()
            mention_everyone = data.get('mention_everyone', False)
            guild_id = int(request.args.get('guild_id', 1234567890))
            
            # Create event in database
            event_id = run_async(get_db().create_event(
                guild_id=guild_id,
                title=title,
                description=description,
                timestamp=timestamp,
                channel_id=channel_id,
                creator_id=0  # Web admin user
            ))
            
            logger.info(f"Event created via web admin: {title} (ID: {event_id})")
            
            return jsonify({
                'success': True,
                'message': 'Event created successfully',
                'event_id': event_id
            })
            
        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET EVENTS
'''

# Insert at func_start + 1 (after docstring line)
lines.insert(func_start + 1, post_handler)

# Write back
with open('api.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Successfully added POST handler to /api/events")
