"""
Database Connection Management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from config import settings
from database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database engine and session factory"""
        try:
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                echo=settings.debug,  # Log SQL queries in debug mode
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                session.query(Customer).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_db(self) -> Generator[Session, None, None]:
        """
        Dependency for FastAPI to get database session
        
        Usage in FastAPI:
            @app.get("/items")
            def get_items(db: Session = Depends(db_manager.get_db)):
                return db.query(Item).all()
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Get database session for FastAPI dependency injection"""
    return db_manager.get_db()


def init_database():
    """Initialize database with tables"""
    db_manager.create_tables()
    logger.info("Database initialized")


if __name__ == "__main__":
    # For testing/setup purposes
    logging.basicConfig(level=logging.INFO)
    init_database()
    print("Database setup completed!")
