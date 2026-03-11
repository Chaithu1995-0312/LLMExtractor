from graph.db import Base, engine


def upgrade():
    Base.metadata.reflect(engine)
    
    with engine.connect() as conn:
        conn.execute("""
        ALTER TABLE graph.nodes 
        ADD COLUMN status VARCHAR(20),
        ADD COLUMN l1_started_at TIMESTAMP,
        ADD COLUMN l1_completed_at TIMESTAMP;
        """)
        
        conn.execute("""
        ALTER TABLE sync.bricks
        ADD COLUMN status VARCHAR(20),
        ADD COLUMN l2_started_at TIMESTAMP,
        ADD COLUMN l2_completed_at TIMESTAMP;
        """)