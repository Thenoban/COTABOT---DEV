"""
Add Training Match models to database/models.py
"""

# Read current models.py
with open('database/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already added
if 'TrainingMatch' in content:
    print("Training Match models already exist!")
else:
    # Append Training Match models
    training_models = """

# ============================================
# TRAINING MATCHES MODELS
# ============================================

class TrainingMatch(Base):
    \"\"\"Training match records\"\"\"
    __tablename__ = 'training_matches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(20), unique=True, nullable=False, index=True)
    server_ip = Column(String(50))
    map_name = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), default='active')
    snapshot_start_json = Column(Text)
    snapshot_end_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    players = relationship("TrainingPlayer", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TrainingMatch(id={self.match_id}, map={self.map_name})>"


class TrainingPlayer(Base):
    \"\"\"Player participation in training match\"\"\"
    __tablename__ = 'training_players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('training_matches.id'), nullable=False, index=True)
    steam_id = Column(String(20))
    name = Column(String(100))
    kills_manual = Column(Integer)
    deaths_manual = Column(Integer)
    assists_manual = Column(Integer)
    final_kills = Column(Integer, default=0)
    final_deaths = Column(Integer, default=0)
    final_assists = Column(Integer, default=0)
    kd_ratio = Column(Float, default=0.0)
    data_source = Column(String(20))
    
    match = relationship("TrainingMatch", back_populates="players")
    
    __table_args__ = (
        UniqueConstraint('match_id', 'steam_id', name='_match_player_uc'),
    )
    
    def __repr__(self):
        return f"<TrainingPlayer(name={self.name})>"
"""
    
    # Write back
    with open('database/models.py', 'w', encoding='utf-8') as f:
        f.write(content + training_models)
    
    print("SUCCESS: Training Match models added to database/models.py")

# Now test it
print("\nTesting import...")
from database.adapter import DatabaseAdapter

db = DatabaseAdapter('sqlite:///cotabot_dev.db')
db.init_db()
print("SUCCESS: Database tables created!")
