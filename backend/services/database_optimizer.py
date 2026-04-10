"""
Database Migration and Optimization Service

Provides PostgreSQL migration utilities, database optimization,
and performance monitoring for the diabetes prediction system.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine
from backend.extensions import db
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Database optimization and performance monitoring"""
    
    def __init__(self):
        self.performance_metrics = {}
        self.index_recommendations = []
        self.query_stats = {}
    
    def analyze_database_performance(self) -> Dict[str, Any]:
        """Analyze database performance and provide recommendations"""
        engine = db.engine
        
        # Check database type
        is_postgresql = 'postgresql' in engine.dialect.name.lower()
        
        performance_report = {
            'database_type': engine.dialect.name,
            'connection_pool_stats': self._get_connection_pool_stats(),
            'slow_queries': self._get_slow_queries() if is_postgresql else [],
            'missing_indexes': self._find_missing_indexes() if is_postgresql else [],
            'table_sizes': self._get_table_sizes() if is_postgresql else [],
            'recommendations': []
        }
        
        # Generate recommendations
        performance_report['recommendations'] = self._generate_recommendations(performance_report)
        
        return performance_report
    
    def _get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool = db.engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalid()
        }
    
    def _get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get slow query statistics from PostgreSQL"""
        try:
            query = text("""
                SELECT query, calls, total_time, mean_time, rows
                FROM pg_stat_statements
                WHERE mean_time > 1000
                ORDER BY mean_time DESC
                LIMIT 10
            """)
            
            result = db.session.execute(query)
            return [dict(row) for row in result]
        except Exception as e:
            logger.warning(f"Could not get slow queries: {e}")
            return []
    
    def _find_missing_indexes(self) -> List[Dict[str, Any]]:
        """Find potentially missing indexes in PostgreSQL"""
        try:
            query = text("""
                SELECT schemaname, tablename, attname, n_distinct, correlation
                FROM pg_stats
                WHERE schemaname = 'public'
                AND n_distinct > 10
                ORDER BY n_distinct DESC
                LIMIT 20
            """)
            
            result = db.session.execute(query)
            return [dict(row) for row in result]
        except Exception as e:
            logger.warning(f"Could not analyze missing indexes: {e}")
            return []
    
    def _get_table_sizes(self) -> List[Dict[str, Any]]:
        """Get table size statistics"""
        try:
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """)
            
            result = db.session.execute(query)
            return [dict(row) for row in result]
        except Exception as e:
            logger.warning(f"Could not get table sizes: {e}")
            return []
    
    def _generate_recommendations(self, performance_report: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Connection pool recommendations
        pool_stats = performance_report['connection_pool_stats']
        if pool_stats['checked_out'] > pool_stats['pool_size'] * 0.8:
            recommendations.append("Consider increasing database pool size")
        
        # Slow query recommendations
        if performance_report['slow_queries']:
            recommendations.append(f"Found {len(performance_report['slow_queries'])} slow queries - optimize them")
        
        # Index recommendations
        if performance_report['missing_indexes']:
            recommendations.append("Consider adding indexes for frequently queried columns")
        
        # Table size recommendations
        large_tables = [t for t in performance_report['table_sizes'] if t['size_bytes'] > 100_000_000]  # 100MB
        if large_tables:
            recommendations.append(f"Consider partitioning large tables: {[t['tablename'] for t in large_tables]}")
        
        return recommendations
    
    def create_performance_indexes(self) -> bool:
        """Create recommended performance indexes"""
        indexes = [
            # User and authentication indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            
            # Patient indexes
            "CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_patients_registered_by ON patients(registered_by)",
            
            # Health record indexes
            "CREATE INDEX IF NOT EXISTS idx_health_records_patient ON health_records(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_health_records_created ON health_records(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_health_records_patient_created ON health_records(patient_id, created_at)",
            
            # Prediction indexes
            "CREATE INDEX IF NOT EXISTS idx_predictions_patient ON predictions(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_risk_level ON predictions(risk_level)",
            
            # Prescription indexes
            "CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_prescriptions_status ON prescriptions(status)",
            "CREATE INDEX IF NOT EXISTS idx_prescriptions_created ON prescriptions(created_at)",
            
            # Lab test indexes
            "CREATE INDEX IF NOT EXISTS idx_lab_tests_patient ON lab_tests(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_lab_tests_doctor ON lab_tests(doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_lab_tests_technician ON lab_tests(technician_id)",
            "CREATE INDEX IF NOT EXISTS idx_lab_tests_status ON lab_tests(status)",
            "CREATE INDEX IF NOT EXISTS idx_lab_tests_created ON lab_tests(created_at)",
            
            # Appointment indexes
            "CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)",
            "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)",
            
            # Audit log indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action)",
            
            # Payment indexes
            "CREATE INDEX IF NOT EXISTS idx_payments_patient ON payments(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(payment_status)",
            "CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at)",
        ]
        
        success = True
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                logger.info(f"Created index: {index_sql}")
            except Exception as e:
                logger.error(f"Failed to create index: {index_sql}, Error: {e}")
                success = False
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit index creation: {e}")
            db.session.rollback()
            success = False
        
        return success
    
    def optimize_database_settings(self) -> bool:
        """Apply PostgreSQL performance optimizations"""
        optimizations = [
            # Enable query statistics
            "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
            
            # Update table statistics
            "ANALYZE",
            
            # Vacuum and reindex
            "VACUUM ANALYZE",
            "REINDEX DATABASE CONCURRENTLY diabetes_db",
        ]
        
        success = True
        for opt_sql in optimizations:
            try:
                db.session.execute(text(opt_sql))
                logger.info(f"Applied optimization: {opt_sql}")
            except Exception as e:
                logger.error(f"Failed to apply optimization: {opt_sql}, Error: {e}")
                success = False
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit optimizations: {e}")
            db.session.rollback()
            success = False
        
        return success
    
    def setup_database_monitoring(self) -> Dict[str, Any]:
        """Setup database monitoring and alerting"""
        monitoring_setup = {
            'slow_query_threshold': 1000,  # milliseconds
            'connection_threshold': 0.8,    # 80% of pool
            'table_size_threshold': 100_000_000,  # 100MB
            'query_timeout': 30000,  # 30 seconds
            'monitoring_queries': {
                'active_connections': """
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """,
                'database_size': """
                    SELECT pg_size_pretty(pg_database_size(current_database())) as database_size
                """,
                'lock_waits': """
                    SELECT count(*) as lock_waits 
                    FROM pg_locks l 
                    JOIN pg_stat_activity a ON l.pid = a.pid 
                    WHERE l.granted = false
                """
            }
        }
        
        return monitoring_setup

class DatabaseMigration:
    """Database migration utilities for PostgreSQL"""
    
    def __init__(self):
        self.migration_version = "1.0.0"
    
    def migrate_from_sqlite_to_postgresql(self, sqlite_db_path: str, postgres_url: str) -> bool:
        """Migrate data from SQLite to PostgreSQL"""
        try:
            import sqlite3
            from sqlalchemy import create_engine
            
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(sqlite_db_path)
            sqlite_conn.row_factory = sqlite3.Row
            
            # Connect to PostgreSQL
            postgres_engine = create_engine(postgres_url)
            
            # Get all tables from SQLite
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Migrate each table
            for table in tables:
                if table.startswith('sqlite_') or table == 'alembic_version':
                    continue
                
                logger.info(f"Migrating table: {table}")
                
                # Get data from SQLite
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                if rows:
                    # Convert to list of dictionaries
                    data = [dict(row) for row in rows]
                    
                    # Create DataFrame and insert to PostgreSQL
                    import pandas as pd
                    df = pd.DataFrame(data)
                    
                    # Handle datetime conversion
                    for col in df.columns:
                        if 'date' in col.lower() or 'time' in col.lower():
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                    
                    # Insert to PostgreSQL
                    df.to_sql(table, postgres_engine, if_exists='append', index=False)
                    logger.info(f"Migrated {len(df)} rows to {table}")
            
            sqlite_conn.close()
            logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def create_postgresql_schema(self) -> bool:
        """Create optimized PostgreSQL schema"""
        schema_statements = [
            # UUID extension for better primary keys
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
            
            # Enable pg_stat_statements for query monitoring
            "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
            
            # Create optimized data types
            """
            DO $$
            BEGIN
                -- Add UUID columns for better performance
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name = 'users' AND column_name = 'uuid') THEN
                    ALTER TABLE users ADD COLUMN uuid UUID DEFAULT uuid_generate_v4();
                    CREATE UNIQUE INDEX idx_users_uuid ON users(uuid);
                END IF;
                
                -- Add similar UUID columns to other tables
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name = 'patients' AND column_name = 'uuid') THEN
                    ALTER TABLE patients ADD COLUMN uuid UUID DEFAULT uuid_generate_v4();
                    CREATE UNIQUE INDEX idx_patients_uuid ON patients(uuid);
                END IF;
            END $$;
            """
        ]
        
        success = True
        for statement in schema_statements:
            try:
                db.session.execute(text(statement))
                logger.info(f"Applied schema optimization: {statement}")
            except Exception as e:
                logger.error(f"Schema optimization failed: {statement}, Error: {e}")
                success = False
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit schema changes: {e}")
            db.session.rollback()
            success = False
        
        return success

# Global instances
db_optimizer = DatabaseOptimizer()
db_migration = DatabaseMigration()
