"""
Cotabot Web Admin Panel - Flask REST API
"""
from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
import logging
import asyncio
from functools import wraps

# SocketIO imports (optional - install with: pip install flask-socketio)
try:
    from socketio_handler import init_socketio, broadcast_event
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    broadcast_event = lambda *args: None  # No-op if not available

# Add parent directory to path to import database modules
sys.path.append(str(Path(__file__).parent.parent))
from database.adapter import DatabaseAdapter
from database.models import Player, PlayerStats, Event, TrainingMatch

# Import config and auth with proper paths for Docker
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from auth import require_api_key, login_with_api_key

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Setup logger (before conditional blocks)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS configuration
CORS(app, supports_credentials=True, origins=config.CORS_ORIGINS)

# Initialize SocketIO if available
if SOCKETIO_AVAILABLE:
    socketio = init_socketio(app)
    logger.info("✅ Flask app initialized with SocketIO")
else:
    socketio = None
    logger.info("ℹ️ Flask app initialized without SocketIO (install flask-socketio for real-time features)")

# Database adapters cache (environment -> adapter)
_db_adapters = {}

def get_db(environment=None):
    """Get database adapter for specified environment"""
    # Get environment from session, header, or default
    if environment is None:
        environment = request.headers.get('X-Environment') or \
                     session.get('environment') or \
                     config.DEFAULT_ENVIRONMENT
    
    # Create adapter if not cached
    if environment not in _db_adapters:
        env_config = config.ENVIRONMENTS.get(environment)
        if not env_config:
            raise ValueError(f"Invalid environment: {environment}")
        _db_adapters[environment] = DatabaseAdapter(env_config['database_url'])
    
    return _db_adapters[environment]

# Setup logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Helper to run async functions in sync context
def run_async(coro):
    """Helper to run async coroutines in Flask's synchronous context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ============================================
# STATIC FILES & ROOT
# ============================================

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

# ============================================
# AUTHENTICATION
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.get_json()
    api_key = data.get('api_key', '')
    
    success, message = login_with_api_key(api_key)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'api_key': api_key
        })
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 401

# ============================================
# ENVIRONMENT MANAGEMENT
# ============================================

@app.route('/api/environment', methods=['GET'])
@require_api_key
def get_environment():
    """Get current environment"""
    current_env = session.get('environment', config.DEFAULT_ENVIRONMENT)
    env_config = config.ENVIRONMENTS.get(current_env, {})
    
    return jsonify({
        'success': True,
        'data': {
            'current': current_env,
            'name': env_config.get('name', current_env),
            'database_path': str(env_config.get('database_path', ''))
        }
    })

@app.route('/api/environment/switch', methods=['POST'])
@require_api_key
def switch_environment():
    """Switch to different environment"""
    data = request.get_json()
    new_env = data.get('environment', '').upper()
    
    if new_env not in config.ENVIRONMENTS:
        return jsonify({
            'success': False,
            'error': f'Invalid environment: {new_env}'
        }), 400
    
    # Update session
    session['environment'] = new_env
    
    return jsonify({
        'success': True,
        'message': f'Switched to {new_env} environment',
        'environment': new_env
    })

@app.route('/api/environments', methods=['GET'])
@require_api_key
def list_environments():
    """List all available environments"""
    environments = []
    for env_key, env_config in config.ENVIRONMENTS.items():
        environments.append({
            'key': env_key,
            'name': env_config['name'],
            'database_path': str(env_config['database_path'])
        })
    
    return jsonify({
        'success': True,
        'data': environments
    })

# ============================================
# DASHBOARD ENDPOINTS
# ============================================

@app.route('/api/stats/dashboard', methods=['GET'])
@require_api_key
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get total players
        all_players = run_async(get_db().get_all_players())
        total_players = len(all_players)
        
        # Get active events
        # Note: We need guild_id, using a default one
        # In production, this should come from config or request
        guild_id = 1234567890  # Placeholder
        try:
            active_events = run_async(get_db().get_active_events(guild_id))
            total_events = len(active_events)
        except:
            total_events = 0
        
        # Get recent activity (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        active_players_count = 0
        
        for player in all_players:
            try:
                activities = run_async(get_db().get_player_activity(player.id, days=7))
                if activities:
                    active_players_count += 1
            except:
                continue
        
        # Get training matches
        try:
            # Get all training matches (assuming they exist in DB)
            # For now, we'll return a placeholder
            total_training_matches = 0
        except:
            total_training_matches = 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_players': total_players,
                'active_events': total_events,
                'active_players_7d': active_players_count,
                'training_matches': total_training_matches
            }
        })
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats/activity-chart', methods=['GET'])
@require_api_key
def get_activity_chart():
    """Get activity chart data for last 30 days"""
    try:
        days = int(request.args.get('days', 30))
        
        # Get all recent activity
        activities = run_async(get_db().get_all_recent_activity(days=days))
        
        # Group by date
        activity_by_date = {}
        for row in activities:
            activity_log, player = row
            date_str = activity_log.date.strftime('%Y-%m-%d')
            if date_str not in activity_by_date:
                activity_by_date[date_str] = {
                    'date': date_str,
                    'players': 0,
                    'minutes': 0
                }
            activity_by_date[date_str]['players'] += 1
            activity_by_date[date_str]['minutes'] += activity_log.minutes
        
        # Convert to list and sort by date
        chart_data = sorted(activity_by_date.values(), key=lambda x: x['date'])
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        logger.error(f"Error getting activity chart: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# PLAYER MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/players', methods=['GET'])
@require_api_key
def get_players():
    """Get all players with pagination and search"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', config.DEFAULT_PAGE_SIZE)), config.MAX_PAGE_SIZE)
        search = request.args.get('search', '')
        
        # Get players
        if search:
            players = run_async(get_db().search_players(search))
        else:
            players = run_async(get_db().get_all_players())
        
        # Get stats for each player
        result = []
        for player in players:
            try:
                stats = run_async(get_db().get_player_stats(player.id))
                player_data = {
                    'steam_id': player.steam_id,
                    'name': player.name,
                    'discord_id': player.discord_id,
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'stats': {
                        'total_score': stats.total_score if stats else 0,
                        'total_kills': stats.total_kills if stats else 0,
                        'total_deaths': stats.total_deaths if stats else 0,
                        'total_kd_ratio': stats.total_kd_ratio if stats else 0
                    } if stats else None
                }
                result.append(player_data)
            except:
                result.append({
                    'steam_id': player.steam_id,
                    'name': player.name,
                    'discord_id': player.discord_id,
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'stats': None
                })
        
        # Pagination
        total = len(result)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_result = result[start:end]
        
        return jsonify({
            'success': True,
            'data': paginated_result,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/players/<steam_id>', methods=['GET'])
@require_api_key
def get_player(steam_id):
    """Get single player details"""
    try:
        player = db.get_player_by_steam_id(steam_id)
        if not player:
            return jsonify({
                'success': False,
                'error': 'Player not found'
            }), 404
        
        # Get stats
        stats = run_async(get_db().get_player_stats(player.id))
        
        # Get activity (last 30 days)
        activities = run_async(get_db().get_player_activity(player.id, days=30))
        activity_data = [{
            'date': a.date.isoformat(),
            'minutes': a.minutes,
            'last_seen': a.last_seen.isoformat() if a.last_seen else None
        } for a in activities]
        
        return jsonify({
            'success': True,
            'data': {
                'steam_id': player.steam_id,
                'name': player.name,
                'discord_id': player.discord_id,
                'created_at': player.created_at.isoformat() if player.created_at else None,
                'stats': {
                    'total_score': stats.total_score,
                    'total_kills': stats.total_kills,
                    'total_deaths': stats.total_deaths,
                    'total_revives': stats.total_revives,
                    'total_kd_ratio': stats.total_kd_ratio,
                    'season_score': stats.season_score,
                    'season_kills': stats.season_kills,
                    'season_deaths': stats.season_deaths,
                    'season_kd_ratio': stats.season_kd_ratio
                } if stats else None,
                'activity': activity_data
            }
        })
    except Exception as e:
        logger.error(f"Error getting player {steam_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/players', methods=['POST'])
@require_api_key
def add_player():
    """Add new player"""
    try:
        data = request.get_json()
        
        steam_id = data.get('steam_id')
        name = data.get('name')
        discord_id = data.get('discord_id')
        
        if not steam_id or not name:
            return jsonify({
                'success': False,
                'error': 'steam_id and name are required'
            }), 400
        
        # Check if player already exists
        existing = run_async(get_db().get_player_by_steam_id(steam_id))
        if existing:
            return jsonify({
                'success': False,
                'error': 'Player with this Steam ID already exists'
            }), 409
        
        # Add player
        player_id = run_async(get_db().add_player(steam_id, name, discord_id))
        
        return jsonify({
            'success': True,
            'message': 'Player added successfully',
            'player_id': player_id
        }), 201
    except Exception as e:
        logger.error(f"Error adding player: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/players/<steam_id>', methods=['PUT'])
@require_api_key
def update_player(steam_id):
    """Update player information"""
    try:
        data = request.get_json()
        
        name = data.get('name')
        discord_id = data.get('discord_id')
        
        # Check if player exists
        player = run_async(get_db().get_player_by_steam_id(steam_id))
        if not player:
            return jsonify({
                'success': False,
                'error': 'Player not found'
            }), 404
        
        # Update player
        run_async(get_db().update_player(steam_id, name=name, discord_id=discord_id))
        
        return jsonify({
            'success': True,
            'message': 'Player updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating player {steam_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/players/<steam_id>', methods=['DELETE'])
@require_api_key
def delete_player(steam_id):
    """Delete player"""
    try:
        # Check if player exists
        player = run_async(get_db().get_player_by_steam_id(steam_id))
        if not player:
            return jsonify({
                'success': False,
                'error': 'Player not found'
            }), 404
        
        # Delete player
        run_async(get_db().delete_player(steam_id))
        
        return jsonify({
            'success': True,
            'message': 'Player deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting player {steam_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# EVENT MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/events', methods=['GET', 'POST'])
@require_api_key
def get_events():
    """Handle events - GET to list, POST to create"""
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
            
            # Queue bot action for Discord announcement
            run_async(get_db().queue_bot_action(
                action_type='announce_event',
                data={
                    'event_id': event_id,
                    'title': title,
                    'description': description,
                    'channel_id': channel_id,
                    'mention_everyone': mention_everyone,
                    'timestamp': timestamp.isoformat()
                }
            ))
            
            # Log activity
            run_async(get_db().log_activity('event_create', title, f'Channel: {channel_id}'))
            
            return jsonify({
                'success': True,
                'message': 'Event created successfully',
                'event_id': event_id
            })
            
        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET EVENTS
    """Get all events"""
    try:
        guild_id = int(request.args.get('guild_id', 1234567890))  # Placeholder
        
        events = run_async(get_db().get_all_events(guild_id))
        
        result = []
        for event in events:
            event_data = {
                'id': event.id,
                'event_id': event.event_id,
                'title': event.title,
                'description': event.description,
                'timestamp': event.timestamp.isoformat(),
                'channel_id': event.channel_id,
                'creator_id': event.creator_id,
                'active': event.active,
                'created_at': event.created_at.isoformat() if event.created_at else None,
                'participants_count': len(event.participants) if event.participants else 0
            }
            result.append(event_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/events/<int:event_id>/participants', methods=['GET'])
@require_api_key
def get_event_participants_api(event_id):
    """Get detailed participant information for an event"""
    try:
        db = get_db()
        
        # Get event info
        event = run_async(db.get_event(event_id))
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        # Get all participants
        participants = db.get_event_participants(event_id)
        
        # Categorize participants (status: 'attendee', 'declined', 'tentative')
        joined = [p for p in participants if p.status == 'attendee']
        declined = [p for p in participants if p.status == 'declined']
        maybe = [p for p in participants if p.status == 'tentative']
        
        # Serialize participants
        def serialize_participant(p):
            return {
                'user_id': str(p.user_id),
                'username': p.user_mention,  # Using user_mention field
                'excuse': p.reason if p.reason else None,  # Using reason field
                'responded_at': p.joined_at.isoformat() if p.joined_at else None  # Using joined_at field
            }
        
        # Calculate stats
        total_responded = len(participants)
        
        # Build response
        return jsonify({
            'success': True,
            'event': {
                'event_id': event.event_id,
                'title': event.title,
                'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                'active': event.active
            },
            'stats': {
                'total_responded': total_responded,
                'join_count': len(joined),
                'decline_count': len(declined),
                'maybe_count': len(maybe)
            },
            'participants': {
                'joined': [serialize_participant(p) for p in joined],
                'declined': [serialize_participant(p) for p in declined],
                'maybe': [serialize_participant(p) for p in maybe]
            }
        })
    except Exception as e:
        logger.error(f"Error getting event participants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/events/active', methods=['GET'])
@require_api_key
def get_active_events():
    """Get active events only"""
    try:
        guild_id = int(request.args.get('guild_id', 1234567890))
        
        events = run_async(get_db().get_active_events(guild_id))
        
        result = []
        for event in events:
            event_data = {
                'id': event.id,
                'event_id': event.event_id,
                'title': event.title,
                'description': event.description,
                'timestamp': event.timestamp.isoformat(),
                'participants_count': len(event.participants) if event.participants else 0
            }
            result.append(event_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting active events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# REPORTS ENDPOINTS
# ============================================

@app.route('/api/reports/hall-of-fame', methods=['GET'])
@require_api_key
def get_hall_of_fame():
    """Get Hall of Fame records"""
    try:
        records = run_async(get_db().get_hall_of_fame_records())
        
        result = [{
            'record_type': r.record_type,
            'player_name': r.player_name,
            'value': r.value,
            'achieved_at': r.achieved_at.isoformat() if r.achieved_at else None
        } for r in records]
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting Hall of Fame: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

# ============================================
# SERVER STATUS ENDPOINT
# ============================================

@app.route('/api/server/status', methods=['GET'])
@require_api_key
def get_server_status():
    """Get server status from BattleMetrics API"""
    try:
        import aiohttp
        
        async def fetch_server():
            headers = {"Authorization": f"Bearer {config.BM_API_KEY}"} if config.BM_API_KEY else {}
            url = f"{config.BM_API_URL}/servers/{config.SERVER_ID}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"BattleMetrics API error: {response.status}")
                        raise Exception(f"API returned {response.status}")
                    
                    data = await response.json()
                    server = data['data']['attributes']
                    
                    return {
                        'online': server.get('status') == 'online',
                        'players': server.get('players', 0),
                        'max_players': server.get('maxPlayers', 0),
                        'map': server.get('details', {}).get('map', 'Unknown'),
                        'server_name': server.get('name', 'Cotabot Squad Server'),
                        'queue': server.get('details', {}).get('squad_publicQueue', 0)
                    }
        
        server_data = run_async(fetch_server())
        
        return jsonify({
            'success': True,
            'data': server_data
        })
        
    except Exception as e:
        logger.error(f"Server status error: {e}", exc_info=True)
        return jsonify({
            'success': True,
            'data': {
                'online': False,
                'players': 0,
                'max_players': 80,
                'map': 'Error: ' + str(e),
                'server_name': 'Cotabot Squad Server',
                'queue': 0
            }
        })

# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    logger.info("Starting Cotabot Web Admin Panel API...")
    logger.info(f"Database: {config.DATABASE_PATH}")
    logger.info(f"Server: http://{config.HOST}:{config.PORT}")
    
    if SOCKETIO_AVAILABLE and socketio:
        # Run with SocketIO
        logger.info("🚀 Starting with SocketIO support...")
        socketio.run(
            app,
            host=config.HOST,
            port=config.PORT,
            debug=True,
            allow_unsafe_werkzeug=True  # Allow for development/testing
        )
    else:
        # Run without SocketIO
        logger.info("🚀 Starting without SocketIO...")
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=True
        )
