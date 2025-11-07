"""
Database backup system for Secret Vault
"""
import sqlite3
import shutil
import gzip
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import os
import time
from config import settings
from logger import get_logger, log_backup_operation

logger = get_logger("backup")


class DatabaseBackup:
    """Database backup manager"""
    
    def __init__(self):
        self.backup_dir = Path(settings.backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.database_path = Path("secret_vault.db")
        self.encryption_key_path = Path(settings.encryption_key_file)
    
    def create_backup(self, include_metadata: bool = True) -> Optional[str]:
        """Create a complete backup of the database and encryption key"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"secret_vault_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Check if database exists
            if not self.database_path.exists():
                logger.error("Database file not found")
                return None
            
            # Create backup
            shutil.copy2(self.database_path, backup_path)
            
            # Compress the backup
            compressed_path = self.compress_file(backup_path)
            
            # Remove uncompressed backup
            backup_path.unlink()
            
            # Create metadata file
            if include_metadata:
                metadata = self.create_backup_metadata(compressed_path)
                metadata_path = compressed_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Log the backup
            file_size = compressed_path.stat().st_size
            log_backup_operation(logger, "CREATE", compressed_path.name, file_size, True)
            
            logger.info(f"Backup created successfully: {compressed_path.name} ({file_size} bytes)")
            return str(compressed_path)
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            log_backup_operation(logger, "CREATE", "unknown", None, False)
            return None
    
    def compress_file(self, file_path: Path) -> Path:
        """Compress a file using gzip"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path
    
    def decompress_file(self, compressed_path: Path) -> Path:
        """Decompress a gzipped file"""
        decompressed_path = compressed_path.with_suffix('').with_suffix(compressed_path.suffix.replace('.gz', ''))
        
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_path
    
    def create_backup_metadata(self, backup_path: Path) -> Dict[str, Any]:
        """Create metadata for the backup"""
        metadata = {
            "backup_filename": backup_path.name,
            "backup_timestamp": datetime.now().isoformat(),
            "database_size": self.database_path.stat().st_size if self.database_path.exists() else 0,
            "backup_size": backup_path.stat().st_size,
            "compression_ratio": self.calculate_compression_ratio(),
            "database_info": self.get_database_info(),
            "encryption_key_exists": self.encryption_key_path.exists(),
            "application_version": "1.0.0",
            "environment": settings.environment
        }
        return metadata
    
    def calculate_compression_ratio(self) -> float:
        """Calculate compression ratio"""
        if not self.database_path.exists():
            return 0.0
        
        original_size = self.database_path.stat().st_size
        # Create a temporary compressed file to measure size
        temp_compressed = self.compress_file(self.database_path)
        compressed_size = temp_compressed.stat().st_size
        temp_compressed.unlink()
        
        return (1 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        if not self.database_path.exists():
            return {"error": "Database not found"}
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get row counts
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            
            # Get database size
            cursor.execute("PRAGMA page_count;")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size;")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size
            
            conn.close()
            
            return {
                "tables": tables,
                "table_counts": table_counts,
                "database_size_bytes": db_size,
                "total_rows": sum(table_counts.values())
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.db.gz"):
            try:
                stat = backup_file.stat()
                metadata_file = backup_file.with_suffix('.json')
                
                backup_info = {
                    "filename": backup_file.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime),
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "metadata": None
                }
                
                # Load metadata if available
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            backup_info["metadata"] = json.load(f)
                    except Exception as e:
                        logger.warning(f"Could not load metadata for {backup_file.name}: {e}")
                
                backups.append(backup_info)
                
            except Exception as e:
                logger.error(f"Error reading backup {backup_file.name}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def restore_backup(self, backup_filename: str, verify_only: bool = False) -> bool:
        """Restore a backup"""
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            # Decompress backup
            decompressed_path = self.decompress_file(backup_path)
            
            if verify_only:
                # Just verify the backup is valid
                try:
                    conn = sqlite3.connect(decompressed_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()
                    
                    logger.info(f"Backup verification successful: {len(tables)} tables found")
                    decompressed_path.unlink()  # Clean up
                    return True
                    
                except Exception as e:
                    logger.error(f"Backup verification failed: {e}")
                    decompressed_path.unlink()  # Clean up
                    return False
            
            # Create backup of current database before restore
            if self.database_path.exists():
                current_backup = f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(self.database_path, self.backup_dir / current_backup)
                logger.info(f"Created pre-restore backup: {current_backup}")
            
            # Restore the backup
            shutil.copy2(decompressed_path, self.database_path)
            
            # Clean up decompressed file
            decompressed_path.unlink()
            
            # Verify the restore
            if self.verify_database():
                log_backup_operation(logger, "RESTORE", backup_filename, None, True)
                logger.info(f"Backup restored successfully: {backup_filename}")
                return True
            else:
                logger.error("Database verification failed after restore")
                return False
                
        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            log_backup_operation(logger, "RESTORE", backup_filename, None, False)
            return False
    
    def verify_database(self) -> bool:
        """Verify the database integrity"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                logger.error(f"Database integrity check failed: {result[0]}")
                return False
            
            # Check if required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ["credentials", "audit_logs"]
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"Missing required tables: {missing_tables}")
                return False
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False
    
    def cleanup_old_backups(self) -> int:
        """Remove old backups based on retention policy"""
        try:
            retention_days = settings.backup_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob("*.db.gz"):
                try:
                    stat = backup_file.stat()
                    created_date = datetime.fromtimestamp(stat.st_ctime)
                    
                    if created_date < cutoff_date:
                        # Delete backup file
                        backup_file.unlink()
                        
                        # Delete metadata file if it exists
                        metadata_file = backup_file.with_suffix('.json')
                        if metadata_file.exists():
                            metadata_file.unlink()
                        
                        logger.info(f"Deleted old backup: {backup_file.name}")
                        deleted_count += 1
                        
                except Exception as e:
                    logger.error(f"Error deleting backup {backup_file.name}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleanup completed: {deleted_count} old backups deleted")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return 0
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        backups = self.list_backups()
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "average_size": 0
            }
        
        total_size = sum(backup["size"] for backup in backups)
        oldest_backup = min(backup["created"] for backup in backups)
        newest_backup = max(backup["created"] for backup in backups)
        average_size = total_size / len(backups)
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": oldest_backup.isoformat(),
            "newest_backup": newest_backup.isoformat(),
            "average_size": round(average_size / (1024 * 1024), 2),
            "retention_days": settings.backup_retention_days
        }


def create_scheduled_backup():
    """Create a scheduled backup (for use with cron or scheduler)"""
    backup_manager = DatabaseBackup()
    
    # Create backup
    backup_path = backup_manager.create_backup()
    
    if backup_path:
        # Cleanup old backups
        deleted_count = backup_manager.cleanup_old_backups()
        
        # Log summary
        stats = backup_manager.get_backup_stats()
        logger.info(f"Scheduled backup completed. Stats: {stats}")
        
        return True
    else:
        logger.error("Scheduled backup failed")
        return False


if __name__ == "__main__":
    # Test the backup system
    backup_manager = DatabaseBackup()
    
    print("=== Secret Vault Backup System Test ===")
    
    # Create a backup
    print("\n1. Creating backup...")
    backup_path = backup_manager.create_backup()
    if backup_path:
        print(f"✓ Backup created: {backup_path}")
    else:
        print("✗ Backup creation failed")
    
    # List backups
    print("\n2. Listing backups...")
    backups = backup_manager.list_backups()
    for backup in backups:
        print(f"  - {backup['filename']} ({backup['size']} bytes, {backup['created']})")
    
    # Get stats
    print("\n3. Backup statistics...")
    stats = backup_manager.get_backup_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Verify a backup
    if backups:
        print(f"\n4. Verifying backup: {backups[0]['filename']}...")
        if backup_manager.restore_backup(backups[0]['filename'], verify_only=True):
            print("✓ Backup verification successful")
        else:
            print("✗ Backup verification failed")
    
    print("\n=== Backup system test completed ===")
